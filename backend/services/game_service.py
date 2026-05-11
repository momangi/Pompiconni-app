"""Business rules for games.

GridFS-heavy paths (thumbnail/card-image/page-image upload, serve, delete)
keep their implementation in ``server.py``. This service owns the JSON
CRUD: list, single, create, update, delete-document.

Response shape decoration (``thumbnailUrl``, ``cardImageUrl``,
``pageImageUrl``) is performed here so the route handlers become thin.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import HTTPException

from repositories import game_repo


# --- Internal helpers ---------------------------------------------------------

def _cache_bust(game: dict) -> str:
    """Return the cache-busting suffix derived from ``updatedAt``.

    Matches the legacy logic: int Unix timestamp of ``updatedAt`` if it
    exists, otherwise an empty string. The value is interpolated into
    ``?v=<n>`` URLs to invalidate the browser cache after admin edits.
    """
    updated = game.get("updatedAt")
    if updated:
        return str(int(updated.timestamp()))
    return ""


def _decorate(game: dict) -> dict:
    """Add ``thumbnailUrl`` / ``cardImageUrl`` / ``pageImageUrl`` in-place."""
    bust = _cache_bust(game)
    slug = game.get("slug")
    if game.get("thumbnailFileId"):
        game["thumbnailUrl"] = f"/api/games/{slug}/thumbnail?v={bust}"
    if game.get("cardImageFileId"):
        game["cardImageUrl"] = f"/api/games/{slug}/card-image?v={bust}"
    if game.get("pageImageFileId"):
        game["pageImageUrl"] = f"/api/games/{slug}/page-image?v={bust}"
    return game


# --- Public -------------------------------------------------------------------

async def list_public_games() -> list[dict]:
    games = await game_repo.list_all_sorted()
    for g in games:
        _decorate(g)
    return games


async def get_public_game(slug: str) -> dict:
    game = await game_repo.find_by_slug(slug)
    if not game:
        raise HTTPException(status_code=404, detail="Gioco non trovato")
    return _decorate(game)


# --- Admin reads --------------------------------------------------------------

async def list_admin_games() -> list[dict]:
    games = await game_repo.list_all_sorted()
    for g in games:
        _decorate(g)
    return games


# --- Admin mutations ----------------------------------------------------------

async def create_game(game_data: dict) -> dict:
    """Insert a new game. 400 if the slug already exists.

    Mirrors the legacy ``POST /api/admin/games`` handler verbatim, including
    the implicit defaults for optional fields.
    """
    slug = game_data.get("slug")
    if await game_repo.exists_by_slug(slug):
        raise HTTPException(status_code=400, detail="Slug già esistente")

    now = datetime.now(timezone.utc)
    game = {
        "id": str(uuid.uuid4()),
        "slug": slug,
        "title": game_data.get("title"),
        "shortDescription": game_data.get("shortDescription", ""),
        "longDescription": game_data.get("longDescription", ""),
        "status": game_data.get("status", "coming_soon"),
        "ageRecommended": game_data.get("ageRecommended", "3+"),
        "howToPlay": game_data.get("howToPlay", []),
        "thumbnailFileId": None,
        "sortOrder": game_data.get("sortOrder", 0),
        "createdAt": now,
        "updatedAt": now,
    }
    return await game_repo.insert(game)


async def update_game(game_id: str, game_data: dict) -> dict:
    """Update game fields and return the decorated refreshed document."""
    current = await game_repo.find_raw_by_id(game_id)
    if not current:
        raise HTTPException(status_code=404, detail="Gioco non trovato")

    # Build update dict copying legacy defaults so existing values are
    # preserved when the client omits a key.
    update_data = {
        "title": game_data.get("title", current["title"]),
        "slug": game_data.get("slug", current["slug"]),
        "shortDescription": game_data.get("shortDescription", current.get("shortDescription", "")),
        "longDescription": game_data.get("longDescription", current.get("longDescription", "")),
        "status": game_data.get("status", current.get("status", "coming_soon")),
        "ageRecommended": game_data.get("ageRecommended", current.get("ageRecommended", "3+")),
        "howToPlay": game_data.get("howToPlay", current.get("howToPlay", [])),
        "sortOrder": game_data.get("sortOrder", current.get("sortOrder", 0)),
        # Opacity values are clamped to [0..100] (legacy behaviour).
        "cardImageOpacity": max(0, min(100, int(
            game_data.get("cardImageOpacity", current.get("cardImageOpacity", 35))
        ))),
        "pageImageOpacity": max(0, min(100, int(
            game_data.get("pageImageOpacity", current.get("pageImageOpacity", 25))
        ))),
    }
    updated = await game_repo.update_fields(game_id, update_data)
    return _decorate(updated) if updated else None


async def prepare_admin_delete(game_id: str) -> dict:
    """Return the raw game doc so the route can cleanup GridFS images.

    Raises 404 if the game does not exist.
    """
    game = await game_repo.find_raw_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Gioco non trovato")
    return game


async def finalize_admin_delete(game_id: str) -> None:
    """Delete the game document. The route does GridFS cleanup beforehand."""
    await game_repo.delete(game_id)
