"""Admin character-images media router (Fase 5/M3).

Admin list (with placeholder fallback for missing traits), image upload,
delete, and text update. Logic preserved verbatim from legacy
``server.py``. The text-update route is co-located here for domain
cohesion even though it does not touch GridFS.
"""
from datetime import datetime, timezone
import io
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import verify_admin
from constants.character_traits import CHARACTER_TRAITS
from core.database import db, gridfs_bucket
from media_pipeline import ensure_variants
from models import CharacterTextUpdate


logger = logging.getLogger(__name__)

router = APIRouter()


def _fire_variants(file_id) -> None:
    """Fire-and-forget variant generation. Safe to call after any image upload."""
    import asyncio

    try:
        asyncio.create_task(ensure_variants(db, gridfs_bucket, file_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not schedule variants for {file_id}: {e}")


@router.get("/character-images")
async def admin_get_character_images(email: str = Depends(verify_admin)):
    """Get all character trait images for admin"""
    images = await db.character_images.find({}, {"_id": 0}).to_list(10)
    # Ensure all traits exist
    existing_traits = {img['trait'] for img in images}
    for trait in CHARACTER_TRAITS:
        if trait not in existing_traits:
            images.append({
                "trait": trait,
                "imageFileId": None,
                "imageUrl": None
            })
    return images


@router.post("/character-images/{trait}/upload")
async def admin_upload_character_image(
    trait: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload image for a character trait (dolce, simpatico, impacciato)"""
    from bson import ObjectId

    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail=f"Trait must be one of: {CHARACTER_TRAITS}")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        filename = f"character_{trait}{ext}"

        # Check if image already exists for this trait
        existing = await db.character_images.find_one({"trait": trait})
        if existing and existing.get('imageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(existing['imageFileId']))
            except Exception:
                pass

        # Upload new image
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "trait": trait,
                "type": "character_image",
                "content_type": content_type
            }
        )

        # Upsert character image record
        await db.character_images.update_one(
            {"trait": trait},
            {
                "$set": {
                    "trait": trait,
                    "imageFileId": str(file_id),
                    "imageUrl": f"/api/character-images/{trait}/image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

        _fire_variants(file_id)

        return {
            "success": True,
            "trait": trait,
            "imageUrl": f"/api/character-images/{trait}/image"
        }
    except Exception as e:
        logger.error(f"Error uploading character image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")


@router.delete("/character-images/{trait}")
async def admin_delete_character_image(trait: str, email: str = Depends(verify_admin)):
    """Delete character trait image"""
    from bson import ObjectId

    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail="Invalid trait")

    record = await db.character_images.find_one({"trait": trait})
    if record and record.get('imageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(record['imageFileId']))
        except Exception:
            pass

    await db.character_images.delete_one({"trait": trait})
    return {"success": True}


@router.put("/character-images/{trait}/text")
async def admin_update_character_text(
    trait: str,
    data: CharacterTextUpdate,
    email: str = Depends(verify_admin)
):
    """Update text content for a character trait"""
    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail=f"Trait must be one of: {CHARACTER_TRAITS}")

    update_data = {"trait": trait, "updatedAt": datetime.now(timezone.utc)}

    if data.title is not None:
        update_data["title"] = data.title
    if data.shortDescription is not None:
        update_data["shortDescription"] = data.shortDescription
    if data.longDescription is not None:
        update_data["longDescription"] = data.longDescription

    await db.character_images.update_one(
        {"trait": trait},
        {"$set": update_data},
        upsert=True
    )

    # Return updated record
    record = await db.character_images.find_one({"trait": trait}, {"_id": 0})
    return {"success": True, "data": record}
