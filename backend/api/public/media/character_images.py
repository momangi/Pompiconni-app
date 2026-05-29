"""Public character-images media router (Fase 5/M3).

Public list (dict-by-trait) and per-trait GridFS image stream. Logic
preserved verbatim from legacy ``server.py``.
"""
from fastapi import APIRouter, HTTPException, Request

from constants.character_traits import CHARACTER_TRAITS
from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response


router = APIRouter()


@router.get("/character-images")
async def get_character_images():
    """Get all character trait images for public display"""
    images = await db.character_images.find({}, {"_id": 0}).to_list(10)
    # Return as dict for easy access
    result = {}
    for img in images:
        result[img['trait']] = img
    return result


@router.get("/character-images/{trait}/image")
async def get_character_image(trait: str, request: Request):
    """Serve character trait image (true streaming + ETag)."""
    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail="Invalid trait")
    record = await db.character_images.find_one({"trait": trait})
    if not record or not record.get('imageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=record['imageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )
