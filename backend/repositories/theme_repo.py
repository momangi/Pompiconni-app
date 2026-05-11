"""Repository for the ``themes`` collection.

Only CRUD against ``db.themes`` (and the read of ``db.illustrations`` for
the delete-safety check) lives here. The GridFS-backed background image
upload/serve endpoints stay in ``server.py`` for this batch (out of 4B
Batch 1 scope: ``GridFS/PDF/downloads/character_images``).
"""
from datetime import datetime, timezone

from core.database import db

from .base import EXCLUDE_ID


PAGE_LIMIT = 100


async def list_all() -> list[dict]:
    """Return every theme without the BSON ``_id``."""
    return await db.themes.find({}, EXCLUDE_ID).to_list(PAGE_LIMIT)


async def find_by_id(theme_id: str) -> dict | None:
    """Return a single theme without the BSON ``_id``."""
    return await db.themes.find_one({"id": theme_id}, EXCLUDE_ID)


async def exists(theme_id: str) -> bool:
    """Return True if a theme with the given id exists."""
    return await db.themes.find_one({"id": theme_id}) is not None


async def insert(theme_dict: dict) -> dict:
    """Insert a theme. Mongo mutates the dict; the returned doc has its
    BSON ``_id`` popped so it can be sent over the wire untouched.
    """
    await db.themes.insert_one(theme_dict)
    theme_dict.pop("_id", None)
    return theme_dict


async def update(theme_id: str, fields: dict) -> dict | None:
    """Apply a partial update and return the refreshed document.

    Returns ``None`` if no document matches the id (caller decides 404).
    """
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    await db.themes.update_one({"id": theme_id}, {"$set": fields})
    return await db.themes.find_one({"id": theme_id}, EXCLUDE_ID)


async def delete(theme_id: str) -> int:
    """Delete a theme by id, return the deleted count."""
    result = await db.themes.delete_one({"id": theme_id})
    return result.deleted_count


async def count_illustrations(theme_id: str) -> int:
    """Number of illustrations referencing this theme."""
    return await db.illustrations.count_documents({"themeId": theme_id})


async def unassign_illustrations(theme_id: str) -> int:
    """Unassign all illustrations from a theme (force-delete support).

    Returns the modified count.
    """
    result = await db.illustrations.update_many(
        {"themeId": theme_id},
        {"$set": {"themeId": None, "updatedAt": datetime.now(timezone.utc)}},
    )
    return result.modified_count


async def recalc_illustration_count(theme_id: str) -> None:
    """Recompute and persist the illustration counter for one theme."""
    if not theme_id:
        return
    count = await db.illustrations.count_documents({"themeId": theme_id})
    await db.themes.update_one(
        {"id": theme_id},
        {"$set": {"illustrationCount": count}},
    )
