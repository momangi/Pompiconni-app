"""Public illustrations router (Fase 4C router split).

Pure CRUD/metadata reads. Media-heavy routes (image streaming with
variants, image-status, download, download-status, search) intentionally
stay in ``server.py``.
"""
from typing import List, Optional

from fastapi import APIRouter

from services import illustration_service


router = APIRouter()


@router.get("/illustrations", response_model=List[dict])
async def get_illustrations(themeId: Optional[str] = None, isFree: Optional[bool] = None):
    # R1 fix (Fase 4B Batch 3, approved cleanup): _id is no longer leaked.
    return await illustration_service.list_public_illustrations(
        themeId=themeId, isFree=isFree
    )


@router.get("/illustrations/{illustration_id}")
async def get_illustration(illustration_id: str):
    # R1 fix (Fase 4B Batch 3, approved cleanup): _id is no longer leaked.
    return await illustration_service.get_public_illustration(illustration_id)
