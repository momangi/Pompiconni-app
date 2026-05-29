"""Admin generation-styles media router (Fase 5/M3).

Style library (reference images for the Multi-AI pipeline): list, create,
delete, upload-reference image, and admin-only image stream. Logic
preserved verbatim from legacy ``server.py``.

All routes are scoped per-user via ``userId = <admin email>`` (the JWT
``sub``). The reference-image stream stays admin-only with
``cache_control="private, max-age=3600"`` to keep style libraries
isolated per administrator.
"""
from datetime import datetime, timezone
import io
import logging
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket
from image_pipeline import MAX_REFERENCE_IMAGES_PER_USER
from models import GenerationStyleCreate
from streaming import stream_gridfs_response


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/styles")
async def get_generation_styles(email: str = Depends(verify_admin)):
    """Get all generation styles for the current user"""
    styles = await db.generation_styles.find(
        {"userId": email},
        {"_id": 0}
    ).to_list(MAX_REFERENCE_IMAGES_PER_USER + 10)
    return {
        "styles": styles,
        "count": len(styles),
        "limit": MAX_REFERENCE_IMAGES_PER_USER
    }


@router.post("/styles")
async def create_generation_style(
    style: GenerationStyleCreate,
    email: str = Depends(verify_admin)
):
    """Create a new generation style (reference image library)"""
    # Check limit
    count = await db.generation_styles.count_documents({"userId": email})
    if count >= MAX_REFERENCE_IMAGES_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Limite raggiunto: massimo {MAX_REFERENCE_IMAGES_PER_USER} stili per utente"
        )

    style_dict = {
        "id": str(uuid.uuid4()),
        "userId": email,
        "styleName": style.styleName,
        "description": style.description,
        "isActive": style.isActive,
        "referenceImageFileId": None,
        "referenceImageUrl": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }

    await db.generation_styles.insert_one(style_dict)
    style_dict.pop('_id', None)

    return {"success": True, "style": style_dict}


@router.delete("/styles/{style_id}")
async def delete_generation_style(style_id: str, email: str = Depends(verify_admin)):
    """Delete a generation style and its reference image"""
    from bson import ObjectId

    style = await db.generation_styles.find_one({"id": style_id, "userId": email})
    if not style:
        raise HTTPException(status_code=404, detail="Stile non trovato")

    # Delete reference image from GridFS if exists
    if style.get('referenceImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(style['referenceImageFileId']))
        except Exception:
            pass

    await db.generation_styles.delete_one({"id": style_id})
    return {"success": True}


@router.post("/styles/{style_id}/upload-reference")
async def upload_style_reference(
    style_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload reference image for a generation style"""
    from bson import ObjectId

    style = await db.generation_styles.find_one({"id": style_id, "userId": email})
    if not style:
        raise HTTPException(status_code=404, detail="Stile non trovato")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        filename = f"style_reference_{style_id}{ext}"

        # Delete old reference if exists
        if style.get('referenceImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(style['referenceImageFileId']))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "style_id": style_id,
                "type": "style_reference",
                "content_type": content_type,
                "uploaded_by": email
            }
        )

        await db.generation_styles.update_one(
            {"id": style_id},
            {
                "$set": {
                    "referenceImageFileId": str(file_id),
                    "referenceImageUrl": f"/api/admin/styles/{style_id}/reference-image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        return {
            "success": True,
            "imageUrl": f"/api/admin/styles/{style_id}/reference-image"
        }
    except Exception as e:
        logger.error(f"Error uploading style reference: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")


@router.get("/styles/{style_id}/reference-image")
async def get_style_reference_image(style_id: str, request: Request, email: str = Depends(verify_admin)):
    """Serve reference image for a style (true streaming + ETag).

    Admin-only stream with private cache; ownership enforced via
    ``userId = email`` filter.
    """
    style = await db.generation_styles.find_one({"id": style_id, "userId": email})
    if not style or not style.get('referenceImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine di riferimento non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=style['referenceImageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="private, max-age=3600",
        not_found_detail="Immagine di riferimento non trovata",
    )
