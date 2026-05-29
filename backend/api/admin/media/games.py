"""Admin games media router (Fase 5/M2).

GridFS image uploads (thumbnail, card-image, page-image) with variant
fire-and-forget, plus delete endpoints for card/page images. Logic
preserved verbatim from legacy ``server.py``.

Tech debt notes (preserved verbatim, intentionally not refactored in M2):
- ``delete_game_page_image`` uses the legacy auth pattern
  ``credentials: HTTPAuthorizationCredentials = Depends(security)`` +
  ``verify_token(credentials.credentials)`` instead of the standard
  ``email: str = Depends(verify_admin)`` used by sibling routes.
"""
from datetime import datetime, timezone
import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket
from core.security import security_bearer as security, verify_token
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


# ============== THUMBNAIL ==============

@router.post("/games/{game_id}/thumbnail")
async def upload_game_thumbnail(game_id: str, file: UploadFile = File(...), email: str = Depends(verify_admin)):
    """Upload game thumbnail"""
    from bson import ObjectId

    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Gioco non trovato")

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo file non supportato")

    content = await file.read()

    # Delete old thumbnail if exists
    if game.get('thumbnailFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['thumbnailFileId']))
        except:
            pass

    # Upload new thumbnail
    file_id = await gridfs_bucket.upload_from_stream(
        f"game_thumbnail_{game['slug']}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "game_id": game_id}
    )

    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "thumbnailFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    _fire_variants(file_id)

    return {"success": True, "thumbnailUrl": f"/api/games/{game['slug']}/thumbnail"}


# ============== CARD IMAGE ==============

@router.post("/games/{game_id}/card-image")
async def upload_game_card_image(
    game_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload card image for game (used in /giochi list page)"""
    from bson import ObjectId

    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Delete old card image if exists
    if game.get('cardImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['cardImageFileId']))
        except Exception:
            pass

    content = await file.read()
    file_id = await gridfs_bucket.upload_from_stream(
        f"game_card_{game_id}_{file.filename}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "game_id": game_id, "type": "card"}
    )

    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "cardImageFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    _fire_variants(file_id)

    return {"success": True, "cardImageUrl": f"/api/games/{game['slug']}/card-image"}


@router.delete("/games/{game_id}/card-image")
async def delete_game_card_image(
    game_id: str,
    email: str = Depends(verify_admin)
):
    """Delete card image for game"""
    from bson import ObjectId

    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Delete from GridFS
    if game.get('cardImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['cardImageFileId']))
        except Exception:
            pass

    # Clear DB fields (set to null)
    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "cardImageFileId": None,
            "cardImageUrl": None,
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    return {"success": True, "message": "Card image removed"}


# ============== PAGE IMAGE ==============

@router.post("/games/{game_id}/page-image")
async def upload_game_page_image(
    game_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload page background image for game (used in /giochi/:slug page)"""
    from bson import ObjectId

    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Delete old page image if exists
    if game.get('pageImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['pageImageFileId']))
        except Exception:
            pass

    content = await file.read()
    file_id = await gridfs_bucket.upload_from_stream(
        f"game_page_{game_id}_{file.filename}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "game_id": game_id, "type": "page"}
    )

    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "pageImageFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    _fire_variants(file_id)

    return {"success": True, "pageImageUrl": f"/api/games/{game['slug']}/page-image"}


@router.delete("/games/{game_id}/page-image")
async def delete_game_page_image(
    game_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete page background image for game.

    NOTE: legacy anomalous auth pattern preserved verbatim — uses manual
    ``HTTPAuthorizationCredentials`` + ``verify_token(credentials.credentials)``
    rather than the canonical ``Depends(verify_admin)``. Tech debt, M2 keeps
    it identical.
    """
    from bson import ObjectId
    verify_token(credentials.credentials)

    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Delete from GridFS
    if game.get('pageImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['pageImageFileId']))
        except Exception:
            pass

    # Clear DB fields (set to null)
    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "pageImageFileId": None,
            "pageImageUrl": None,
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    return {"success": True, "message": "Page image removed"}
