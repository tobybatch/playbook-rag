#!/usr/bin/env python3
"""
Crawls playbook.dxw.com and saves each page as clean text to data/raw/.

Run this on a machine with normal internet access (your laptop, etc).
It discovers pages by following internal links from the homepage (the
Playbook's nav links out to every doc), so re-running it later will pick
up new/removed pages automatically.

Usage:
    python3 crawler.py                 # crawl the whole site
    python3 crawler.py --max-pages 20  # crawl only the first 20 pages (for a quick test)
"""
import argparse
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_URL = "https://playbook.dxw.com"
RAW_DIR = os.path.join(os.path.dirname(__file__), "data", "raw")
USER_AGENT = "playbook-rag-crawler/1.0 (personal use; contact: internal dxw tool)"
REQUEST_DELAY_SECONDS = 0.5  # be polite - don't hammer the site


def is_internal_doc_link(href: str) -> bool:
    if not href:
        return False
    joined = urljoin(BASE_URL, href)
    parsed = urlparse(joined)
    if parsed.netloc != urlparse(BASE_URL).netloc:
        return False
    # The Playbook (an Outline wiki) publishes pages under /doc/<slug>-<id>
    return parsed.path.startswith("/doc/")


def normalise(url: str) -> str:
    joined = urljoin(BASE_URL, url)
    parsed = urlparse(joined)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def fetch(session: requests.Session, url: str) -> requests.Response | None:
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        print(f"  ! failed to fetch {url}: {e}")
        return None


def extract_page(html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else (soup.title.get_text(strip=True) if soup.title else url)

    # Drop elements that are never part of the actual document content.
    for selector in ["nav", "header", "footer", "script", "style", "[role='navigation']"]:
        for tag in soup.select(selector):
            tag.decompose()

    # Outline (the wiki this site runs on) renders the document body inside
    # a <main> or an element with a data-testid/class hinting at the editor.
    # Fall back to the whole body if none of these are found.
    content_root = (
        soup.find("main")
        or soup.find(attrs={"class": re.compile(r"(document|editor|content)", re.I)})
        or soup.body
    )
    if content_root is None:
        return None

    text = content_root.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    if len(text) < 40:
        # Likely a nav-only or empty page - skip it.
        return None

    return {"url": url, "title": title, "text": text}


def discover_links(html: str) -> set[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()
    for a in soup.find_all("a", href=True):
        if is_internal_doc_link(a["href"]):
            links.add(normalise(a["href"]))
    return links


def crawl(max_pages: int | None = None) -> list[dict]:
    os.makedirs(RAW_DIR, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    to_visit = {BASE_URL}
    visited = set()
    pages = []

    with tqdm(desc="crawling", unit="page") as pbar:
        while to_visit:
            if max_pages is not None and len(visited) >= max_pages:
                break
            url = to_visit.pop()
            if url in visited:
                continue
            visited.add(url)

            resp = fetch(session, url)
            time.sleep(REQUEST_DELAY_SECONDS)
            if resp is None:
                continue

            # Always harvest links, even from the homepage, so we discover
            # every doc even though the homepage itself isn't saved as a doc.
            to_visit |= discover_links(resp.text) - visited

            if url != BASE_URL:
                page = extract_page(resp.text, url)
                if page:
                    pages.append(page)
                    slug = urlparse(url).path.rstrip("/").split("/")[-1] or "index"
                    out_path = os.path.join(RAW_DIR, f"{slug}.json")
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(page, f, ensure_ascii=False, indent=2)

            pbar.update(1)
            pbar.set_postfix(queued=len(to_visit), saved=len(pages))

    return pages


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=None, help="Stop after crawling this many pages (useful for a quick test)")
    args = parser.parse_args()

    pages = crawl(max_pages=args.max_pages)
    print(f"\nDone. Saved {len(pages)} pages to {os.path.abspath(RAW_DIR)}")
