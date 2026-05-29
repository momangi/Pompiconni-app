"""Public Bolle Magiche level-backgrounds router (Fase 4C router split).

Only the list endpoint is moved. The GridFS image stream stays in
``server.py``.
"""
from fastapi import APIRouter

from services import level_background_service


router = APIRouter()


@router.get("/games/bolle-magiche/level-backgrounds")
async def get_level_backgrounds():
    """Get all level backgrounds for Bolle Magiche (public)"""
    return await level_background_service.list_public_backgrounds()
