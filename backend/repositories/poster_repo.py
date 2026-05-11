"""Repository for the ``posters`` collection.

Pure data access. GridFS uploads/deletes for poster image and PDF stay in
``server.py`` for this batch — the repository only exposes the file IDs
so the route can perform the side-effects (delete-on-poster-delete,
upload-replace flows).
"""
from datetime import datetime, timezone

from core.database import db

from .base import EXCLUDE_ID


PAGE_LIMIT = 100


# --- Public lookups -----------------------------------------------------------

async def list_published() -> list[dict]:
    """Published posters for the public site, newest first."""
    return await db.posters.find(
        {"status": "published"}, EXCLUDE_ID
    ).sort("createdAt", -1).to_list(PAGE_LIMIT)


async def find_published_by_id(poster_id: str) -> dict | None:
    """Return a single published poster (used by public detail page)."""
    return await db.posters.find_one(
        {"id": poster_id, "status": "published"}, EXCLUDE_ID
    )


# Variant WITH BSON _id, used by media endpoints that still live in
# server.py to access the GridFS file IDs without losing the doc.
async def find_published_raw(poster_id: str) -> dict | None:
    """Like :func:`find_published_by_id` but keeps the ``_id`` field."""
    return await db.posters.find_one({"id": poster_id, "status": "published"})


# --- Admin lookups ------------------------------------------------------------

async def list_all() -> list[dict]:
    """All posters for admin (any status), newest first."""
    return await db.posters.find({}, EXCLUDE_ID).sort("createdAt", -1).to_list(PAGE_LIMIT)


async def find_by_id(poster_id: str) -> dict | None:
    """Admin view of one poster."""
    return await db.posters.find_one({"id": poster_id}, EXCLUDE_ID)


async def find_raw(poster_id: str) -> dict | None:
    """Admin lookup that keeps ``_id`` (used by GridFS cleanup paths)."""
    return await db.posters.find_one({"id": poster_id})


# --- Mutations ----------------------------------------------------------------

async def insert(poster_dict: dict) -> dict:
    """Insert a new poster. Mutates the dict (Mongo adds ``_id``); we pop it."""
    await db.posters.insert_one(poster_dict)
    poster_dict.pop("_id", None)
    return poster_dict


async def update_fields(poster_id: str, fields: dict) -> int:
    """Apply a partial update. Returns modified_count."""
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    result = await db.posters.update_one({"id": poster_id}, {"$set": fields})
    return result.modified_count


async def set_download_enabled(poster_id: str, new_value: bool) -> int:
    """Persist a new ``downloadEnabled`` flag. Returns modified_count."""
    result = await db.posters.update_one(
        {"id": poster_id},
        {"$set": {
            "downloadEnabled": new_value,
            "updatedAt": datetime.now(timezone.utc),
        }},
    )
    return result.modified_count


async def increment_download_count(poster_id: str) -> None:
    """Atomic +1 on the ``downloadCount`` counter."""
    await db.posters.update_one({"id": poster_id}, {"$inc": {"downloadCount": 1}})


async def delete(poster_id: str) -> int:
    """Delete a poster document. Returns deleted_count."""
    result = await db.posters.delete_one({"id": poster_id})
    return result.deleted_count


# --- Stats --------------------------------------------------------------------

async def stats_summary() -> dict:
    """Counts and total downloads used by the admin stats page."""
    total = await db.posters.count_documents({})
    published = await db.posters.count_documents({"status": "published"})
    drafts = await db.posters.count_documents({"status": "draft"})
    free = await db.posters.count_documents({"status": "published", "price": 0})

    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$downloadCount"}}}]
    agg = await db.posters.aggregate(pipeline).to_list(1)
    total_downloads = agg[0]["total"] if agg else 0

    return {
        "total": total,
        "published": published,
        "drafts": drafts,
        "free": free,
        "paid": published - free,
        "totalDownloads": total_downloads,
    }
