# Is `grep` all you need for RAG?

A discussion about replacing the embedding-model + vector-database stack in a
RAG application with the humble Unix `grep`, why that argument works, where it
breaks, and a small proof-of-concept that demonstrates the mechanism.

---

## 1. The claim: "just use grep"

The provocative version is *"you don't need an embedding model or a vector DB
for RAG — `grep` is all you need."* It is most compelling once you notice it is
really an argument about **agentic** retrieval, not the classic one-shot RAG
setup.

### What the embedding pipeline actually costs you

An embedding + vector DB system looks clean in a diagram but hides a lot of
moving parts:

- **Chunking** is lossy and arbitrary. Where you cut matters, and a bad
  boundary can split the answer across two chunks so neither retrieves well.
- You must **choose and host an embedding model**, keep it identical between
  index time and query time, and **re-embed everything** if you ever change it.
- You need a **vector store as live infrastructure** that must stay in sync with
  the source of truth. Every file change means re-embed + re-index; if that job
  lags, retrieval silently returns stale results.

It is a full ETL pipeline that can drift away from reality.

`grep` has none of that. It reads the current bytes on disk, so there is no
index to go stale and no sync problem. There are no chunking decisions — you
match the actual text and pull as much surrounding context as you want. Results
are deterministic and explainable, and `ripgrep` is fast enough to scan large
repositories in the time the vector approach takes to warm up.

### Semantic search's advantage is smaller than it looks

The selling point of embeddings is matching *meaning* rather than surface words.
But for code, logs, config, and structured text, **the words *are* the
meaning.** Symbol names, error strings, config keys, and API routes are precise
lexical anchors. Embeddings are notoriously weak exactly here — bad at exact
matches, rare tokens, and specific identifiers — and will happily return
something "vibe-similar" but wrong while missing the one line you needed.

### The agent is what changes the equation

This is the crux. Classic RAG was **one-shot**: embed the query, grab top-k
chunks, stuff them in context, generate. Because you got one try, you *needed*
fuzzy semantic retrieval to compensate for not being able to iterate.

An agent removes that constraint. The model can issue a `grep`, read the
results, open a file, follow a reference, notice a naming convention, and search
again with better terms — the way a human explores an unfamiliar codebase. It
does not need one magic semantic query; it needs a fast, precise tool it can
call in a loop. The intelligence that used to live in the retrieval system has
moved into the model. This is why coding agents (Claude Code among them) lean on
`ripgrep` and file navigation instead of maintaining a vector index.

### Where the argument breaks down

"grep is *all* you need" is the provocative version of a more defensible claim.
Pure lexical search fails on the genuine **vocabulary gap**: ask "how do I
cancel" when the docs only say "terminate subscription" and there is no shared
token to match. Natural-language prose corpora — support articles, knowledge
bases, multilingual content — are where semantic search earns its keep. `grep`
also does not rank by relevance out of the box, and it assumes an agent that can
afford to iterate over a corpus small enough to scan.

**Honest formulation:** *for codebases and structured text, searched by an agent
that can iterate, lexical search matches or beats embeddings at a fraction of
the complexity.* Most production systems land on the middle ground — BM25
(basically `grep` that ranks) plus optional vector search as a fallback for
semantic-gap queries: hybrid retrieval.

---

## 2. Does the argument depend on an LLM in the *retrieve* stage?

Yes — this is the load-bearing assumption, and the argument mostly does **not**
survive if you require the retrieve stage to be LLM-free.

In classic RAG the pipeline is `embed(query) → ANN lookup → top-k → LLM`. The
LLM sits at the **end**, in generation. The retrieve stage is a dumb, cheap,
non-generative similarity computation — deliberately so, because retrieval must
be fast, stateless, and callable millions of times without paying for token
generation. The single embedded query has to be good enough on its only shot.

The grep-based approach **relocates the LLM from generation into the retrieve
stage.** The semantic capability the embedding model used to provide has not
been eliminated — it has been moved, and made more expensive per query (you now
pay generation tokens for each search-and-read cycle instead of a cheap vector
dot product).

Holding the constraint *"retrieval must not involve an LLM"*:

- **Operational wins survive completely.** No index to build, no embedding model
  to host, no vector DB, no sync/staleness, works on a fresh directory,
  deterministic, nothing leaves the machine. These are properties of `grep`
  itself.
- **Semantic capability does *not* survive.** Without an LLM *or* embeddings
  somewhere, you have raw lexical matching and are fully exposed to the
  vocabulary gap. You removed the semantic layer without providing a
  replacement.

An LLM in the retrieve loop is in fact **more** powerful than an embedding model
at the semantic job, not just a substitute. An embedding collapses the query to
a single fixed vector and matches by geometric proximity — one shot, no memory,
no reasoning. An agent can decompose the query, try multiple phrasings, learn
from failed searches, follow cross-references, and apply world knowledge about
likely synonyms. The primitive got dumber; the controller got much smarter.

This is also why the middle-ground systems exist. If you want good retrieval
*without* an LLM in the retrieve stage (the right choice at high QPS), bare
`grep` is not enough — you want embeddings, or at least **BM25**. BM25 is the
interesting case: lexical like `grep`, no neural model, but it adds relevance
ranking and term weighting — "grep that ranks," and it is LLM-free. But it is
still lexical, so it too fails the vocabulary-gap query. Only embeddings give you
semantic matching in a single non-LLM retrieve step.

**Direct answer:** the *complexity-reduction* half of the argument is
independent of the LLM. The *"and it still retrieves well"* half depends entirely
on there being an LLM in the retrieve loop.

---

## 3. So how does grep-based RAG do "semantic search"? Isn't grep just precise search?

Correct — and the honest answer is that **`grep` never does semantic search. It
can't.** `grep` is precise lexical matching, full stop. The *system as a whole*
approximates semantic search, not by making `grep` semantic, but by wrapping a
dumb precise tool in a smart loop.

- In a **vector system**, the semantics live in the *data structure*. You
  precompute an embedding that places "cancel" and "terminate" near each other,
  and the match step is where meaning gets resolved. The retrieval primitive
  itself is semantic.
- In a **grep system**, the retrieval primitive is not semantic and never
  becomes semantic. The semantics live in whatever *generates the queries*.

Concretely: the user asks "how do I cancel my subscription," but the docs only
say "terminate." A single `grep cancel` returns nothing — exactly as precise
search should. What the LLM does is refuse to accept that as the answer. It
reasons *"cancel is the user's word; the corpus might say terminate, deactivate,
end, close account, unsubscribe,"* and fires a `grep -i` for each. One hits. The
vocabulary gap got bridged **not by grep, but by the model generating the synonym
before grep ran.**

The semantic step happens at query-**generation** time, in the model's head,
rather than at match time in a vector space. `grep` did only what it always
does: find literal strings. The bridging an embedding model does geometrically
("these two vectors are close"), the LLM does generatively ("these two words
mean the same thing, let me search both"). Same semantic work — different
location, different mechanism.

The model, sitting in front of `grep`, does three things a raw pattern-matcher
cannot:

1. **Expand vocabulary** — turn one concept into many literal search terms.
2. **Iterate** — read that a search failed, try different words, follow a
   reference from one file to another, narrow or broaden based on results.
3. **Interpret** — judge whether a lexically-matched line is actually relevant to
   the intent, which `grep`'s binary match/no-match cannot.

None of that is retrieval technology. It is the model treating `grep` as a tool
the way a human developer does: you do not expect `grep` to understand you, you
expect to run it twenty times with different guesses until you find the thing.
The intelligence is in the guessing, and the guessing is semantic. Remove the
intelligent operator and you have no semantics at all — just a fast string
finder.

---

## 4. Proof of concept: LLM + grep, no embeddings, no vector DB

The PoC below demonstrates the mechanism end to end. The demo corpus is
deliberately rigged with the vocabulary gap: **none of the files contain the
word "cancel"** — they only say *terminate*, *deactivate*, and *close*. A naive
`grep cancel` returns nothing; watch the model bridge the gap by generating
synonyms and searching again.

The only retrieval primitive is the real `grep` (or `rg`) binary. There is no
embedding model and no vector database anywhere in the code.

### How to run

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python grep_rag_poc.py "how do I cancel my subscription?"
```

### Expected trace

```
grep> 'cancel'        [MISS]
grep> 'terminate'     [HIT ]
grep> 'deactivate'    [HIT ]
ANSWER: To end your subscription, go to Settings -> Plan and click
        "Deactivate account"... (billing.md, accounts.md)
```

The `cancel → terminate` jump on the first two lines is the entire thesis: `grep`
contributed only speed and precision; the LLM contributed the synonym *before*
`grep` ran.

### The code

```python
#!/usr/bin/env python3
"""
grep_rag_poc.py  --  A minimal "LLM + grep" RAG system.

The whole point of this PoC is to show the mechanism:

    grep NEVER does semantic search. It only does precise, literal matching.
    The *LLM* supplies the semantics -- it expands the user's word into
    likely synonyms, fires precise greps for each, reads what came back,
    and searches again until it finds the answer.

There is NO embedding model and NO vector database anywhere in here.
The only retrieval primitive is the real `grep` (or `rg`) binary on disk.

The demo corpus is rigged to expose the vocabulary gap:
    the user asks how to "cancel" their subscription,
    but the docs only ever say "terminate" / "deactivate" / "close".
A single `grep cancel` returns nothing. Watch the model bridge that gap.

------------------------------------------------------------------
Run it:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python grep_rag_poc.py "how do I cancel my subscription?"
------------------------------------------------------------------
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

try:
    from anthropic import Anthropic
except ImportError:
    sys.exit("Please `pip install anthropic` first.")

MODEL = "claude-sonnet-4-6"          # current, active tool-use model string
CORPUS_DIR = Path(__file__).parent / "corpus"
MAX_TURNS = 8                        # safety cap on the search loop


# --------------------------------------------------------------------------
# 1. Build a tiny demo corpus on disk (only if it isn't there already).
#    Note the deliberate vocabulary gap: NONE of these files contain the
#    word "cancel". They say terminate / deactivate / close instead.
# --------------------------------------------------------------------------
CORPUS = {
    "billing.md": """# Billing & Subscriptions

## Ending your plan
To terminate your subscription, open Settings -> Plan and press
"Deactivate account". Your plan stays active until the end of the
current billing period; after that you are not charged again.

Refunds are only issued for annual plans terminated within 14 days
of renewal. Monthly plans are non-refundable once the period starts.
""",
    "accounts.md": """# Account Management

## Closing an account
Closing your account is permanent and removes all stored data after
30 days. This is different from merely deactivating a subscription:
a closed account cannot be recovered.

To close an account, contact support with the subject line CLOSE ACCOUNT.
""",
    "faq.md": """# FAQ

Q: Can I pause instead of stopping entirely?
A: Yes. A paused subscription keeps your data but suspends billing for
up to 3 months. After that it is automatically terminated.

Q: What happens to my invoices?
A: Past invoices remain downloadable even after a plan is deactivated.
""",
}


def build_corpus() -> None:
    CORPUS_DIR.mkdir(exist_ok=True)
    for name, text in CORPUS.items():
        (CORPUS_DIR / name).write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# 2. The ONLY retrieval tool: real grep. No neural anything.
#    Prefers ripgrep (`rg`) if installed, falls back to POSIX grep.
# --------------------------------------------------------------------------
def run_grep(pattern: str, context: int = 1) -> str:
    """Case-insensitive, recursive literal-ish search over the corpus.
    Returns matching lines as `file:lineno: text`, or a 'no matches' note."""
    if shutil.which("rg"):
        cmd = ["rg", "-i", "-n", f"-C{context}", "--no-heading", pattern, str(CORPUS_DIR)]
    else:
        cmd = ["grep", "-r", "-i", "-n", f"-C{context}", pattern, str(CORPUS_DIR)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout.strip()
    if not out:
        return f"(no matches for pattern: {pattern!r})"
    # Trim absolute paths down to filenames to keep the context tidy.
    return out.replace(str(CORPUS_DIR) + "/", "")


GREP_TOOL = {
    "name": "grep",
    "description": (
        "Search the documentation corpus for a literal, case-insensitive "
        "pattern. This is EXACT text matching only -- it has no understanding "
        "of meaning or synonyms. If a search returns no matches, try other "
        "words that could express the same concept."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The literal string / regex to search for.",
            }
        },
        "required": ["pattern"],
    },
}


# --------------------------------------------------------------------------
# 3. The agentic retrieval loop.
#    LLM -> emits a grep -> we run it -> feed results back -> repeat -> answer.
# --------------------------------------------------------------------------
SYSTEM = (
    "You answer user questions using ONLY the documentation corpus, which you "
    "can access solely through the `grep` tool. grep does exact literal "
    "matching with no notion of meaning, so YOU are responsible for the "
    "semantics: translate the user's wording into the terms the docs are "
    "likely to actually use, and if a search comes back empty, reason about "
    "synonyms and try again. Keep searching until you have enough to answer. "
    "When you answer, cite the file names you relied on."
)


def answer(question: str) -> None:
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages = [{"role": "user", "content": question}]

    print(f"\n\033[1mUSER:\033[0m {question}\n")
    print("--- retrieval loop (LLM in the driver's seat) ---\n")

    for turn in range(MAX_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            tools=[GREP_TOOL],
            messages=messages,
        )

        # Surface any thinking-out-loud text the model emitted this turn.
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                print(f"\033[90m[model] {block.text.strip()}\033[0m")

        if resp.stop_reason != "tool_use":
            # No more searches requested -> this turn is the final answer.
            final = "".join(b.text for b in resp.content if b.type == "text")
            print(f"\n\033[1m\033[92mANSWER:\033[0m {final.strip()}\n")
            return

        # Record the assistant turn, then execute each grep it asked for.
        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                pattern = block.input["pattern"]
                result = run_grep(pattern)
                hit = "HIT " if not result.startswith("(no matches") else "MISS"
                print(f"  \033[93mgrep> {pattern!r:<28}\033[0m [{hit}]")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})

    print("\n(hit the search-loop cap without a final answer)")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY in your environment first.")
    build_corpus()
    q = " ".join(sys.argv[1:]) or "how do I cancel my subscription?"
    answer(q)
```

### What this is and isn't

- It genuinely shells out to the system `grep` (preferring `ripgrep` if
  present), so the retrieval primitive is authentically lexical — no fuzzy
  matching quietly reimplemented in Python.
- The cost profile is the tradeoff from Section 2: you pay generation tokens for
  every search-and-read cycle instead of one cheap vector lookup. Fine for a
  coding agent iterating over a bounded corpus; not fine for high-QPS serving.
- To feel the failure mode, point it at a large `corpus/` and ask something whose
  answer needs ranking across hundreds of matches — that is where BM25 or
  embeddings start earning their place.

---

## Summary

| | Classic (one-shot) RAG | LLM + grep (agentic) |
|---|---|---|
| Retrieval primitive | vector similarity (semantic) | `grep` (lexical, precise) |
| Where semantics live | in the data structure (embeddings) | in the query generator (the LLM) |
| LLM position | generation stage only | retrieve loop **and** generation |
| Infra | embedding model + vector DB + sync ETL | none (reads bytes on disk) |
| Cost per query | cheap vector dot product | generation tokens per search cycle |
| Vocabulary gap | bridged geometrically | bridged by synonym generation |
| Best for | high-QPS prose search | agents over code / structured text |

The grep pitch is not "you don't need semantic retrieval." It is *"let the LLM do
the semantic retrieval interactively instead of precomputing it into vectors."*
The word "semantic" never attaches to `grep` — it attaches to the thing driving
it.
