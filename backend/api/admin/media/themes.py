"""Admin themes media router (Fase 5/M1).

Theme background image upload (GridFS). Logic preserved verbatim.
"""
from datetime import datetime, timezone
import io
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket


logger = logging.getLogger(__name__)

router = APIRouter()


_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.post("/themes/{theme_id}/upload-background")
async def upload_theme_background(
    theme_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin),
):
    """Upload background image for a theme."""
    from bson import ObjectId

    theme = await db.themes.find_one({"id": theme_id})
    if not theme:
        raise HTTPException(status_code=404, detail="Tema non trovato")

    ext = Path(file.filename).suffix.lower()
    if ext not in _CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")
    content_type = _CONTENT_TYPES[ext]

    try:
        content = await file.read()
        filename = f"theme_bg_{theme_id}{ext}"

        if theme.get("backgroundImageFileId"):
            try:
                await gridfs_bucket.delete(ObjectId(theme["backgroundImageFileId"]))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "theme_id": theme_id,
                "type": "theme_background",
                "content_type": content_type,
            },
        )

        await db.themes.update_one(
            {"id": theme_id},
            {"$set": {
                "backgroundImageFileId": str(file_id),
                "backgroundImageUrl": f"/api/themes/{theme_id}/background-image",
                "updatedAt": datetime.now(timezone.utc),
            }},
        )

        return {
            "success": True,
            "backgroundImageUrl": (
                f"/api/themes/{theme_id}/background-image"
                f"?v={datetime.now(timezone.utc).timestamp()}"
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading theme background: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")
