"""Admin Bolle Magiche level-backgrounds router (Fase 4C router split).

Metadata-only routes (list + update). The create flow has GridFS upload
intertwined and the image-upload/delete flows touch GridFS directly;
both stay in ``server.py`` (heavy-media policy preserved).
"""
from fastapi import APIRouter, Depends, Form

from api.dependencies import verify_admin
from services import level_background_service


router = APIRouter()


@router.get("/games/bolle-magiche/level-backgrounds")
async def admin_get_level_backgrounds(user_id: str = Depends(verify_admin)):
    """Admin: Get all level backgrounds"""
    return await level_background_service.list_admin_backgrounds()


@router.put("/games/bolle-magiche/level-backgrounds/{bg_id}")
async def admin_update_level_background(
    bg_id: str,
    levelRangeStart: int = Form(None),
    levelRangeEnd: int = Form(None),
    backgroundOpacity: int = Form(None),
    user_id: str = Depends(verify_admin),
):
    """Admin: Update level background settings"""
    return await level_background_service.update_background(
        bg_id, levelRangeStart, levelRangeEnd, backgroundOpacity
    )
