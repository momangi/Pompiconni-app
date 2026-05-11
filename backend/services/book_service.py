"""Business rules for books, scenes and reading progress.

GridFS-heavy endpoints (cover upload/serve, scene image upload/serve,
public/admin PDF generation) intentionally stay in ``server.py`` for
this batch. Only the metadata/CRUD/list pipelines are extracted.

R1 fix (Fase 4B Batch 4, approved cleanup): every public/admin read
response now omits the BSON ``_id`` field for ``books`` and
``book_scenes``. No other key in the response shape is changed.
"""
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException

from models import MAX_SCENES_PER_BOOK
from repositories import book_repo, book_scene_repo, reading_progress_repo


# --- Public reads -----------------------------------------------------------

async def list_public_books() -> list[dict]:
    """Visible books for the public listing. R1: no ``_id``."""
    return await book_repo.list_visible()


async def get_public_book_with_scenes(book_id: str) -> dict:
    """Return ``{book, scenes}`` and increment ``viewCount``.

    Mirrors the legacy 404 semantics: missing book OR ``isVisible=False``
    both raise ``404 Libro non disponibile``. R1 applied to both shapes.
    """
    book = await book_repo.find_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    if not book.get("isVisible", True):
        raise HTTPException(status_code=404, detail="Libro non disponibile")

    scenes = await book_scene_repo.list_by_book(book_id)
    await book_repo.inc_view_count(book_id)
    return {"book": book, "scenes": scenes}


# --- Reading progress -------------------------------------------------------

async def get_reading_progress(book_id: str, visitor_id: str) -> dict:
    progress = await reading_progress_repo.get_for_visitor(book_id, visitor_id)
    if not progress:
        return {"currentScene": 1, "hasProgress": False}
    return {
        "currentScene": progress.get("currentScene", 1),
        "hasProgress": True,
    }


async def save_reading_progress(book_id: str, visitor_id: str, scene: int) -> dict:
    await reading_progress_repo.upsert_progress(book_id, visitor_id, scene)
    return {"success": True}


# --- Admin: books -----------------------------------------------------------

async def list_admin_books() -> list[dict]:
    """All books (any visibility) for admin. R1: no ``_id``."""
    return await book_repo.list_all_sorted()


async def create_book(payload) -> dict:
    """Insert a new book with the default counters."""
    book_dict = payload.dict()
    now = datetime.now(timezone.utc)
    book_dict.update({
        "id": str(uuid.uuid4()),
        "sceneCount": 0,
        "viewCount": 0,
        "downloadCount": 0,
        "coverImageFileId": None,
        "coverImageUrl": None,
        "createdAt": now,
        "updatedAt": now,
    })
    return await book_repo.insert(book_dict)


async def update_book(book_id: str, payload) -> dict:
    if not await book_repo.exists(book_id):
        raise HTTPException(status_code=404, detail="Libro non trovato")
    fields = payload.dict()
    fields["updatedAt"] = datetime.now(timezone.utc)
    await book_repo.update_fields(book_id, fields)
    return {"success": True}


async def prepare_admin_delete_book(book_id: str) -> tuple[dict, list[dict]]:
    """Return raw ``(book, scenes)`` so the route can clean GridFS, or 404."""
    book = await book_repo.find_raw(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    scenes = await book_scene_repo.list_raw_by_book(book_id)
    return book, scenes


async def finalize_admin_delete_book(book_id: str) -> dict:
    """Cascade delete: scenes → reading_progress → book."""
    await book_scene_repo.delete_all_by_book(book_id)
    await reading_progress_repo.delete_all_by_book(book_id)
    await book_repo.delete(book_id)
    return {"success": True, "message": "Libro eliminato con tutte le scene"}


# --- Admin: scenes ----------------------------------------------------------

async def list_admin_book_scenes(book_id: str) -> list[dict]:
    """All scenes for a book. R1: no ``_id``."""
    return await book_scene_repo.list_by_book(book_id)


async def create_scene(book_id: str, scene_number: int, sanitized_html: str) -> dict:
    """Insert a new scene after validating the legacy invariants.

    HTML sanitization is performed by the caller (``sanitize_scene_html``
    lives in ``server.py`` to avoid pulling its dependencies into this
    module). The service enforces the same 400/404 semantics as legacy.
    """
    if not await book_repo.exists(book_id):
        raise HTTPException(status_code=404, detail="Libro non trovato")

    current_count = await book_scene_repo.count_by_book(book_id)
    if current_count >= MAX_SCENES_PER_BOOK:
        raise HTTPException(
            status_code=400,
            detail=f"Limite massimo di {MAX_SCENES_PER_BOOK} scene raggiunto",
        )

    if scene_number < 1 or scene_number > MAX_SCENES_PER_BOOK:
        raise HTTPException(
            status_code=400,
            detail=f"Numero scena deve essere tra 1 e {MAX_SCENES_PER_BOOK}",
        )

    if await book_scene_repo.find_by_scene_number(book_id, scene_number):
        raise HTTPException(
            status_code=400,
            detail=f"Scena {scene_number} già esistente",
        )

    now = datetime.now(timezone.utc)
    scene_dict = {
        "id": str(uuid.uuid4()),
        "bookId": book_id,
        "sceneNumber": scene_number,
        "text": {"html": sanitized_html},
        "coloredImageFileId": None,
        "coloredImageUrl": None,
        "lineArtImageFileId": None,
        "lineArtImageUrl": None,
        "createdAt": now,
        "updatedAt": now,
    }
    await book_scene_repo.insert(scene_dict)
    await book_repo.inc_scene_count(book_id, 1)
    return scene_dict


async def update_scene_text(book_id: str, scene_id: str, sanitized_html: str) -> dict:
    scene = await book_scene_repo.find_raw(scene_id, book_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")
    await book_scene_repo.update_fields(
        scene_id, {"text": {"html": sanitized_html}}
    )
    return {"success": True}


async def prepare_admin_delete_scene(book_id: str, scene_id: str) -> dict:
    """Return raw scene so the route can clean GridFS, or 404."""
    scene = await book_scene_repo.find_raw(scene_id, book_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")
    return scene


async def finalize_admin_delete_scene(book_id: str, scene_id: str) -> dict:
    await book_scene_repo.delete(scene_id)
    await book_repo.inc_scene_count(book_id, -1)
    return {"success": True}
