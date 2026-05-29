"""Public posters router (Fase 4C router split).

Only list/detail metadata. The GridFS image stream and PDF download
endpoints stay in ``server.py``.
"""
from fastapi import APIRouter

from services import poster_service


router = APIRouter()


@router.get("/posters")
async def get_public_posters():
    """Get all published posters for public display"""
    return await poster_service.list_public_posters()


@router.get("/posters/{poster_id}")
async def get_public_poster(poster_id: str):
    """Get a single published poster by ID"""
    return await poster_service.get_public_poster(poster_id)
