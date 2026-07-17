"""
Azure AI Search RAG proof-of-concept for FGS Chinese -> English translation.

Replaces the finetuned GPT-4o approach (issue #17) with retrieval of translation
memory + glossary terms at inference time. Loads:
  * glossary TSV files (phrase-level zh<TAB>en, e.g. blia_terminology.tsv,
    hb_glossary_v2v3.tsv)
  * augmented jsonl files (sentence-level pairs, e.g. data/fgsft3.jsonl)
into one Azure AI Search index, then runs hybrid (keyword + vector) retrieval and
builds a few-shot prompt for any Azure OpenAI chat model.

This POC embeds text client-side via Azure OpenAI (transparent, easy to run
locally). For a zero-pipeline alternative, Azure AI Search "integrated
vectorization" can embed at index/query time -- see the survey in issue #17.

Setup:
    pip install azure-search-documents openai python-dotenv

Env (.env):
    AZURE_SEARCH_ENDPOINT=https://<svc>.search.windows.net
    AZURE_SEARCH_KEY=<admin-key>
    AZURE_OPENAI_ENDPOINT=https://<res>.openai.azure.com
    AZURE_OPENAI_KEY=<key>
    AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-small   # 1536 dims
    AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o                     # for `translate`

Usage:
    python azure_rag_poc.py create-index
    python azure_rag_poc.py ingest blia_terminology.tsv hb_glossary_v2v3.tsv data/fgsft3.jsonl
    python azure_rag_poc.py query  "人間音緣星雲大師佛教歌曲發表會"
    python azure_rag_poc.py translate "在今年的活動中，共有五十首全新創作的歌曲被選入。"
"""
import argparse
import hashlib
import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)

load_dotenv()

INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX", "fgs-translation-memory")
EMBED_DIMS = int(os.getenv("AZURE_OPENAI_EMBED_DIMS", "1536"))  # 3-small=1536, 3-large=3072
EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small")
CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
SYSTEM_PROMPT = "你是一個佛學專家,精通中英文佛教詞彙,會將輸入中文翻譯為英文."


def _search_index_client() -> SearchIndexClient:
    return SearchIndexClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"]),
    )


def _search_client() -> SearchClient:
    return SearchClient(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"]),
    )


def _openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version="2025-04-01-preview",
    )


def embed(client: AzureOpenAI, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with Azure OpenAI.

    text-embedding-3-* support Matryoshka truncation via `dimensions`; short
    inputs (we translate 2-3 sentences at a time) retain quality at 384 dims
    while using 4x less index storage than the default 1536.
    """
    resp = client.embeddings.create(
        model=EMBED_DEPLOYMENT, input=texts, dimensions=EMBED_DIMS
    )
    return [d.embedding for d in resp.data]


# --------------------------------------------------------------------------- #
# Index management
# --------------------------------------------------------------------------- #
def create_index() -> None:
    """(Re)create the hybrid search index: full-text on zh + vector on zh."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        # kind: "glossary" (phrase pair) or "sentence" (augmented example)
        SimpleField(name="kind", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="zh", type=SearchFieldDataType.String, analyzer_name="zh-Hant.microsoft"),
        SearchableField(name="en", type=SearchFieldDataType.String),
        SearchField(
            name="zh_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBED_DIMS,
            vector_search_profile_name="hnsw-profile",
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-config")],
    )
    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
    _search_index_client().create_or_update_index(index)
    print(f"index '{INDEX_NAME}' created/updated ({EMBED_DIMS}-dim vectors)")


# --------------------------------------------------------------------------- #
# Loading records from the repo's existing formats
# --------------------------------------------------------------------------- #
def _doc_id(kind: str, zh: str) -> str:
    return f"{kind}-{hashlib.sha1(zh.encode('utf-8')).hexdigest()}"


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
            zh, en = parts[0].strip(), parts[1].strip()
            yield {"id": _doc_id("glossary", zh), "kind": "glossary", "zh": zh, "en": en}


def load_jsonl(path: str):
    """Augmented jsonl: translation.phrase + translation.sentences[].{zh,en}."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            tr = obj.get("translation")
            if not tr:
                continue
            phrase = tr.get("phrase") or {}
            if phrase.get("zh") and phrase.get("en"):
                yield {
                    "id": _doc_id("glossary", phrase["zh"]),
                    "kind": "glossary",
                    "zh": phrase["zh"].strip(),
                    "en": phrase["en"].strip(),
                }
            for s in tr.get("sentences", []):
                if s.get("zh") and s.get("en"):
                    yield {
                        "id": _doc_id("sentence", s["zh"]),
                        "kind": "sentence",
                        "zh": s["zh"].strip(),
                        "en": s["en"].strip(),
                    }


def load_records(paths: list[str]):
    for path in paths:
        loader = load_tsv if path.endswith(".tsv") else load_jsonl
        yield from loader(path)


def ingest(paths: list[str], batch_size: int = 64, limit: int | None = None) -> None:
    """Embed zh side and upload to the index, de-duplicating by id.

    limit caps the number of unique documents (useful for the Free search tier,
    which allows at most 10,000 documents).
    """
    oai = _openai_client()
    search = _search_client()
    seen: set[str] = set()
    batch: list[dict] = []
    total = 0

    def flush() -> None:
        nonlocal total
        if not batch:
            return
        vectors = embed(oai, [d["zh"] for d in batch])
        for d, v in zip(batch, vectors):
            d["zh_vector"] = v
        search.upload_documents(documents=batch)
        total += len(batch)
        print(f"  uploaded {total}")
        batch.clear()

    for rec in load_records(paths):
        if rec["id"] in seen:
            continue
        seen.add(rec["id"])
        batch.append(rec)
        if len(batch) >= batch_size:
            flush()
        if limit is not None and total + len(batch) >= limit:
            break
    flush()
    print(f"done: {total} unique documents ingested")


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
def retrieve(zh: str, k: int = 5, kind: str | None = None, timings: dict | None = None) -> list[dict]:
    """Hybrid search: BM25 on zh text + vector similarity on zh embedding.

    If `timings` is provided, records embed/search latency (ms) into it.
    """
    oai = _openai_client()
    search = _search_client()
    t0 = time.perf_counter()
    qvec = embed(oai, [zh])[0]
    t1 = time.perf_counter()
    vquery = VectorizedQuery(vector=qvec, k_nearest_neighbors=k, fields="zh_vector")
    results = search.search(
        search_text=zh,  # keyword half of the hybrid query
        vector_queries=[vquery],
        filter=f"kind eq '{kind}'" if kind else None,
        select=["kind", "zh", "en"],
        top=k,
    )
    out = [{"kind": r["kind"], "zh": r["zh"], "en": r["en"], "score": r["@search.score"]} for r in results]
    t2 = time.perf_counter()
    if timings is not None:
        timings["embed_ms"] = (t1 - t0) * 1000
        timings["search_ms"] = (t2 - t1) * 1000
    return out


def build_prompt(zh: str, glossary: list[dict], examples: list[dict]) -> list[dict]:
    """Assemble a few-shot chat prompt grounded in retrieved TM + glossary."""
    ctx = []
    if glossary:
        ctx.append("詞彙對照 (glossary):")
        ctx += [f"  {g['zh']} => {g['en']}" for g in glossary]
    if examples:
        ctx.append("\n翻譯範例 (translation memory):")
        for e in examples:
            ctx.append(f"  中文: {e['zh']}\n  英文: {e['en']}")
    user = ("\n".join(ctx) + "\n\n" if ctx else "") + f"請翻譯以下中文為英文:\n{zh}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def translate(zh: str, k: int = 4) -> str:
    tg, ts = {}, {}
    t0 = time.perf_counter()
    glossary = retrieve(zh, k=k, kind="glossary", timings=tg)
    examples = retrieve(zh, k=k, kind="sentence", timings=ts)
    t1 = time.perf_counter()
    messages = build_prompt(zh, glossary, examples)
    kwargs = {"model": CHAT_DEPLOYMENT, "messages": messages}
    # GPT-5 reasoning models only accept the default temperature; older models
    # (e.g. gpt-4o) benefit from a low temperature for deterministic translation.
    if "gpt-5" not in CHAT_DEPLOYMENT.lower():
        kwargs["temperature"] = 0.2
    resp = _openai_client().chat.completions.create(**kwargs)
    t2 = time.perf_counter()
    retrieval_ms, gen_ms = (t1 - t0) * 1000, (t2 - t1) * 1000
    embed_ms = tg["embed_ms"] + ts["embed_ms"]
    search_ms = tg["search_ms"] + ts["search_ms"]
    print(
        f"⏱ retrieval {retrieval_ms:.0f}ms (embed {embed_ms:.0f} · search {search_ms:.0f}) "
        f"· generation {gen_ms:.0f}ms · total {retrieval_ms + gen_ms:.0f}ms",
        file=sys.stderr,
    )
    return resp.choices[0].message.content.strip()


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="FGS Azure AI Search RAG POC")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create-index")
    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("paths", nargs="+", help="glossary .tsv and/or augmented .jsonl files")
    p_ing.add_argument("--limit", type=int, default=None, help="cap total docs (Free tier max 10000)")
    p_q = sub.add_parser("query")
    p_q.add_argument("zh")
    p_q.add_argument("-k", type=int, default=5)
    p_t = sub.add_parser("translate")
    p_t.add_argument("zh")
    p_t.add_argument("-k", type=int, default=4)
    args = ap.parse_args()

    if args.cmd == "create-index":
        create_index()
    elif args.cmd == "ingest":
        ingest(args.paths, limit=args.limit)
    elif args.cmd == "query":
        t = {}
        for r in retrieve(args.zh, k=args.k, timings=t):
            print(f"[{r['kind']:8s} {r['score']:.3f}] {r['zh']}  =>  {r['en']}")
        print(
            f"⏱ embed {t['embed_ms']:.0f}ms · search {t['search_ms']:.0f}ms "
            f"· total {t['embed_ms'] + t['search_ms']:.0f}ms",
            file=sys.stderr,
        )
    elif args.cmd == "translate":
        print(translate(args.zh, k=args.k))


if __name__ == "__main__":
    sys.exit(main())
