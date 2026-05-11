"""Repository for the ``illustrations`` collection.

All public/admin reads now use the ``EXCLUDE_ID`` projection so the BSON
``_id`` never leaves the data access layer. This implements the
"R1 fix" approved as a security cleanup for Fase 4B Batch 3.

Read-helpers that combine with ``download_events`` aggregation live here
too, since the counter is part of the illustration response shape.
"""
from datetime import datetime, timezone
from typing import Optional

from core.database import db

from .base import EXCLUDE_ID


PAGE_LIMIT_LISTS = 1000
PAGE_LIMIT_EVENTS = 1000


# --- Reads (R1 fix: never expose _id) ----------------------------------------

async def list_by_filter(
    query: dict,
    limit: int = PAGE_LIMIT_LISTS,
) -> list[dict]:
    """Return illustrations matching ``query`` without ``_id``."""
    return await db.illustrations.find(query, EXCLUDE_ID).to_list(limit)


async def find_by_id(illustration_id: str) -> dict | None:
    return await db.illustrations.find_one({"id": illustration_id}, EXCLUDE_ID)


async def find_published_by_id(illustration_id: str) -> dict | None:
    return await db.illustrations.find_one(
        {"id": illustration_id, "isPublished": True}, EXCLUDE_ID
    )


async def find_raw(illustration_id: str) -> dict | None:
    """Lookup that keeps the BSON ``_id`` (used by media routes and counters)."""
    return await db.illustrations.find_one({"id": illustration_id})


async def find_raw_published(illustration_id: str) -> dict | None:
    """Published-only raw lookup (used by media routes that still live in
    ``server.py`` and need the GridFS ``imageFileId`` / ``pdfFileId``).
    """
    return await db.illustrations.find_one(
        {"id": illustration_id, "isPublished": True}
    )


# --- Counter aggregations ----------------------------------------------------

async def real_download_counts(limit: int = PAGE_LIMIT_EVENTS) -> dict[str, int]:
    """Build a ``{illustrationId: count}`` map from ``download_events``."""
    counts: dict[str, int] = {}
    pipeline = [{"$group": {"_id": "$illustrationId", "count": {"$sum": 1}}}]
    events = await db.download_events.aggregate(pipeline).to_list(limit)
    for e in events:
        counts[e["_id"]] = e["count"]
    return counts


async def real_download_count_for(illustration_id: str) -> int:
    return await db.download_events.count_documents({"illustrationId": illustration_id})


async def insert_download_event(illustration_id: str, event_id: str) -> None:
    """Log a download event (kept here so the media route is thinner)."""
    await db.download_events.insert_one({
        "id": event_id,
        "illustrationId": illustration_id,
        "bundleId": None,
        "downloadedAt": datetime.now(timezone.utc),
    })


async def increment_download_count(illustration_id: str) -> None:
    await db.illustrations.update_one(
        {"id": illustration_id},
        {"$inc": {"downloadCount": 1}},
    )


# --- Mutations ---------------------------------------------------------------

async def insert(illust_dict: dict) -> dict:
    """Insert a new illustration. Mongo adds ``_id``; we pop it."""
    await db.illustrations.insert_one(illust_dict)
    illust_dict.pop("_id", None)
    return illust_dict


async def update_fields(illustration_id: str, fields: dict) -> int:
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    result = await db.illustrations.update_one(
        {"id": illustration_id}, {"$set": fields}
    )
    return result.modified_count


async def update_theme_assignment(
    illustration_id: str, new_theme_id: Optional[str]
) -> int:
    result = await db.illustrations.update_one(
        {"id": illustration_id},
        {"$set": {
            "themeId": new_theme_id,
            "updatedAt": datetime.now(timezone.utc),
        }},
    )
    return result.modified_count


async def delete(illustration_id: str) -> int:
    result = await db.illustrations.delete_one({"id": illustration_id})
    return result.deleted_count


# --- Counts used by services -------------------------------------------------

async def count_all() -> int:
    return await db.illustrations.count_documents({})


async def count_free() -> int:
    return await db.illustrations.count_documents({"isFree": True})


async def count_by_theme(theme_id: str) -> int:
    return await db.illustrations.count_documents({"themeId": theme_id})
