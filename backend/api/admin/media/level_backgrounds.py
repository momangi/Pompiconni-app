"""Admin level-backgrounds media router (Fase 5/M2).

Create (with optional inline upload), image upload/replace, and delete
endpoints for "Bolle Magiche" level backgrounds. Logic preserved verbatim
from legacy ``server.py``.

Tech debt notes (preserved verbatim, intentionally not refactored in M2):
- ``admin_delete_level_background`` mixes the service-layer accessor
  ``level_background_service.get_raw_background(bg_id)`` with a direct
  ``db.game_level_backgrounds.delete_one`` call. Pre-existing inconsistency.
"""
from datetime import datetime, timezone
import io
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket
from services import level_background_service


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/games/bolle-magiche/level-backgrounds")
async def admin_create_level_background(
    levelRangeStart: int = Form(...),
    levelRangeEnd: int = Form(...),
    backgroundOpacity: int = Form(30),
    backgroundImage: UploadFile = File(None),
    user_id: str = Depends(verify_admin)
):
    """Admin: Create a new level background"""

    # Validate range
    if levelRangeStart >= levelRangeEnd:
        raise HTTPException(status_code=400, detail="levelRangeStart deve essere minore di levelRangeEnd")

    if levelRangeEnd - levelRangeStart != 4:
        raise HTTPException(status_code=400, detail="Il range deve essere di 5 livelli (es. 1-5, 6-10)")

    # Check for overlapping ranges
    existing = await db.game_level_backgrounds.find_one({
        "gameSlug": "bolle-magiche",
        "$or": [
            {"levelRangeStart": {"$lte": levelRangeEnd, "$gte": levelRangeStart}},
            {"levelRangeEnd": {"$lte": levelRangeEnd, "$gte": levelRangeStart}}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Esiste già uno sfondo per questo range di livelli")

    new_bg = {
        "id": str(uuid.uuid4()),
        "gameSlug": "bolle-magiche",
        "levelRangeStart": levelRangeStart,
        "levelRangeEnd": levelRangeEnd,
        "backgroundOpacity": backgroundOpacity,
        "backgroundImageFileId": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }

    # Upload image if provided
    if backgroundImage:
        content = await backgroundImage.read()
        file_id = await gridfs_bucket.upload_from_stream(
            f"level_bg_{levelRangeStart}_{levelRangeEnd}",
            io.BytesIO(content),
            metadata={"content_type": backgroundImage.content_type, "bg_id": new_bg["id"]}
        )
        new_bg["backgroundImageFileId"] = str(file_id)

    await db.game_level_backgrounds.insert_one(new_bg)

    result = {k: v for k, v in new_bg.items() if k != "_id"}
    if result.get('backgroundImageFileId'):
        result['backgroundImageUrl'] = f"/api/games/bolle-magiche/level-backgrounds/{result['id']}/image"

    return result


@router.post("/games/bolle-magiche/level-backgrounds/{bg_id}/image")
async def admin_upload_level_background_image(
    bg_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(verify_admin)
):
    """Admin: Upload/replace level background image"""
    from bson import ObjectId

    bg = await db.game_level_backgrounds.find_one({"id": bg_id})
    if not bg:
        raise HTTPException(status_code=404, detail="Sfondo non trovato")

    # Delete old image if exists
    if bg.get('backgroundImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(bg['backgroundImageFileId']))
        except Exception:
            pass

    # Upload new image
    content = await file.read()
    file_id = await gridfs_bucket.upload_from_stream(
        f"level_bg_{bg['levelRangeStart']}_{bg['levelRangeEnd']}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "bg_id": bg_id}
    )

    await db.game_level_backgrounds.update_one(
        {"id": bg_id},
        {"$set": {
            "backgroundImageFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    return {"success": True, "backgroundImageUrl": f"/api/games/bolle-magiche/level-backgrounds/{bg_id}/image"}


@router.delete("/games/bolle-magiche/level-backgrounds/{bg_id}")
async def admin_delete_level_background(
    bg_id: str,
    user_id: str = Depends(verify_admin)
):
    """Admin: Delete a level background.

    NOTE: mix of ``level_background_service.get_raw_background`` and raw
    ``db.game_level_backgrounds.delete_one`` preserved verbatim (tech debt).
    """
    from bson import ObjectId

    bg = await level_background_service.get_raw_background(bg_id)

    # GridFS cleanup remains inline (Fase 4B Batch 2 scope).
    if bg.get('backgroundImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(bg['backgroundImageFileId']))
        except Exception:
            pass

    await db.game_level_backgrounds.delete_one({"id": bg_id})
    return {"success": True}
