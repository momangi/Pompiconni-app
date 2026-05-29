"""Public bundles router (Fase 4C router split).

Only the list endpoint is moved. GridFS background-image / download /
download-pdf endpoints stay in ``server.py``.
"""
from typing import List

from fastapi import APIRouter

from services import bundle_service


router = APIRouter()


@router.get("/bundles", response_model=List[dict])
async def get_bundles():
    """Get public bundles - only active ones, sorted by sortOrder"""
    return await bundle_service.list_public_bundles()
