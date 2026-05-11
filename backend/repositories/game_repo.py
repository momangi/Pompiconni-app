"""Repository for the ``games`` collection.

Holds only the DB queries. The GridFS image upload/delete and image
streaming endpoints stay in ``server.py`` and reach into the repository
through :func:`find_raw_by_id` when they need the BSON ``_id`` or the
GridFS FileIDs of attached images.
"""
from datetime import datetime, timezone

from core.database import db

from .base import EXCLUDE_ID


PAGE_LIMIT = 100


async def list_all_sorted() -> list[dict]:
    """All games sorted by ``sortOrder`` ascending, without ``_id``."""
    return await db.games.find({}, EXCLUDE_ID).sort("sortOrder", 1).to_list(PAGE_LIMIT)


async def find_by_slug(slug: str) -> dict | None:
    """Public lookup by slug, without ``_id``."""
    return await db.games.find_one({"slug": slug}, EXCLUDE_ID)


async def find_by_id(game_id: str) -> dict | None:
    """Admin lookup by id, without ``_id``."""
    return await db.games.find_one({"id": game_id}, EXCLUDE_ID)


async def find_raw_by_id(game_id: str) -> dict | None:
    """Admin lookup that retains ``_id`` and FileIDs for GridFS cleanup."""
    return await db.games.find_one({"id": game_id})


async def find_raw_by_slug(slug: str) -> dict | None:
    """Lookup by slug that keeps the BSON ``_id`` (used by media routes)."""
    return await db.games.find_one({"slug": slug})


async def exists_by_slug(slug: str) -> bool:
    return await db.games.find_one({"slug": slug}) is not None


async def insert(game_dict: dict) -> dict:
    """Insert a new game and pop the BSON ``_id`` from the returned dict."""
    await db.games.insert_one(game_dict)
    if "_id" in game_dict:
        del game_dict["_id"]
    return game_dict


async def update_fields(game_id: str, fields: dict) -> dict | None:
    """Apply a partial update and return the refreshed game (no ``_id``)."""
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    await db.games.update_one({"id": game_id}, {"$set": fields})
    return await db.games.find_one({"id": game_id}, EXCLUDE_ID)


async def delete(game_id: str) -> int:
    """Delete the game document. Returns deleted_count."""
    result = await db.games.delete_one({"id": game_id})
    return result.deleted_count
