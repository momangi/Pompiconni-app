"""Repository for the ``book_scenes`` collection.

R1 fix (Fase 4B Batch 4, approved cleanup): reads use the ``EXCLUDE_ID``
projection. GridFS cleanup helpers keep a raw lookup so the route can
delete the colored/lineart image bytes before removing the doc.
"""
from datetime import datetime, timezone

from core.database import db
from models import MAX_SCENES_PER_BOOK

from .base import EXCLUDE_ID


# --- Reads (R1 fix: never expose _id) ---------------------------------------

async def list_by_book(book_id: str) -> list[dict]:
    """All scenes for a book, ordered by ``sceneNumber`` ascending."""
    return await db.book_scenes.find(
        {"bookId": book_id}, EXCLUDE_ID
    ).sort("sceneNumber", 1).to_list(MAX_SCENES_PER_BOOK)


async def list_raw_by_book(book_id: str) -> list[dict]:
    """Raw list (keeps GridFS file ids) used by delete cascades."""
    return await db.book_scenes.find({"bookId": book_id}).to_list(MAX_SCENES_PER_BOOK)


async def find_by_id(scene_id: str, book_id: str) -> dict | None:
    return await db.book_scenes.find_one(
        {"id": scene_id, "bookId": book_id}, EXCLUDE_ID
    )


async def find_raw(scene_id: str, book_id: str) -> dict | None:
    return await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})


async def find_by_scene_number(book_id: str, scene_number: int) -> dict | None:
    return await db.book_scenes.find_one(
        {"bookId": book_id, "sceneNumber": scene_number}
    )


async def count_by_book(book_id: str) -> int:
    return await db.book_scenes.count_documents({"bookId": book_id})


# --- Mutations --------------------------------------------------------------

async def insert(scene_dict: dict) -> dict:
    await db.book_scenes.insert_one(scene_dict)
    scene_dict.pop("_id", None)
    return scene_dict


async def update_fields(scene_id: str, fields: dict) -> int:
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    result = await db.book_scenes.update_one({"id": scene_id}, {"$set": fields})
    return result.modified_count


async def delete(scene_id: str) -> int:
    result = await db.book_scenes.delete_one({"id": scene_id})
    return result.deleted_count


async def delete_all_by_book(book_id: str) -> int:
    result = await db.book_scenes.delete_many({"bookId": book_id})
    return result.deleted_count
