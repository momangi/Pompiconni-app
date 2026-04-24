"""
Phase 2 batch migration: generate responsive variants for every ORIGINAL
image already stored in GridFS.

Safety guarantees:
- Originals are NEVER modified or deleted. Only new variants are uploaded.
- Idempotent: if a variant for (source, size, format) already exists it is
  skipped. Re-running the script is safe.
- Non-image files (PDF, etc.) are ignored based on content_type.
- The script never prints the connection string.

Usage:
    MONGO_URL=... DB_NAME=... python3 migrate_variants.py           # DEV or PROD
    MONGO_URL=... DB_NAME=... python3 migrate_variants.py --dry-run
"""
from __future__ import annotations

import asyncio
import os
import sys
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

from media_pipeline import ensure_variants


def _is_image_metadata(meta: dict) -> bool:
    if not meta:
        return False
    ct = (meta.get("content_type") or "").lower()
    if ct.startswith("image/"):
        return True
    # some legacy uploads may not have content_type; rely on filename extension
    filename = meta.get("filename") or ""
    return any(filename.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp"))


async def main() -> int:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    dry_run = "--dry-run" in sys.argv

    if not mongo_url or not db_name:
        print("ERROR: MONGO_URL and DB_NAME must be set", file=sys.stderr)
        return 2

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=15000)
    db = client[db_name]
    gridfs_bucket = AsyncIOMotorGridFSBucket(db)
    await db.command("ping")
    print(f"[migrate] db={db_name} dry_run={dry_run}")
    print()

    # Find all ORIGINALS (not variants). A document is considered an original
    # when metadata.variant is missing or equal to "original".
    originals_query = {
        "$or": [
            {"metadata.variant": {"$exists": False}},
            {"metadata.variant": "original"},
        ]
    }

    originals = []
    async for doc in db["fs.files"].find(originals_query):
        meta = doc.get("metadata") or {}
        if not _is_image_metadata({**meta, "filename": doc.get("filename", "")}):
            continue
        originals.append(doc)

    print(f"[migrate] found {len(originals)} originals to process")
    print()

    total_created = 0
    total_skipped_existing = 0
    total_errors = 0
    total_original_bytes = 0
    total_variant_bytes = 0

    for idx, doc in enumerate(originals, 1):
        fid = doc["_id"]
        fname = doc.get("filename", "?")
        size = doc.get("length", 0)
        total_original_bytes += size
        print(f"[{idx}/{len(originals)}] {fname} ({size:,} bytes)")

        if dry_run:
            print("    (dry-run — skipping)")
            continue

        report = await ensure_variants(
            db=db,
            gridfs_bucket=gridfs_bucket,
            source_file_id=fid,
            skip_if_exists=True,
        )
        for v in report.get("variants", []):
            if v.get("created"):
                total_created += 1
                if v.get("bytes"):
                    total_variant_bytes += v["bytes"]
                print(f"    + {v['size']}/{v['format']}  {v['bytes']:,} bytes")
            else:
                total_skipped_existing += 1
                print(f"    = {v['size']}/{v['format']}  already exists")
        for err in report.get("errors", []):
            total_errors += 1
            print(f"    ! {err}")
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  originals processed:   {len(originals)}")
    print(f"  variants created:      {total_created}")
    print(f"  variants pre-existing: {total_skipped_existing}")
    print(f"  errors:                {total_errors}")
    print(f"  original total bytes:  {total_original_bytes:,} ({total_original_bytes/(1024*1024):.2f} MB)")
    print(f"  variants total bytes:  {total_variant_bytes:,} ({total_variant_bytes/(1024*1024):.2f} MB)")

    client.close()
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
