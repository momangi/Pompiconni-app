"""Admin posters media router (Fase 5/M2).

Preview image upload (with variant fire-and-forget) and print-ready PDF
upload. Logic preserved verbatim from legacy ``server.py``.
"""
from datetime import datetime, timezone
import io
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket
from media_pipeline import ensure_variants


logger = logging.getLogger(__name__)

router = APIRouter()


def _fire_variants(file_id) -> None:
    """Fire-and-forget variant generation. Safe to call after any image upload."""
    import asyncio

    try:
        asyncio.create_task(ensure_variants(db, gridfs_bucket, file_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not schedule variants for {file_id}: {e}")


@router.post("/posters/{poster_id}/upload-image")
async def admin_upload_poster_image(
    poster_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload preview image for a poster"""
    from bson import ObjectId

    poster = await db.posters.find_one({"id": poster_id})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        filename = f"poster_{poster_id}{ext}"

        # Delete old image if exists
        if poster.get('imageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(poster['imageFileId']))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "poster_id": poster_id,
                "type": "poster_image",
                "content_type": content_type
            }
        )

        await db.posters.update_one(
            {"id": poster_id},
            {
                "$set": {
                    "imageFileId": str(file_id),
                    "imageUrl": f"/api/posters/{poster_id}/image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        _fire_variants(file_id)

        return {
            "success": True,
            "imageUrl": f"/api/posters/{poster_id}/image"
        }
    except Exception as e:
        logger.error(f"Error uploading poster image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")


@router.post("/posters/{poster_id}/upload-pdf")
async def admin_upload_poster_pdf(
    poster_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload print-ready PDF for a poster"""
    from bson import ObjectId

    poster = await db.posters.find_one({"id": poster_id})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")

    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Solo file PDF permessi")

    try:
        content = await file.read()
        filename = f"poster_{poster_id}.pdf"

        # Delete old PDF if exists
        if poster.get('pdfFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(poster['pdfFileId']))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "poster_id": poster_id,
                "type": "poster_pdf",
                "content_type": "application/pdf"
            }
        )

        await db.posters.update_one(
            {"id": poster_id},
            {
                "$set": {
                    "pdfFileId": str(file_id),
                    "pdfUrl": f"/api/posters/{poster_id}/download",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        return {
            "success": True,
            "pdfUrl": f"/api/posters/{poster_id}/download"
        }
    except Exception as e:
        logger.error(f"Error uploading poster PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")
