"""Shared OpenAI Vector Store helpers used by both upload.py (one-off bulk
upload) and main.py (daily delta sync).
"""

import io

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

VECTOR_STORE_NAME = "optibot-support-articles"

client = OpenAI()


def get_or_create_store():
    for vs in client.vector_stores.list(limit=100):
        if vs.name == VECTOR_STORE_NAME:
            return vs
    return client.vector_stores.create(name=VECTOR_STORE_NAME)


def existing_files(vs_id):
    """Map slug -> (vector_store_file_id, hash) from file attributes."""
    out = {}
    for vf in client.vector_stores.files.list(vector_store_id=vs_id, limit=100):
        attrs = vf.attributes or {}
        if "slug" in attrs:
            out[attrs["slug"]] = (vf.id, attrs.get("hash", ""))
    return out


def upload_markdown(vs_id, slug, content, content_hash=None):
    f = client.files.create(
        file=(f"{slug}.md", io.BytesIO(content.encode("utf-8"))),
        purpose="assistants",
    )
    client.vector_stores.files.create_and_poll(
        vector_store_id=vs_id,
        file_id=f.id,
        attributes={"slug": slug, "hash": content_hash} if content_hash else {"slug": slug},
    )


def delete_file(vs_id, vector_store_file_id):
    client.vector_stores.files.delete(vector_store_id=vs_id, file_id=vector_store_file_id)
    client.files.delete(vector_store_file_id)


def estimate_chunks(vs_id):
    """OpenAI doesn't expose exact chunk counts, so estimate from usage_bytes
    against the auto strategy (800-token chunks, 400-token overlap ≈ 1600 bytes/chunk)."""
    n_files = total_bytes = est_chunks = 0
    for vf in client.vector_stores.files.list(vector_store_id=vs_id, limit=100):
        n_files += 1
        total_bytes += vf.usage_bytes or 0
        est_chunks += max(1, round((vf.usage_bytes or 0) / (400 * 4)))
    return n_files, total_bytes, est_chunks
