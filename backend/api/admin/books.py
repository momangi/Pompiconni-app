"""Admin books + book_scenes router (Fase 4C router split).

Metadata CRUD for books and scenes. The GridFS cover upload, scene
colored/lineart image uploads and PDF generation/download endpoints
stay in ``server.py``. HTML sanitization (``sanitize_scene_html``) is
imported from ``server`` to preserve identical behaviour.
"""
from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from core.database import gridfs_bucket
from models import BookCreate, BookSceneCreate, BookSceneText
from services import book_service
from utils.html_sanitizer import sanitize_scene_html


router = APIRouter()


# --- Books ------------------------------------------------------------------

@router.get("/books")
async def admin_get_books(email: str = Depends(verify_admin)):
    """Get all books for admin.
    R1 fix (Fase 4B Batch 4, approved cleanup): _id is no longer leaked.
    """
    return await book_service.list_admin_books()


@router.post("/books")
async def admin_create_book(book: BookCreate, email: str = Depends(verify_admin)):
    """Create a new book"""
    return await book_service.create_book(book)


@router.put("/books/{book_id}")
async def admin_update_book(book_id: str, book: BookCreate, email: str = Depends(verify_admin)):
    """Update book details"""
    return await book_service.update_book(book_id, book)


@router.delete("/books/{book_id}")
async def admin_delete_book(book_id: str, email: str = Depends(verify_admin)):
    """Delete a book and all its scenes"""
    from bson import ObjectId

    book, scenes = await book_service.prepare_admin_delete_book(book_id)

    # GridFS cleanup stays inline (heavy-media policy preserved).
    if book.get("coverImageFileId"):
        try:
            await gridfs_bucket.delete(ObjectId(book["coverImageFileId"]))
        except Exception:
            pass

    for scene in scenes:
        if scene.get("coloredImageFileId"):
            try:
                await gridfs_bucket.delete(ObjectId(scene["coloredImageFileId"]))
            except Exception:
                pass
        if scene.get("lineArtImageFileId"):
            try:
                await gridfs_bucket.delete(ObjectId(scene["lineArtImageFileId"]))
            except Exception:
                pass

    return await book_service.finalize_admin_delete_book(book_id)


# --- Book scenes ------------------------------------------------------------

@router.get("/books/{book_id}/scenes")
async def admin_get_book_scenes(book_id: str, email: str = Depends(verify_admin)):
    """Get all scenes for a book.
    R1 fix (Fase 4B Batch 4, approved cleanup): _id is no longer leaked.
    """
    return await book_service.list_admin_book_scenes(book_id)


@router.post("/books/{book_id}/scenes")
async def admin_create_scene(book_id: str, scene: BookSceneCreate, email: str = Depends(verify_admin)):
    """Create a new scene for a book"""
    sanitized_html = sanitize_scene_html(scene.text.html)
    return await book_service.create_scene(book_id, scene.sceneNumber, sanitized_html)


@router.put("/books/{book_id}/scenes/{scene_id}")
async def admin_update_scene(
    book_id: str,
    scene_id: str,
    text: BookSceneText,
    email: str = Depends(verify_admin),
):
    """Update scene text with HTML sanitization"""
    sanitized_html = sanitize_scene_html(text.html)
    return await book_service.update_scene_text(book_id, scene_id, sanitized_html)


@router.delete("/books/{book_id}/scenes/{scene_id}")
async def admin_delete_scene(book_id: str, scene_id: str, email: str = Depends(verify_admin)):
    """Delete a scene"""
    from bson import ObjectId

    scene = await book_service.prepare_admin_delete_scene(book_id, scene_id)

    # GridFS cleanup stays inline (heavy-media policy preserved).
    if scene.get("coloredImageFileId"):
        try:
            await gridfs_bucket.delete(ObjectId(scene["coloredImageFileId"]))
        except Exception:
            pass
    if scene.get("lineArtImageFileId"):
        try:
            await gridfs_bucket.delete(ObjectId(scene["lineArtImageFileId"]))
        except Exception:
            pass

    return await book_service.finalize_admin_delete_scene(book_id, scene_id)
