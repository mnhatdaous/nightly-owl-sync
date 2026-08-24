"""Daily job: re-scrape OptiSigns support articles and sync the delta to the
OpenAI Vector Store.

Delta detection is stateless: each vector-store file carries attributes
{slug, hash} where hash is the sha256 of the article's Markdown. On each run
we re-scrape, compare hashes, and only upload new/changed articles
(deleting the stale copy of changed ones). Logs: added, updated, skipped.
"""

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from scraper import MAX_ARTICLES, fetch_articles, slugify, to_markdown
from vectorstore import delete_file, existing_files, get_or_create_store, upload_markdown

DOCS_DIR = Path(__file__).parent / "docs"
SUMMARY_LOG = DOCS_DIR / "logs.json"

log = logging.getLogger("optibot")


def record_summary(added: int, updated: int, skipped: int):
    """Append a summary entry to docs/logs.json."""
    DOCS_DIR.mkdir(exist_ok=True)

    raw = SUMMARY_LOG.read_text().strip() if SUMMARY_LOG.exists() else ""
    entries = json.loads(raw) if raw else []

    entries.append(
        {
            "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "added": added,
            "updated": updated,
            "skipped": skipped,
        }
    )

    SUMMARY_LOG.write_text(json.dumps(entries, indent=2))


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    vs = get_or_create_store()
    log.info("Vector store: %s", vs.id)

    articles = fetch_articles(MAX_ARTICLES)
    log.info("Scraped %d articles", len(articles))

    existing = existing_files(vs.id)

    added = updated = skipped = 0

    for article in articles:
        slug = slugify(article["title"])
        content = to_markdown(article)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        if slug not in existing:
            upload_markdown(vs.id, slug, content, content_hash)
            added += 1

        elif existing[slug][1] != content_hash:
            delete_file(vs.id, existing[slug][0])
            upload_markdown(vs.id, slug, content, content_hash)
            updated += 1

        else:
            skipped += 1

    log.info("added: %d, updated: %d, skipped: %d", added, updated, skipped)

    record_summary(added, updated, skipped)

    return 0


if __name__ == "__main__":
    sys.exit(main())
