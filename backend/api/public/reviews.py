"""Public reviews router (Fase 4C router split)."""
from typing import List

from fastapi import APIRouter

from services import review_service


router = APIRouter()


@router.get("/reviews", response_model=List[dict])
async def get_reviews():
    """Get public reviews - only approved ones if show_reviews is enabled"""
    return await review_service.get_public_reviews()
