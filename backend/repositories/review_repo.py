"""Repository for the ``reviews`` collection.

Pure data access. All Mongo queries that touch ``db.reviews`` should live
here. Business decisions (e.g. should the public list be empty when
``show_reviews`` is disabled?) belong to ``services/review_service.py``.

Legacy behaviour preserved verbatim:
    * Public list and admin list both *expose* the stringified ``_id``
      field. This pre-dates the refactor and is part of the documented
      response shape (see baseline §6 / R1). Fixing it requires a
      separate phase explicitly approved by the user.
"""
from core.database import db

from .base import stringify_ids


PAGE_LIMIT = 100  # Identical to the limit used in the legacy server.py.


async def list_approved(limit: int = PAGE_LIMIT) -> list[dict]:
    """Return approved reviews ready for public display."""
    docs = await db.reviews.find({"is_approved": True}).to_list(limit)
    return stringify_ids(docs)


async def list_all(limit: int = PAGE_LIMIT) -> list[dict]:
    """Return every review (admin view)."""
    docs = await db.reviews.find().to_list(limit)
    return stringify_ids(docs)


async def set_approved(review_id: str, is_approved: bool) -> int:
    """Toggle the ``is_approved`` flag and return the modified count."""
    result = await db.reviews.update_one(
        {"id": review_id},
        {"$set": {"is_approved": is_approved}},
    )
    return result.modified_count


async def delete(review_id: str) -> int:
    """Delete a review by domain id, return the deleted count."""
    result = await db.reviews.delete_one({"id": review_id})
    return result.deleted_count
