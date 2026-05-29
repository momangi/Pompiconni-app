"""Public level-backgrounds media router (Fase 5/M2).

GridFS image stream for "Bolle Magiche" level background images. Logic
preserved verbatim from legacy ``server.py``.
"""
from fastapi import APIRouter, HTTPException, Request

from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response


router = APIRouter()


@router.get("/games/bolle-magiche/level-backgrounds/{bg_id}/image")
async def get_level_background_image(bg_id: str, request: Request):
    """Serve level background image from GridFS (true streaming + ETag)."""
    bg = await db.game_level_backgrounds.find_one({"id": bg_id})
    if not bg or not bg.get('backgroundImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=bg['backgroundImageFileId'],
        request=request,
        fallback_content_type="image/jpeg",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )
