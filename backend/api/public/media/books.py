"""Public books media router (Fase 5/M2).

GridFS scene image streams (colored/lineart), book cover with responsive
variants, and free-book PDF download. Logic preserved verbatim from
legacy ``server.py``.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.database import db, gridfs_bucket
from models import MAX_SCENES_PER_BOOK
from pdf_generator import generate_book_pdf
from streaming import stream_gridfs_response, stream_gridfs_response_with_variants
from utils.gridfs_helpers import get_gridfs_image


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/books/{book_id}/scene/{scene_number}/colored-image")
async def get_scene_colored_image(book_id: str, scene_number: int, request: Request):
    """Serve colored image for a scene (true streaming + ETag)."""
    scene = await db.book_scenes.find_one({"bookId": book_id, "sceneNumber": scene_number})
    if not scene or not scene.get('coloredImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=scene['coloredImageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=31536000, immutable",
        not_found_detail="Immagine non trovata",
    )


@router.get("/books/{book_id}/scene/{scene_number}/lineart-image")
async def get_scene_lineart_image(book_id: str, scene_number: int, request: Request):
    """Serve line art image for a scene (true streaming + ETag)."""
    scene = await db.book_scenes.find_one({"bookId": book_id, "sceneNumber": scene_number})
    if not scene or not scene.get('lineArtImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=scene['lineArtImageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=31536000, immutable",
        not_found_detail="Immagine non trovata",
    )


@router.get("/books/{book_id}/cover")
async def get_book_cover(
    book_id: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve book cover image (streaming + ETag + responsive variants)."""
    book = await db.books.find_one({"id": book_id})
    if not book or not book.get('coverImageFileId'):
        raise HTTPException(status_code=404, detail="Copertina non disponibile")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=book['coverImageFileId'],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Copertina non trovata",
    )


@router.get("/books/{book_id}/pdf")
async def download_book_pdf_public(book_id: str):
    """
    Download PDF for a FREE book (public access).
    Premium books cannot be downloaded without payment.
    """
    # Get book
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")

    # Check visibility
    if not book.get('isVisible', True):
        raise HTTPException(status_code=404, detail="Libro non disponibile")

    # Check if free
    if not book.get('isFree', True):
        raise HTTPException(status_code=403, detail="Pagamenti non ancora attivi. Questo libro è premium.")

    # Check if download is allowed
    if not book.get('allowDownload', True):
        raise HTTPException(status_code=403, detail="Download non abilitato per questo libro")

    # Get scenes
    scenes = await db.book_scenes.find({"bookId": book_id}).sort("sceneNumber", 1).to_list(MAX_SCENES_PER_BOOK)
    if not scenes:
        raise HTTPException(status_code=404, detail="Questo libro non ha ancora scene")

    # Generate PDF
    try:
        pdf_buffer = await generate_book_pdf(book, scenes, get_gridfs_image)

        # Increment download count
        await db.books.update_one({"id": book_id}, {"$inc": {"downloadCount": 1}})

        # Create filename
        filename = f"poppiconni_{book_id}.pdf"

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"Error generating PDF for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Errore nella generazione del PDF")
