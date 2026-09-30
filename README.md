# Playbook RAG

A personal question-answering tool over dxw's Playbook (playbook.dxw.com), using
retrieval-augmented generation (RAG): your questions are answered by Claude,
grounded only in the actual Playbook content, with sources cited.

Nothing here fine-tunes or trains a model. It works by:
1. Crawling the Playbook and saving each page as text (`crawler.py`)
2. Splitting that text into chunks and embedding them into a local vector
   database (`build_index.py`)
3. At question time, finding the most relevant chunks and handing them to
   Claude to answer from (`ask.py`)

Because it's just retrieval + an existing model, re-running steps 1-2
whenever the Playbook changes keeps it current - no retraining involved.

## A note on where this was built

This project was built and tested inside a sandboxed cloud environment
that blocks outbound requests to arbitrary websites (including
playbook.dxw.com itself, and the Hugging Face model hub used to download
the embedding model). Every piece of code was tested as far as that
allowed:

- `build_index.py`'s chunking logic was run against 6 real pages pulled
  from the live Playbook (included in `data/raw/` so you have some data to
  try immediately)
- The vector storage/retrieval wiring was verified end-to-end
- `crawler.py`'s HTML parsing/link-discovery was verified against a
  synthetic test page
- `ask.py`'s retrieval + prompt-building + Claude API call was verified
  end-to-end with a mocked Claude client

What could **not** be run inside that sandbox: an actual live crawl of
playbook.dxw.com (155+ pages), and downloading the real embedding model
from Hugging Face. Both are ordinary outbound HTTPS requests that will
work fine on a normal machine (your laptop, most work machines, etc) -
run the three commands below there to build the complete, real thing.

## Setup

You'll need Python 3.10+ and an Anthropic API key (from
[console.anthropic.com](https://console.anthropic.com)).

```bash
cd playbook-rag
python3 -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...   # on Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

Run these in order. Each one can be re-run any time the Playbook changes.

```bash
# 1. Crawl the whole site (takes a few minutes; add --max-pages 10 to test quickly first)
python3 crawler.py

# 2. Chunk and embed everything into a local vector database
#    (first run downloads a small embedding model, ~90MB)
python3 build_index.py

# 3. Ask questions
python3 ask.py "How much holiday do I get?"

# or run it as an interactive chat:
python3 ask.py
```

A handful of real pages are already included in `data/raw/` so you can try
step 2 and 3 immediately, before running the full crawl - though the
index that builds from just 6 pages will only answer questions about
those specific pages (holiday, AI usage guidance, flexible working,
onboarding, working securely, and mission/values). Run `crawler.py` for
real to get the complete Playbook.

## How it works, in more detail

- **Chunking** (`build_index.py`): each page is split on markdown-style
  headings, and any section still too long is further split by paragraph,
  with a little overlap so context isn't lost across a chunk boundary.
- **Embeddings**: chunks are embedded locally using the free
  `all-MiniLM-L6-v2` model via `sentence-transformers` - no API key or
  per-query cost for this part.
- **Vector store**: embeddings are stored in [Chroma](https://www.trychroma.com/),
  a lightweight local vector database - just a folder on disk
  (`data/index/`), no server to run.
- **Retrieval + generation** (`ask.py`): your question is embedded the
  same way, the 6 most similar chunks are pulled from Chroma, and those
  chunks plus your question are sent to Claude (`claude-sonnet-5`) with
  instructions to answer only from the provided excerpts and cite sources.

## Tuning

A few things worth adjusting if answers feel off, in `build_index.py` /
`ask.py`:

- `MAX_CHUNK_CHARS` / `CHUNK_OVERLAP_CHARS` - chunk size and overlap
- `TOP_K` in `ask.py` - how many chunks get pulled per question
- `CLAUDE_MODEL` in `ask.py` - swap for a different Claude model if you
  want

## Files

```
crawler.py       - crawls playbook.dxw.com -> data/raw/*.json
build_index.py   - chunks + embeds data/raw/ -> data/index/ (Chroma DB)
ask.py           - retrieval + Claude Q&A
data/raw/        - one JSON file per crawled page (url, title, text)
data/index/      - the Chroma vector database (created by build_index.py)
scripts/seed_sample.py - the script that seeded the 6 sample pages (safe to ignore)
```
