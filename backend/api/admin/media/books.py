"""Admin books media router (Fase 5/M2).

PDF preview (admin override), book cover upload, scene image uploads
(colored + lineart). GridFS cleanup + variant fire-and-forget preserved
verbatim from legacy ``server.py``.
"""
from datetime import datetime, timezone
import io
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket
from media_pipeline import ensure_variants
from models import MAX_SCENES_PER_BOOK
from pdf_generator import generate_book_pdf
from utils.gridfs_helpers import get_gridfs_image


logger = logging.getLogger(__name__)

router = APIRouter()


def _fire_variants(file_id) -> None:
    """Fire-and-forget variant generation. Safe to call after any image upload."""
    import asyncio

    try:
        asyncio.create_task(ensure_variants(db, gridfs_bucket, file_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not schedule variants for {file_id}: {e}")


@router.get("/books/{book_id}/pdf")
async def admin_download_book_pdf(book_id: str, email: str = Depends(verify_admin)):
    """
    Download PDF for ANY book (admin access).
    Admin can download both free and premium books for preview/testing.
    """
    # Get book
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")

    # Get scenes
    scenes = await db.book_scenes.find({"bookId": book_id}).sort("sceneNumber", 1).to_list(MAX_SCENES_PER_BOOK)
    if not scenes:
        raise HTTPException(status_code=404, detail="Questo libro non ha ancora scene")

    # Generate PDF
    try:
        pdf_buffer = await generate_book_pdf(book, scenes, get_gridfs_image)

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


@router.post("/books/{book_id}/cover")
async def admin_upload_book_cover(
    book_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload book cover image"""
    from bson import ObjectId

    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        filename = f"book_cover_{book_id}{ext}"

        # Delete old cover if exists
        if book.get('coverImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(book['coverImageFileId']))
            except Exception:
                pass

        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"book_id": book_id, "type": "cover", "content_type": content_type}
        )

        # Update book
        await db.books.update_one(
            {"id": book_id},
            {
                "$set": {
                    "coverImageFileId": str(file_id),
                    "coverImageUrl": f"/api/books/{book_id}/cover",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        _fire_variants(file_id)

        return {"success": True, "coverUrl": f"/api/books/{book_id}/cover"}
    except Exception as e:
        logger.error(f"Error uploading book cover: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")


@router.post("/books/{book_id}/scenes/{scene_id}/colored-image")
async def admin_upload_scene_colored_image(
    book_id: str,
    scene_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload colored image for a scene"""
    from bson import ObjectId

    scene = await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        filename = f"scene_colored_{scene_id}{ext}"

        # Delete old image
        if scene.get('coloredImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(scene['coloredImageFileId']))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"scene_id": scene_id, "type": "colored", "content_type": content_type}
        )

        await db.book_scenes.update_one(
            {"id": scene_id},
            {
                "$set": {
                    "coloredImageFileId": str(file_id),
                    "coloredImageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/colored-image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        return {"success": True, "imageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/colored-image"}
    except Exception as e:
        logger.error(f"Error uploading colored image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")


@router.post("/books/{book_id}/scenes/{scene_id}/lineart-image")
async def admin_upload_scene_lineart_image(
    book_id: str,
    scene_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin)
):
    """Upload line art image for a scene"""
    from bson import ObjectId

    scene = await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")

    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")

    try:
        content = await file.read()
        filename = f"scene_lineart_{scene_id}{ext}"

        # Delete old image
        if scene.get('lineArtImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(scene['lineArtImageFileId']))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"scene_id": scene_id, "type": "lineart", "content_type": content_type}
        )

        await db.book_scenes.update_one(
            {"id": scene_id},
            {
                "$set": {
                    "lineArtImageFileId": str(file_id),
                    "lineArtImageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/lineart-image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        return {"success": True, "imageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/lineart-image"}
    except Exception as e:
        logger.error(f"Error uploading lineart image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")
