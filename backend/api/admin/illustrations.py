"""Admin illustrations router (Fase 4C router split).

Metadata CRUD + publish/download-enabled toggles. The attach-pdf,
attach-image and AI generate endpoints (GridFS-heavy) stay in
``server.py``. ``PUT /illustrations/{id}/theme`` is kept on
``server.py`` as a cross-domain helper not yet refactored to service.
"""
from typing import Optional

from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from models import IllustrationCreate
from services import illustration_service


router = APIRouter()


@router.post("/illustrations")
async def create_illustration(illustration: IllustrationCreate, email: str = Depends(verify_admin)):
    # R1 fix (Fase 4B Batch 3): _id is no longer included in the response.
    return await illustration_service.create_illustration(illustration)


@router.get("/illustrations")
async def get_admin_illustrations(
    themeId: Optional[str] = None,
    isPublished: Optional[bool] = None,
    email: str = Depends(verify_admin),
):
    """Admin endpoint: get all illustrations including drafts, with optional filters.
    R1 fix (Fase 4B Batch 3, approved cleanup): _id is no longer leaked.
    """
    return await illustration_service.list_admin_illustrations(
        themeId=themeId, isPublished=isPublished
    )


@router.put("/illustrations/{illustration_id}/publish")
async def toggle_illustration_publish(illustration_id: str, email: str = Depends(verify_admin)):
    """Toggle the published status of an illustration"""
    return await illustration_service.toggle_publish(illustration_id)


@router.put("/illustrations/{illustration_id}/download-enabled")
async def toggle_illustration_download(illustration_id: str, email: str = Depends(verify_admin)):
    """Toggle the downloadEnabled status of an illustration"""
    return await illustration_service.toggle_download_enabled(illustration_id)


@router.put("/illustrations/{illustration_id}")
async def update_illustration(
    illustration_id: str,
    illustration: IllustrationCreate,
    email: str = Depends(verify_admin),
):
    return await illustration_service.update_illustration(illustration_id, illustration)


@router.delete("/illustrations/{illustration_id}")
async def delete_illustration(illustration_id: str, email: str = Depends(verify_admin)):
    return await illustration_service.delete_illustration(illustration_id)
