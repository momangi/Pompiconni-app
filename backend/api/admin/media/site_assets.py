"""Admin site-assets media router (Fase 5/M3).

Hero image + brand logo: upload, delete, and brand-logo status. Logic
preserved verbatim from legacy ``server.py`` — including pre-existing
inconsistencies between hero and brand-logo handling (see TD notes).

Tech debt notes (preserved verbatim, intentionally not refactored in M3):
- Brand-logo DELETE uses ``$set`` to empty strings instead of ``$unset``
  used by hero DELETE.
- ``upload-brand-logo`` returns the URL with a ``?v=<timestamp>``
  cachebust query, hero does not.
- Path ``/api/admin/upload-brand-logo`` is flat (no ``/site/`` prefix
  like hero).
- Path ``/api/admin/brand-logo-status`` is flat (no ``/site/`` prefix
  like ``/api/site/hero-status``).
"""
from datetime import datetime, timezone
import io
import logging
from pathlib import Path
import uuid

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


# ============== HERO IMAGE ==============

@router.post("/site/hero-image")
async def upload_hero_image(
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload or replace hero image"""
    from bson import ObjectId

    # Validate file type
    ext = Path(file.filename).suffix.lower()
    allowed_extensions = [".jpg", ".jpeg", ".png"]
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Solo file immagine sono permessi: {', '.join(allowed_extensions)}")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        unique_filename = f"hero_pompiconni_{uuid.uuid4()}{ext}"

        # Delete old hero image if exists
        settings = await db.site_settings.find_one({"id": "global"})
        if settings and settings.get('heroImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(settings['heroImageFileId']))
            except Exception:
                pass

        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(content),
            metadata={
                "type": "hero_image",
                "original_filename": file.filename,
                "content_type": content_type,
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )

        # Update site settings
        await db.site_settings.update_one(
            {"id": "global"},
            {
                "$set": {
                    "heroImageFileId": str(file_id),
                    "heroImageContentType": content_type,
                    "heroImageFileName": file.filename,
                    "heroImageUpdatedAt": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )

        # Fire-and-forget: generate responsive variants for hero
        _fire_variants(file_id)

        return {
            "success": True,
            "heroImageUrl": "/api/site/hero-image",
            "message": "Hero image aggiornata con successo"
        }

    except Exception as e:
        logger.error(f"Error uploading hero image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento dell'immagine")


@router.delete("/site/hero-image")
async def delete_hero_image(email: str = Depends(verify_admin)):
    """Delete hero image (restore to default)"""
    from bson import ObjectId

    settings = await db.site_settings.find_one({"id": "global"})
    if settings and settings.get('heroImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(settings['heroImageFileId']))
        except Exception:
            pass

        await db.site_settings.update_one(
            {"id": "global"},
            {
                "$unset": {
                    "heroImageFileId": "",
                    "heroImageContentType": "",
                    "heroImageFileName": "",
                    "heroImageUpdatedAt": ""
                }
            }
        )

    return {"success": True, "message": "Hero image rimossa, ripristinato default"}


# ============== BRAND LOGO ==============

@router.get("/brand-logo-status")
async def get_brand_logo_status(email: str = Depends(verify_admin)):
    """Get brand logo status"""
    settings = await db.site_settings.find_one({"id": "global"})
    has_logo = bool(settings and settings.get('brandLogoFileId'))
    return {
        "hasBrandLogo": has_logo,
        "brandLogoUrl": "/api/site/brand-logo" if has_logo else None
    }


@router.post("/upload-brand-logo")
async def upload_brand_logo(
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload brand logo image"""
    from bson import ObjectId

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        filename = f"brand_logo{ext}"

        settings = await db.site_settings.find_one({"id": "global"})

        # Delete old logo if exists
        if settings and settings.get('brandLogoFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(settings['brandLogoFileId']))
            except Exception:
                pass

        # Upload new logo
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"type": "brand_logo", "content_type": content_type}
        )

        await db.site_settings.update_one(
            {"id": "global"},
            {
                "$set": {
                    "brandLogoFileId": str(file_id),
                    "brandLogoContentType": content_type,
                    "brandLogoUpdatedAt": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )

        # Fire-and-forget: generate responsive variants for the brand logo
        _fire_variants(file_id)

        return {"success": True, "brandLogoUrl": f"/api/site/brand-logo?v={datetime.now(timezone.utc).timestamp()}"}
    except Exception as e:
        logger.error(f"Error uploading brand logo: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")


@router.delete("/brand-logo")
async def delete_brand_logo(email: str = Depends(verify_admin)):
    """Delete brand logo.

    NOTE: uses ``$set`` to empty strings instead of ``$unset`` (TD,
    preserved verbatim — see module docstring).
    """
    from bson import ObjectId

    settings = await db.site_settings.find_one({"id": "global"})

    if settings and settings.get('brandLogoFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(settings['brandLogoFileId']))
        except Exception:
            pass

        await db.site_settings.update_one(
            {"id": "global"},
            {"$set": {"brandLogoFileId": "", "brandLogoContentType": "", "brandLogoUpdatedAt": ""}}
        )

    return {"success": True}
