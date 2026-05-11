"""Repository for the ``bundles`` collection.

Pure data access. GridFS uploads (background image, manual PDF) keep
their implementation in ``server.py`` for this batch — the repository
only exposes file IDs so the route can perform the side-effects
(delete-on-bundle-delete, generated-pdf cache invalidation).
"""
from datetime import datetime, timezone

from core.database import db

from .base import EXCLUDE_ID


PAGE_LIMIT = 100


# --- Public lookups -----------------------------------------------------------

async def list_active() -> list[dict]:
    """Active bundles for the public site, sorted by ``sortOrder`` asc."""
    return await db.bundles.find(
        {"isActive": True}, EXCLUDE_ID
    ).sort("sortOrder", 1).to_list(PAGE_LIMIT)


# --- Admin lookups ------------------------------------------------------------

async def list_all_sorted() -> list[dict]:
    """All bundles for admin (any status), sorted by ``sortOrder`` asc."""
    return await db.bundles.find({}, EXCLUDE_ID).sort("sortOrder", 1).to_list(PAGE_LIMIT)


async def find_by_id(bundle_id: str) -> dict | None:
    return await db.bundles.find_one({"id": bundle_id}, EXCLUDE_ID)


async def find_raw(bundle_id: str) -> dict | None:
    """Lookup that keeps the BSON ``_id`` and FileIDs for GridFS cleanup."""
    return await db.bundles.find_one({"id": bundle_id})


async def exists(bundle_id: str) -> bool:
    return await db.bundles.find_one({"id": bundle_id}) is not None


# --- Mutations ----------------------------------------------------------------

async def insert(bundle_dict: dict) -> dict:
    """Insert a new bundle. Mutates the dict (Mongo adds ``_id``); we pop it."""
    await db.bundles.insert_one(bundle_dict)
    bundle_dict.pop("_id", None)
    return bundle_dict


async def update_fields(bundle_id: str, fields: dict) -> int:
    """Apply a partial update. Returns modified_count."""
    fields = dict(fields)
    fields.setdefault("updatedAt", datetime.now(timezone.utc))
    result = await db.bundles.update_one({"id": bundle_id}, {"$set": fields})
    return result.modified_count


async def update_by_name(bundle_name: str, fields: dict) -> int:
    """Legacy helper: update a bundle by its ``name`` (used by recalc)."""
    result = await db.bundles.update_one({"name": bundle_name}, {"$set": fields})
    return result.modified_count


async def delete(bundle_id: str) -> int:
    """Delete the bundle document. Returns deleted_count."""
    result = await db.bundles.delete_one({"id": bundle_id})
    return result.deleted_count
