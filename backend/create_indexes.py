"""
One-shot script: create all performance indexes on a target MongoDB cluster.

Usage:
    MONGO_URL="mongodb+srv://...@poppiconni-prod.../poppiconni_prod?..." \
    DB_NAME="poppiconni_prod" \
    python3 create_indexes.py

All create_index calls are idempotent: if an equivalent index exists the call
is a no-op. If an index with the same name but different spec exists, MongoDB
raises an error and we log + skip, leaving the cluster state intact.

This script is designed to be run against both Atlas DEV and Atlas PROD.
It does NOT read credentials from the file system; it only reads env vars.
"""
from __future__ import annotations

import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient


PERF_INDEXES = [
    ("illustrations", [("id", 1), ("isPublished", 1)], {"name": "ix_id_isPublished"}),
    ("illustrations", [("isPublished", 1)],            {"name": "ix_isPublished"}),
    ("posters",       [("id", 1), ("status", 1)],      {"name": "ix_id_status"}),
    ("posters",       [("status", 1)],                 {"name": "ix_status"}),
    ("books",         [("id", 1)],                     {"name": "ix_id"}),
    ("books",         [("slug", 1)],                   {"name": "ix_slug"}),
    ("book_scenes",   [("bookId", 1), ("sceneNumber", 1)], {"name": "ix_bookId_sceneNumber"}),
    ("book_scenes",   [("id", 1), ("bookId", 1)],      {"name": "ix_id_bookId"}),
    ("bundles",       [("id", 1)],                     {"name": "ix_id"}),
    ("games",         [("id", 1)],                     {"name": "ix_id"}),
    ("games",         [("slug", 1)],                   {"name": "ix_slug"}),
    ("themes",        [("id", 1)],                     {"name": "ix_id"}),
    ("game_level_backgrounds", [("id", 1)],            {"name": "ix_id"}),
    ("generation_styles", [("id", 1), ("userId", 1)],  {"name": "ix_id_userId"}),
    ("character_images", [("trait", 1)],               {"name": "ix_trait"}),
    ("reviews",       [("is_approved", 1)],            {"name": "ix_is_approved"}),
    ("reading_progress", [("bookId", 1), ("visitorId", 1)], {"name": "ix_bookId_visitorId"}),
    ("download_limits", [("key", 1)],                  {"name": "ix_key"}),
    ("download_limits", [("expiresAt", 1)],            {"name": "ix_expiresAt_ttl", "expireAfterSeconds": 0}),
    ("admins",        [("email", 1)],                  {"name": "ix_email", "unique": True}),
    ("site_settings", [("id", 1)],                     {"name": "ix_id"}),
]


async def main() -> int:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        print("ERROR: MONGO_URL and DB_NAME must be set", file=sys.stderr)
        return 2

    # Never print full connection string; mask password segment if shown.
    masked = mongo_url
    try:
        if "@" in mongo_url and "://" in mongo_url:
            scheme, rest = mongo_url.split("://", 1)
            creds, host = rest.split("@", 1)
            masked = f"{scheme}://{creds.split(':')[0]}:***@{host}"
    except Exception:
        masked = "***"
    print(f"[indexes] Connecting to {masked} db={db_name}")

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=15000)
    db = client[db_name]
    await db.command("ping")

    created, existing, failed = 0, 0, 0
    for coll, keys, opts in PERF_INDEXES:
        name = opts.get("name")
        try:
            before = {i.get("name") for i in await db[coll].list_indexes().to_list(1000)}
            await db[coll].create_index(keys, **opts)
            after = {i.get("name") for i in await db[coll].list_indexes().to_list(1000)}
            if name in (after - before):
                print(f"  + created  {coll}.{name}")
                created += 1
            else:
                print(f"  = existed  {coll}.{name}")
                existing += 1
        except Exception as e:
            print(f"  ! failed   {coll}.{name} -> {str(e)[:100]}")
            failed += 1

    print(f"\nSummary: created={created} existed={existing} failed={failed}")
    client.close()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
