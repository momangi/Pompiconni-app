"""Repository for the ``site_settings`` collection.

The site_settings collection contains a single document keyed by
``{"id": "global"}`` that holds cross-cutting toggles (show_reviews,
legal info, brand assets references, social links, etc.).

Only the SQL-like CRUD operations belong here. Side effects such as
GridFS uploads (brand logo, hero image) remain in ``server.py`` and
will be moved to a dedicated infrastructure module in a later phase.
"""
from datetime import datetime, timezone

from core.database import db


GLOBAL_FILTER = {"id": "global"}


async def find_global(projection: dict | None = None) -> dict | None:
    """Return the global settings document, or ``None`` if not present."""
    return await db.site_settings.find_one(GLOBAL_FILTER, projection)


async def update_global(fields: dict, *, touch_updated_at: bool = True) -> None:
    """Upsert the given fields onto the global settings document.

    Mirrors the legacy behaviour: when ``touch_updated_at`` is True (the
    default for admin edits) we stamp ``updatedAt`` with the current UTC
    time. The public site-settings GET and the social-links PUT do NOT
    set ``updatedAt`` in legacy code; pass ``touch_updated_at=False`` to
    preserve that semantics.
    """
    update_data = dict(fields)
    if touch_updated_at and "updatedAt" not in update_data:
        update_data["updatedAt"] = datetime.now(timezone.utc)
    await db.site_settings.update_one(
        GLOBAL_FILTER,
        {"$set": update_data},
        upsert=True,
    )
