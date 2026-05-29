"""Admin posters router (Fase 4C router split).

CRUD metadata + stats summary. The GridFS upload-image, upload-pdf,
image stream, download endpoints stay in ``server.py``.
"""
from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from core.database import gridfs_bucket
from models import PosterCreate, PosterUpdate
from services import poster_service


router = APIRouter()


@router.get("/posters")
async def admin_get_posters(email: str = Depends(verify_admin)):
    """Get all posters for admin panel"""
    return await poster_service.list_admin_posters()


@router.post("/posters")
async def admin_create_poster(poster: PosterCreate, email: str = Depends(verify_admin)):
    """Create a new poster"""
    return await poster_service.create_poster(poster)


@router.get("/posters/{poster_id}")
async def admin_get_poster(poster_id: str, email: str = Depends(verify_admin)):
    """Get a single poster for editing"""
    return await poster_service.get_admin_poster(poster_id)


@router.put("/posters/{poster_id}")
async def admin_update_poster(poster_id: str, poster: PosterUpdate, email: str = Depends(verify_admin)):
    """Update a poster"""
    return await poster_service.update_poster(poster_id, poster)


@router.put("/posters/{poster_id}/download-enabled")
async def toggle_poster_download(poster_id: str, email: str = Depends(verify_admin)):
    """Toggle the downloadEnabled status of a poster"""
    return await poster_service.toggle_download_enabled(poster_id)


@router.delete("/posters/{poster_id}")
async def admin_delete_poster(poster_id: str, email: str = Depends(verify_admin)):
    """Delete a poster and its files"""
    from bson import ObjectId

    poster = await poster_service.prepare_admin_delete(poster_id)

    # GridFS cleanup remains inline (heavy-media policy preserved).
    for file_id_key in ("imageFileId", "pdfFileId"):
        file_id = poster.get(file_id_key)
        if file_id:
            try:
                await gridfs_bucket.delete(ObjectId(file_id))
            except Exception:
                pass

    await poster_service.finalize_admin_delete(poster_id)
    return {"success": True}


@router.get("/posters/stats/summary")
async def admin_poster_stats(email: str = Depends(verify_admin)):
    """Get poster statistics"""
    return await poster_service.stats_summary()
