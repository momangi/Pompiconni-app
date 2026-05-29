"""Admin reviews router (Fase 4C router split)."""
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import verify_admin
from models import ReviewUpdate
from services import review_service


router = APIRouter()


@router.get("/reviews")
async def admin_get_reviews(email: str = Depends(verify_admin)):
    """Get all reviews for admin (including non-approved)"""
    return await review_service.get_admin_reviews()


@router.put("/reviews/{review_id}")
async def admin_update_review(review_id: str, update: ReviewUpdate, email: str = Depends(verify_admin)):
    """Approve or disapprove a review"""
    if not await review_service.set_review_approval(review_id, update.is_approved):
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    return {"success": True}


@router.delete("/reviews/{review_id}")
async def admin_delete_review(review_id: str, email: str = Depends(verify_admin)):
    """Delete a review"""
    if not await review_service.delete_review(review_id):
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    return {"success": True}
