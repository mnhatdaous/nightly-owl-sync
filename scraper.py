"""Scrape support.optisigns.com articles via the Zendesk Help Center API
and convert them to clean Markdown files (<slug>.md) in ./articles.
"""

import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

BASE = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
OUT_DIR = Path(__file__).parent / "articles"
MAX_ARTICLES = 10_000  # all articles (requirement: >= 30)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:80] or "article"


def clean_html(body: str) -> str:
    soup = BeautifulSoup(body, "html.parser")
    # Remove non-content elements (nav, ads, scripts, embedded widgets)
    for tag in soup(["script", "style", "nav", "iframe", "form", "footer", "header"]):
        tag.decompose()
    return str(soup)


def to_markdown(article: dict) -> str:
    body_md = md(clean_html(article["body"] or ""), heading_style="ATX", bullets="-")
    # Collapse 3+ blank lines into one
    body_md = re.sub(r"\n{3,}", "\n\n", body_md).strip()
    header = (
        f"# {article['title']}\n\n"
        f"Article URL: {article['html_url']}\n"
        f"Last updated: {article['updated_at']}\n\n---\n\n"
    )
    return header + body_md + "\n"


def fetch_articles(limit: int):
    url = f"{BASE}?per_page=100"
    fetched = []
    while url and len(fetched) < limit:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for a in data["articles"]:
            if a.get("draft") or not a.get("body"):
                continue
            fetched.append(a)
            if len(fetched) >= limit:
                break
        url = data.get("next_page")
    return fetched


def main():
    OUT_DIR.mkdir(exist_ok=True)
    articles = fetch_articles(MAX_ARTICLES)
    index = {}
    for a in articles:
        slug = slugify(a["title"])
        path = OUT_DIR / f"{slug}.md"
        path.write_text(to_markdown(a), encoding="utf-8")
        index[slug] = {"id": a["id"], "url": a["html_url"], "updated_at": a["updated_at"]}
        print(f"saved {path.name}")
    (OUT_DIR / "_index.json").write_text(json.dumps(index, indent=2))
    print(f"\nDone: {len(articles)} articles saved to {OUT_DIR}")


if __name__ == "__main__":
    sys.exit(main())
