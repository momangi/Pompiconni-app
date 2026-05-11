"""Business rules for bundles.

Holds:
  * decoration of bundle responses with ``backgroundImageUrl`` and
    ``pdfUrl`` (mirrors the legacy inline blocks in ``server.py``);
  * CRUD operations with 404 semantics preserved;
  * the legacy ``recalculate_bundle_counts`` helper that rebuilds the
    cached counters on 4 named bundles.

GridFS-heavy endpoints (upload-background, upload-pdf, download,
generated-pdf streaming) stay in ``server.py`` for this batch.
"""
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException

from core.database import db
from repositories import bundle_repo


# --- Decoration --------------------------------------------------------------

def _decorate(bundle: dict) -> dict:
    """Add ``backgroundImageUrl`` and ``pdfUrl`` in-place when present."""
    bid = bundle.get("id")
    if bundle.get("backgroundImageFileId"):
        bundle["backgroundImageUrl"] = f"/api/bundles/{bid}/background-image"
    if bundle.get("pdfFileId"):
        bundle["pdfUrl"] = f"/api/bundles/{bid}/download"
    return bundle


# --- Reads -------------------------------------------------------------------

async def list_public_bundles() -> list[dict]:
    bundles = await bundle_repo.list_active()
    for b in bundles:
        _decorate(b)
    return bundles


async def list_admin_bundles() -> list[dict]:
    bundles = await bundle_repo.list_all_sorted()
    for b in bundles:
        _decorate(b)
    return bundles


# --- Mutations ---------------------------------------------------------------

async def create_bundle(payload) -> dict:
    """Insert a new bundle from a Pydantic ``BundleCreate``."""
    bundle_dict = payload.dict()
    bundle_dict["id"] = str(uuid.uuid4())
    bundle_dict["illustrationCount"] = len(payload.illustrationIds)
    bundle_dict["pdfFileId"] = None
    bundle_dict["pdfUrl"] = None
    bundle_dict["backgroundImageFileId"] = None
    bundle_dict["backgroundImageUrl"] = None
    now = datetime.now(timezone.utc)
    bundle_dict["createdAt"] = now
    bundle_dict["updatedAt"] = now
    return await bundle_repo.insert(bundle_dict)


async def update_bundle(bundle_id: str, payload) -> dict:
    """Apply a partial update and return the decorated refreshed document."""
    if not await bundle_repo.exists(bundle_id):
        raise HTTPException(status_code=404, detail="Bundle non trovato")

    update_data: dict = {}
    for key, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            update_data[key] = value

    if "illustrationIds" in update_data:
        update_data["illustrationCount"] = len(update_data["illustrationIds"])

    await bundle_repo.update_fields(bundle_id, update_data)
    updated = await bundle_repo.find_by_id(bundle_id)
    return _decorate(updated) if updated else None


async def prepare_admin_delete(bundle_id: str) -> dict:
    """Return the raw bundle doc so the route can cleanup GridFS, or 404."""
    bundle = await bundle_repo.find_raw(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    return bundle


async def finalize_admin_delete(bundle_id: str) -> None:
    await bundle_repo.delete(bundle_id)


# --- Cross-domain helper used by illustrations service ----------------------

async def recalculate_named_bundle_counts() -> None:
    """Refresh the cached counters for the legacy named bundles.

    Mirrors verbatim the side effects of ``recalculate_bundle_counts`` in
    the legacy ``server.py``: the 4 hardcoded bundles ("Starter Pack
    Poppiconni", "Album Mestieri Completo", "Mega Pack Stagioni" and
    "Collezione Completa") are kept in sync with the illustrations
    collection. Logs to the standard logger on success/failure.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        total_count = await db.illustrations.count_documents({})
        free_count = await db.illustrations.count_documents({"isFree": True})
        mestieri_count = await db.illustrations.count_documents({"themeId": "mestieri"})
        stagioni_count = await db.illustrations.count_documents({"themeId": "stagioni"})

        starter_count = min(free_count, 10)
        await bundle_repo.update_by_name(
            "Starter Pack Poppiconni",
            {
                "illustrationCount": starter_count,
                "description": f"{starter_count} tavole gratuite per iniziare a colorare!",
            },
        )
        await bundle_repo.update_by_name(
            "Album Mestieri Completo",
            {
                "illustrationCount": mestieri_count,
                "description": f"Tutte le {mestieri_count} tavole dei mestieri in PDF",
            },
        )
        await bundle_repo.update_by_name(
            "Mega Pack Stagioni",
            {
                "illustrationCount": stagioni_count,
                "description": f"{stagioni_count} tavole per tutte le stagioni",
            },
        )
        await bundle_repo.update_by_name(
            "Collezione Completa",
            {
                "illustrationCount": total_count,
                "description": f"Tutti i {total_count} disegni + bonus esclusivi",
            },
        )
        logger.info(
            "Bundle counts updated: total=%s, free=%s, mestieri=%s, stagioni=%s",
            total_count, free_count, mestieri_count, stagioni_count,
        )
    except Exception as e:  # noqa: BLE001 - legacy swallows errors here
        logger.error(f"Error updating bundle counts: {e}")
