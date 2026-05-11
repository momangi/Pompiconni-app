"""Repository for the ``game_level_backgrounds`` collection.

Same separation as posters and games: GridFS upload/serve flows stay in
``server.py``; this module owns only the document queries.
"""
from datetime import datetime, timezone

from core.database import db

from .base import EXCLUDE_ID


PAGE_LIMIT = 50
DEFAULT_GAME_SLUG = "bolle-magiche"


async def list_for_game(game_slug: str = DEFAULT_GAME_SLUG) -> list[dict]:
    """Backgrounds for a given game, sorted by level range start."""
    return await db.game_level_backgrounds.find(
        {"gameSlug": game_slug}, EXCLUDE_ID
    ).sort("levelRangeStart", 1).to_list(PAGE_LIMIT)


async def find_by_id(bg_id: str) -> dict | None:
    """Lookup by id, without ``_id``."""
    return await db.game_level_backgrounds.find_one({"id": bg_id}, EXCLUDE_ID)


async def find_raw_by_id(bg_id: str) -> dict | None:
    """Lookup that retains the BSON ``_id`` and GridFS FileID for cleanup."""
    return await db.game_level_backgrounds.find_one({"id": bg_id})


async def find_overlapping(
    level_range_start: int,
    level_range_end: int,
    game_slug: str = DEFAULT_GAME_SLUG,
) -> dict | None:
    """Return any existing background whose range overlaps the given one."""
    return await db.game_level_backgrounds.find_one({
        "gameSlug": game_slug,
        "$or": [
            {"levelRangeStart": {"$lte": level_range_end, "$gte": level_range_start}},
            {"levelRangeEnd": {"$lte": level_range_end, "$gte": level_range_start}},
        ],
    })


async def insert(bg_dict: dict) -> dict:
    """Insert a new background and pop the BSON ``_id`` from the returned dict."""
    await db.game_level_backgrounds.insert_one(bg_dict)
    bg_dict.pop("_id", None)
    return bg_dict


async def update_fields(bg_id: str, fields: dict) -> dict | None:
    """Apply a partial update and return the refreshed doc (no ``_id``)."""
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    await db.game_level_backgrounds.update_one({"id": bg_id}, {"$set": fields})
    return await db.game_level_backgrounds.find_one({"id": bg_id}, EXCLUDE_ID)


async def set_image_file_id(bg_id: str, file_id_str: str) -> None:
    """Persist the GridFS FileID after the route uploaded the image."""
    await db.game_level_backgrounds.update_one(
        {"id": bg_id},
        {"$set": {
            "backgroundImageFileId": file_id_str,
            "updatedAt": datetime.now(timezone.utc),
        }},
    )


async def delete(bg_id: str) -> int:
    """Delete the document. Returns deleted_count."""
    result = await db.game_level_backgrounds.delete_one({"id": bg_id})
    return result.deleted_count
