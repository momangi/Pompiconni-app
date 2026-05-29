"""Public themes router (Fase 4C router split).

Pure CRUD/metadata GETs. The media-heavy ``/themes/{id}/background-image``
endpoint stays in ``server.py`` (GridFS streaming + variants).
"""
from typing import List

from fastapi import APIRouter

from models import THEME_COLOR_PALETTE
from services import theme_service


router = APIRouter()


@router.get("/themes", response_model=List[dict])
async def get_themes():
    return await theme_service.list_public()


@router.get("/themes/{theme_id}")
async def get_theme(theme_id: str):
    return await theme_service.get_public(theme_id)


@router.get("/theme-colors")
async def get_theme_color_palette():
    """Get available theme colors"""
    return THEME_COLOR_PALETTE
