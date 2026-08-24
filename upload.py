"""One-off bulk upload: push every articles/*.md file into the OpenAI Vector
Store, wait for processing, and log file + chunk counts. For daily delta
syncs, use main.py instead.
"""

import sys
from pathlib import Path

from vectorstore import client, estimate_chunks, get_or_create_store

ARTICLES_DIR = Path(__file__).parent / "articles"


def main():
    files = sorted(ARTICLES_DIR.glob("*.md"))
    if not files:
        sys.exit("No articles/*.md found — run scraper.py first.")

    vs = get_or_create_store()
    print(f"Vector store: {vs.id}")

    print(f"Uploading {len(files)} files...")
    batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vs.id,
        files=[open(f, "rb") for f in files],
    )
    print(f"Batch status: {batch.status}")
    print(f"File counts: {batch.file_counts}")

    n_files, total_bytes, est_chunks = estimate_chunks(vs.id)
    print(f"Files embedded: {n_files}, total {total_bytes} bytes, ~{est_chunks} chunks (est.)")


if __name__ == "__main__":
    main()
