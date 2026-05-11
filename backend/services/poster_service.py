"""Business rules for posters.

GridFS-heavy paths (image serving, PDF download, image/PDF uploads,
delete-with-cleanup) keep some logic in ``server.py`` because they
combine streaming and storage side effects with DB CRUD. This service
exposes:
    * pure read/list/CRUD operations consumed by the JSON endpoints;
    * a helper used by the public PDF download route to bump the counter;
    * the stats summary used by the admin dashboard;
    * a "prepare delete" helper that fetches the raw doc and returns it
      to the route, so the route can clean up GridFS files before the
      service finalises the document delete.

Signature decisions match the legacy ``server.py`` responses verbatim.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import HTTPException

from repositories import poster_repo


# --- Public -------------------------------------------------------------------

async def list_public_posters() -> list[dict]:
    return await poster_repo.list_published()


async def get_public_poster(poster_id: str) -> dict:
    poster = await poster_repo.find_published_by_id(poster_id)
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    return poster


# --- Admin reads --------------------------------------------------------------

async def list_admin_posters() -> list[dict]:
    return await poster_repo.list_all()


async def get_admin_poster(poster_id: str) -> dict:
    poster = await poster_repo.find_by_id(poster_id)
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    return poster


# --- Admin mutations ----------------------------------------------------------

async def create_poster(payload) -> dict:
    """Insert a poster from a Pydantic ``PosterCreate`` and return it."""
    now = datetime.now(timezone.utc)
    poster_dict = {
        "id": str(uuid.uuid4()),
        "title": payload.title,
        "description": payload.description,
        "price": payload.price,
        "status": payload.status,
        "imageFileId": None,
        "imageUrl": None,
        "pdfFileId": None,
        "pdfUrl": None,
        "downloadCount": 0,
        "createdAt": now,
        "updatedAt": now,
    }
    return await poster_repo.insert(poster_dict)


async def update_poster(poster_id: str, payload) -> dict:
    """Apply a ``PosterUpdate`` partial. Returns ``{"success": True}`` or 404.

    Legacy quirk: the original handler returns 404 when ``modified_count`` is
    zero — meaning even an unchanged value on an existing doc would yield
    404. We preserve that behaviour byte-for-byte.
    """
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.now(timezone.utc)
    modified = await poster_repo.update_fields(poster_id, update_data)
    if modified == 0:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    return {"success": True}


async def toggle_download_enabled(poster_id: str) -> dict:
    """Flip the ``downloadEnabled`` flag and return the new value."""
    poster = await poster_repo.find_by_id(poster_id)
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    new_status = not poster.get("downloadEnabled", True)
    await poster_repo.set_download_enabled(poster_id, new_status)
    return {"success": True, "downloadEnabled": new_status}


async def prepare_admin_delete(poster_id: str) -> dict:
    """Return the raw poster doc so the route can cleanup GridFS, or 404."""
    poster = await poster_repo.find_raw(poster_id)
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    return poster


async def finalize_admin_delete(poster_id: str) -> None:
    """Delete the document after the route has cleaned up GridFS files."""
    await poster_repo.delete(poster_id)


# --- Stats --------------------------------------------------------------------

async def stats_summary() -> dict:
    return await poster_repo.stats_summary()


# --- Helpers used by media routes still in server.py -------------------------

async def increment_download_count(poster_id: str) -> None:
    """Bump the ``downloadCount`` counter (called by the PDF download route)."""
    await poster_repo.increment_download_count(poster_id)


def public_poster_pdf_filename(poster_doc: dict) -> str:
    """Build the safe ``Poppiconni_Poster_<title>.pdf`` filename.

    Kept here so server.py does not need to know the sanitisation rules.
    The route currently inlines the regex; we expose the helper for future
    consolidation. Not used in this batch (route untouched).
    """
    import re
    safe_title = (
        re.sub(r"[^\w\s-]", "", poster_doc.get("title", "poster"))
        .strip()
        .replace(" ", "_")
    )
    return f"Poppiconni_Poster_{safe_title}.pdf"
