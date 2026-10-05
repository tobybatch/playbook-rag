# Playbook RAG (Spike)

CLI tool to answer questions using dxw's Playbook (`playbook.dxw.com`) via RAG with Claude. Simple pipeline: crawl -> chunk & embed locally -> retrieve & query Claude.

## Quickstart

```bash
# Setup
cd playbook-rag
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# Run
python3 crawler.py             # 1. Scrape site (or skip to use 6 sample pages in data/raw)
python3 build_index.py         # 2. Chunk & embed to Chroma DB
python3 ask.py "Holiday info?" # 3. Query (or run without args for interactive mode)


## How It Works

1. **`crawler.py`**: Scrapes pages to `data/raw/*.json`.
2. **`build_index.py`**: Splits text by headings/paragraphs (with overlap). Embeds using `all-MiniLM-L6-v2` (`sentence-transformers`) into a local Chroma vector DB (`data/index/`).
3. **`ask.py`**: Embeds your query, fetches top 6 matching chunks from Chroma, feeds them to `claude-sonnet-5` with strict instructions to answer using *only* the retrieved context and cite sources.

## Config / Tweaks

Adjust constants in `build_index.py` or `ask.py`:

* `MAX_CHUNK_CHARS` / `CHUNK_OVERLAP_CHARS`: Chunking behavior.
* `TOP_K`: Number of context chunks pulled per query.
* `CLAUDE_MODEL`: Swap the underlying LLM.

## Project Structure

```text
crawler.py       -> Scrapes site into data/raw/
build_index.py   -> Chunks raw JSONs + embeds into Chroma
ask.py           -> CLI query / interactive chat interface
data/raw/        -> Saved JSON pages (6 sample pages pre-loaded)
data/index/      -> Local Chroma DB directory

```
