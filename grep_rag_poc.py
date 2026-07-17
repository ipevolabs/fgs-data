"""
grep-based (agentic LLM + grep) RAG proof-of-concept for FGS Chinese -> English
translation. Counterpart to azure_rag_poc.py that uses NO embedding model and NO
vector database -- the only retrieval primitive is the real `grep`/`rg` binary
run over the big translation corpus on disk. See issue #18 / grep-based-rag.md.

The thesis: grep never does semantic search. An Azure OpenAI chat model supplies
the semantics -- it decomposes the input Chinese into key terms / proper nouns,
greps the translation memory for each term's existing English rendering, reads
what came back, and searches again until it can translate the whole sentence
with consistent terminology. The semantic step happens at query-generation time
(in the model), not at match time in a vector space.

vs. azure_rag_poc.py:
  * ingest        -> build-corpus  (flatten TM to one grep-able text file; no embeddings)
  * query         -> search        (one raw grep, no LLM)
  * translate     -> translate     (LLM drives grep in a loop, then translates)
  * no create-index, no vector store, no embedding deployment needed

Setup:
    pip install openai python-dotenv        # note: no azure-search-documents

Env (.env) -- only the Azure OpenAI chat model is needed:
    AZURE_OPENAI_ENDPOINT=https://<res>.openai.azure.com
    AZURE_OPENAI_KEY=<key>
    AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o     # or gpt-5-mini-global, etc.

Usage:
    python grep_rag_poc.py build-corpus blia_terminology.tsv hb_glossary_v2v3.tsv data/fgsft3.jsonl
    python grep_rag_poc.py search  "人間佛教"
    python grep_rag_poc.py translate "在今年的活動中，共有五十首全新創作的歌曲被選入。"
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
CORPUS_DIR = Path(os.getenv("GREP_CORPUS_DIR", "corpus"))
CORPUS_FILE = CORPUS_DIR / "fgs_tm.tsv"  # kind<TAB>zh<TAB>en, one pair per line
MAX_TURNS = 8  # safety cap on the search-and-read loop
SYSTEM_PROMPT = (
    "你是一個佛學翻譯專家，精通中英文佛教詞彙。你只能透過 `grep` 工具查詢一個中英對照"
    "翻譯記憶庫，每行格式為 `類別<TAB>中文<TAB>English`。grep 只做精確字面比對，"
    "沒有任何語意理解，所以語意的工作由你負責：把輸入句子拆成關鍵詞、專有名詞或短語，"
    "用 grep 找出這些詞既有的英文譯法；若某次查無結果，就換用同義詞、更短的詞或其他"
    "措辭再試。蒐集到足夠的既有譯法後，參考它們把整句翻成英文，並保持術語一致。"
    "最後只輸出最終英文翻譯，不要輸出搜尋過程。"
)


def _openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version="2025-04-01-preview",
    )


# --------------------------------------------------------------------------- #
# Loading records from the repo's existing formats (mirrors azure_rag_poc.py)
# --------------------------------------------------------------------------- #
def load_tsv(path: str):
    """Glossary TSV: '#Chinese<TAB>#English' header then zh<TAB>en rows."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
                continue
            yield ("glossary", parts[0].strip(), parts[1].strip())


def load_jsonl(path: str):
    """Augmented jsonl: translation.phrase + translation.sentences[].{zh,en}."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tr = json.loads(line).get("translation")
            if not tr:
                continue
            phrase = tr.get("phrase") or {}
            if phrase.get("zh") and phrase.get("en"):
                yield ("glossary", phrase["zh"].strip(), phrase["en"].strip())
            for s in tr.get("sentences", []):
                if s.get("zh") and s.get("en"):
                    yield ("sentence", s["zh"].strip(), s["en"].strip())


def load_records(paths: list[str]):
    for path in paths:
        loader = load_tsv if path.endswith(".tsv") else load_jsonl
        yield from loader(path)


# --------------------------------------------------------------------------- #
# Corpus building -- the "index" is just a flat text file grep reads directly.
# No embeddings, no vector DB, no sync ETL: it is the current bytes on disk.
# --------------------------------------------------------------------------- #
def build_corpus(paths: list[str]) -> None:
    """Flatten glossary + TM pairs into one grep-able TSV, de-duplicating."""
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, str]] = set()
    total = 0
    with open(CORPUS_FILE, "w", encoding="utf-8") as out:
        for kind, zh, en in load_records(paths):
            key = (kind, zh)
            if key in seen:
                continue
            seen.add(key)
            # newlines/tabs inside values would break the one-line-per-pair layout
            zh1 = zh.replace("\t", " ").replace("\n", " ")
            en1 = en.replace("\t", " ").replace("\n", " ")
            out.write(f"{kind}\t{zh1}\t{en1}\n")
            total += 1
    print(f"done: {total} unique pairs written to {CORPUS_FILE}")


# --------------------------------------------------------------------------- #
# The ONLY retrieval tool: real grep. Prefers ripgrep (`rg`), falls back to grep.
# --------------------------------------------------------------------------- #
def run_grep(pattern: str, max_lines: int = 40) -> str:
    """Case-insensitive search over the corpus file. Returns matching
    `kind<TAB>zh<TAB>en` lines, or a 'no matches' note."""
    if not CORPUS_FILE.exists():
        return f"(corpus not built: run `build-corpus` first -- {CORPUS_FILE} missing)"
    if shutil.which("rg"):
        cmd = ["rg", "-i", "-N", "--no-heading", pattern, str(CORPUS_FILE)]
    else:
        cmd = ["grep", "-i", pattern, str(CORPUS_FILE)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip()
    if not out:
        return f"(no matches for pattern: {pattern!r})"
    lines = out.splitlines()
    clipped = lines[:max_lines]
    note = "" if len(lines) <= max_lines else f"\n... ({len(lines) - max_lines} more matches)"
    return "\n".join(clipped) + note


GREP_TOOL = {
    "type": "function",
    "function": {
        "name": "grep",
        "description": (
            "Search the Chinese->English translation memory for a literal, "
            "case-insensitive pattern (each line is `kind<TAB>zh<TAB>en`). This "
            "is EXACT text matching only -- no understanding of meaning or "
            "synonyms. If a search returns no matches, try shorter terms or "
            "other words expressing the same concept."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Literal string / regex to search for."}
            },
            "required": ["pattern"],
        },
    },
}


# --------------------------------------------------------------------------- #
# The agentic retrieval loop: LLM -> emits grep(s) -> we run them -> feed back
# -> repeat -> final translation. All semantics live in the model's queries.
# --------------------------------------------------------------------------- #
def _chat(messages: list[dict], tools=None):
    kwargs = {"model": CHAT_DEPLOYMENT, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    # GPT-5 reasoning models only accept the default temperature.
    if "gpt-5" not in CHAT_DEPLOYMENT.lower():
        kwargs["temperature"] = 0.2
    return _openai_client().chat.completions.create(**kwargs)


def translate(zh: str, verbose: bool = False) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"請翻譯以下中文為英文：\n{zh}"},
    ]
    grep_calls, grep_ms, gen_ms = 0, 0.0, 0.0
    for _ in range(MAX_TURNS):
        t0 = time.perf_counter()
        resp = _chat(messages, tools=[GREP_TOOL])
        gen_ms += (time.perf_counter() - t0) * 1000
        msg = resp.choices[0].message

        if not msg.tool_calls:
            print(
                f"⏱ {grep_calls} grep calls · grep {grep_ms:.0f}ms "
                f"· generation {gen_ms:.0f}ms · total {grep_ms + gen_ms:.0f}ms",
                file=sys.stderr,
            )
            return (msg.content or "").strip()

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            pattern = json.loads(tc.function.arguments).get("pattern", "")
            t0 = time.perf_counter()
            result = run_grep(pattern)
            grep_ms += (time.perf_counter() - t0) * 1000
            grep_calls += 1
            if verbose:
                hit = "MISS" if result.startswith("(no matches") else "HIT "
                print(f"  grep> {pattern!r:<24} [{hit}]", file=sys.stderr)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    print("(hit the search-loop cap without a final answer)", file=sys.stderr)
    return ""


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="FGS grep-based (LLM+grep) RAG POC")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_bc = sub.add_parser("build-corpus")
    p_bc.add_argument("paths", nargs="+", help="glossary .tsv and/or augmented .jsonl files")
    p_s = sub.add_parser("search")
    p_s.add_argument("pattern")
    p_t = sub.add_parser("translate")
    p_t.add_argument("zh")
    p_t.add_argument("-v", "--verbose", action="store_true", help="show each grep the model runs")
    args = ap.parse_args()

    if args.cmd == "build-corpus":
        build_corpus(args.paths)
    elif args.cmd == "search":
        t0 = time.perf_counter()
        print(run_grep(args.pattern))
        print(f"⏱ grep {(time.perf_counter() - t0) * 1000:.0f}ms", file=sys.stderr)
    elif args.cmd == "translate":
        print(translate(args.zh, verbose=args.verbose))


if __name__ == "__main__":
    sys.exit(main())
