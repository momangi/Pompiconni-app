"""Repository for the ``reading_progress`` collection.

Per-visitor progress through a book's scenes. R1 is implicit here since
the legacy route never returned the raw document (only the
``currentScene`` integer).
"""
from datetime import datetime, timezone
import uuid

from core.database import db


async def get_for_visitor(book_id: str, visitor_id: str) -> dict | None:
    return await db.reading_progress.find_one(
        {"bookId": book_id, "visitorId": visitor_id}
    )


async def upsert_progress(book_id: str, visitor_id: str, scene: int) -> None:
    await db.reading_progress.update_one(
        {"bookId": book_id, "visitorId": visitor_id},
        {
            "$set": {
                "currentScene": scene,
                "updatedAt": datetime.now(timezone.utc),
            },
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "bookId": book_id,
                "visitorId": visitor_id,
            },
        },
        upsert=True,
    )


async def delete_all_by_book(book_id: str) -> int:
    result = await db.reading_progress.delete_many({"bookId": book_id})
    return result.deleted_count
