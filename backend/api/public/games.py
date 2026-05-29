"""Public games router (Fase 4C router split).

Only list/detail metadata. GridFS thumbnail / card-image / page-image
endpoints stay in ``server.py``.
"""
from fastapi import APIRouter

from services import game_service


router = APIRouter()


@router.get("/games")
async def get_public_games():
    """Get all games for public display"""
    return await game_service.list_public_games()


@router.get("/games/{slug}")
async def get_public_game(slug: str):
    """Get a single game by slug"""
    return await game_service.get_public_game(slug)
