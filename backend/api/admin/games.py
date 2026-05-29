"""Admin games router (Fase 4C router split).

Metadata CRUD. The GridFS thumbnail, card-image and page-image upload
endpoints stay in ``server.py`` (heavy-media policy preserved).
"""
from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from core.database import gridfs_bucket
from services import game_service


router = APIRouter()


@router.get("/games")
async def get_admin_games(email: str = Depends(verify_admin)):
    """Get all games for admin"""
    return await game_service.list_admin_games()


@router.post("/games")
async def create_game(game_data: dict, email: str = Depends(verify_admin)):
    """Create a new game"""
    return await game_service.create_game(game_data)


@router.put("/games/{game_id}")
async def update_game(game_id: str, game_data: dict, email: str = Depends(verify_admin)):
    """Update a game"""
    return await game_service.update_game(game_id, game_data)


@router.delete("/games/{game_id}")
async def delete_game(game_id: str, email: str = Depends(verify_admin)):
    """Delete a game and all associated images"""
    from bson import ObjectId

    game = await game_service.prepare_admin_delete(game_id)

    # GridFS cleanup stays inline (heavy-media policy preserved).
    for file_id_key in ("thumbnailFileId", "cardImageFileId", "pageImageFileId"):
        file_id = game.get(file_id_key)
        if file_id:
            try:
                await gridfs_bucket.delete(ObjectId(file_id))
            except Exception:
                pass

    await game_service.finalize_admin_delete(game_id)
    return {"message": "Gioco eliminato"}
