"""Repository for the ``books`` collection.

R1 fix (Fase 4B Batch 4, approved cleanup): every public/admin read uses
``EXCLUDE_ID`` projection so the BSON ``_id`` never leaves the data
access layer. GridFS-backed routes (cover, PDF stream) keep their
``find_raw`` lookup since they need access to ``coverImageFileId`` etc.
"""
from datetime import datetime, timezone

from core.database import db

from .base import EXCLUDE_ID


PAGE_LIMIT = 100


# --- Reads (R1 fix: never expose _id) ---------------------------------------

async def list_visible() -> list[dict]:
    """Public list: visible books only, default insertion order."""
    return await db.books.find({"isVisible": True}, EXCLUDE_ID).to_list(PAGE_LIMIT)


async def list_all_sorted() -> list[dict]:
    """Admin list: all books, newest first."""
    return await db.books.find({}, EXCLUDE_ID).sort("createdAt", -1).to_list(PAGE_LIMIT)


async def find_by_id(book_id: str) -> dict | None:
    return await db.books.find_one({"id": book_id}, EXCLUDE_ID)


async def find_raw(book_id: str) -> dict | None:
    """Lookup that keeps GridFS ids (cover, pdf flags). Used by media routes."""
    return await db.books.find_one({"id": book_id})


async def exists(book_id: str) -> bool:
    return await db.books.find_one({"id": book_id}) is not None


# --- Mutations --------------------------------------------------------------

async def insert(book_dict: dict) -> dict:
    """Insert a new book. Mongo adds ``_id``; we pop it for the response."""
    await db.books.insert_one(book_dict)
    book_dict.pop("_id", None)
    return book_dict


async def update_fields(book_id: str, fields: dict) -> int:
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    result = await db.books.update_one({"id": book_id}, {"$set": fields})
    return result.modified_count


async def delete(book_id: str) -> int:
    result = await db.books.delete_one({"id": book_id})
    return result.deleted_count


# --- Counter increments -----------------------------------------------------

async def inc_view_count(book_id: str) -> None:
    await db.books.update_one({"id": book_id}, {"$inc": {"viewCount": 1}})


async def inc_download_count(book_id: str) -> None:
    await db.books.update_one({"id": book_id}, {"$inc": {"downloadCount": 1}})


async def inc_scene_count(book_id: str, delta: int) -> None:
    await db.books.update_one({"id": book_id}, {"$inc": {"sceneCount": delta}})
