"""Public books + reading_progress router (Fase 4C router split).

Pure metadata + reading progress. GridFS (cover, scene colored/lineart
images) and PDF generation endpoints stay in ``server.py``.
"""
from typing import List

from fastapi import APIRouter

from services import book_service


router = APIRouter()


@router.get("/books", response_model=List[dict])
async def get_books():
    """Get all visible books for public display.
    R1 fix (Fase 4B Batch 4, approved cleanup): _id is no longer leaked.
    """
    return await book_service.list_public_books()


@router.get("/books/{book_id}")
async def get_book(book_id: str):
    """Get a single book with its scenes.
    R1 fix (Fase 4B Batch 4, approved cleanup): _id is no longer leaked
    in either ``book`` or ``scenes`` payloads.
    """
    return await book_service.get_public_book_with_scenes(book_id)


# Reading Progress
@router.get("/books/{book_id}/progress/{visitor_id}")
async def get_reading_progress(book_id: str, visitor_id: str):
    """Get reading progress for a visitor"""
    return await book_service.get_reading_progress(book_id, visitor_id)


@router.post("/books/{book_id}/progress/{visitor_id}")
async def save_reading_progress(book_id: str, visitor_id: str, scene: int):
    """Save reading progress for a visitor"""
    return await book_service.save_reading_progress(book_id, visitor_id, scene)
