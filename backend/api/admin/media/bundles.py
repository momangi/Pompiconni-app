"""Admin bundles media router (Fase 5/M1).

GridFS upload for bundle background image (with variant fire-and-forget)
and manual PDF upload. Logic preserved verbatim from legacy server.py.
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


_IMAGE_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _fire_variants(file_id) -> None:
    """Schedule responsive-variant generation. Best-effort; never raises."""
    import asyncio

    try:
        asyncio.create_task(ensure_variants(db, gridfs_bucket, file_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not schedule variants for {file_id}: {e}")


@router.post("/bundles/{bundle_id}/upload-background")
async def upload_bundle_background(
    bundle_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin),
):
    """Upload background image for a bundle."""
    from bson import ObjectId

    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")

    ext = Path(file.filename).suffix.lower()
    if ext not in _IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")
    content_type = _IMAGE_CONTENT_TYPES[ext]

    try:
        content = await file.read()
        filename = f"bundle_bg_{bundle_id}{ext}"

        if bundle.get("backgroundImageFileId"):
            try:
                await gridfs_bucket.delete(ObjectId(bundle["backgroundImageFileId"]))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "bundle_id": bundle_id,
                "type": "bundle_background",
                "content_type": content_type,
            },
        )

        await db.bundles.update_one(
            {"id": bundle_id},
            {"$set": {
                "backgroundImageFileId": str(file_id),
                "backgroundImageUrl": f"/api/bundles/{bundle_id}/background-image",
                "updatedAt": datetime.now(timezone.utc),
            }},
        )

        _fire_variants(file_id)

        return {
            "success": True,
            "backgroundImageUrl": f"/api/bundles/{bundle_id}/background-image",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading bundle background: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")


@router.post("/bundles/{bundle_id}/upload-pdf")
async def upload_bundle_pdf(
    bundle_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin),
):
    """Upload PDF for a bundle."""
    from bson import ObjectId

    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")

    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Solo file PDF permessi")

    try:
        content = await file.read()
        filename = f"bundle_{bundle_id}.pdf"

        if bundle.get("pdfFileId"):
            try:
                await gridfs_bucket.delete(ObjectId(bundle["pdfFileId"]))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "bundle_id": bundle_id,
                "type": "bundle_pdf",
                "content_type": "application/pdf",
            },
        )

        await db.bundles.update_one(
            {"id": bundle_id},
            {"$set": {
                "pdfFileId": str(file_id),
                "pdfUrl": f"/api/bundles/{bundle_id}/download",
                "updatedAt": datetime.now(timezone.utc),
            }},
        )

        return {"success": True, "pdfUrl": f"/api/bundles/{bundle_id}/download"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading bundle PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")
