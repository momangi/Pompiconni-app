"""Business rules for themes.

Covers the public list/detail composition (adds the dynamic
``backgroundImageUrl`` and defaults ``backgroundOpacity``), the admin
CRUD with theme<->illustrations integrity, and the helper used by the
illustrations domain to keep the cached ``illustrationCount`` in sync.

GridFS-backed background upload/serve endpoints stay in ``server.py`` for
this batch (out of 4B Batch 1 scope).
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import HTTPException

from repositories import theme_repo


_BACKGROUND_OPACITY_DEFAULT = 30


def _decorate(theme: dict) -> dict:
    """Add ``backgroundImageUrl`` and default ``backgroundOpacity``.

    Mutates and returns the input dict so it can be used inline.
    """
    if theme.get("backgroundImageFileId"):
        theme["backgroundImageUrl"] = f"/api/themes/{theme['id']}/background-image"
    if "backgroundOpacity" not in theme:
        theme["backgroundOpacity"] = _BACKGROUND_OPACITY_DEFAULT
    return theme


async def list_public() -> list[dict]:
    """Themes for the public site."""
    themes = await theme_repo.list_all()
    for t in themes:
        _decorate(t)
    return themes


async def get_public(theme_id: str) -> dict:
    """Single theme for the public site. Raises 404 if not found."""
    theme = await theme_repo.find_by_id(theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    return _decorate(theme)


# --- Admin --------------------------------------------------------------------

async def create_theme(payload) -> dict:
    """Insert a new theme. Returns the document ready for the response.

    ``payload`` is a Pydantic ``ThemeCreate``. We mirror the legacy
    handler verbatim: id is generated, counters and image fields are
    initialized, timestamps are set, ``_id`` is popped.
    """
    theme_dict = payload.dict()
    theme_dict["id"] = str(uuid.uuid4())
    theme_dict["illustrationCount"] = 0
    theme_dict["backgroundImageFileId"] = None
    theme_dict["backgroundImageUrl"] = None
    now = datetime.now(timezone.utc)
    theme_dict["createdAt"] = now
    theme_dict["updatedAt"] = now
    return await theme_repo.insert(theme_dict)


async def update_theme(theme_id: str, payload) -> dict:
    """Apply a partial update. 404 if the theme does not exist."""
    if not await theme_repo.exists(theme_id):
        raise HTTPException(status_code=404, detail="Tema non trovato")

    update_data: dict = {}
    for key, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            update_data[key] = value
    updated = await theme_repo.update(theme_id, update_data)
    # The repo already excluded ``_id``; decorate URL + opacity if needed.
    if updated and updated.get("backgroundImageFileId"):
        updated["backgroundImageUrl"] = f"/api/themes/{theme_id}/background-image"
    return updated


async def check_delete(theme_id: str) -> dict:
    """Return whether the theme can be deleted and the dependent count."""
    if not await theme_repo.exists(theme_id):
        raise HTTPException(status_code=404, detail="Tema non trovato")
    count = await theme_repo.count_illustrations(theme_id)
    return {
        "canDelete": count == 0,
        "illustrationCount": count,
        "message": (
            f"Questo tema ha {count} illustrazioni associate"
            if count > 0
            else "Tema eliminabile"
        ),
    }


async def delete_theme(theme_id: str, *, force: bool = False) -> dict:
    """Delete a theme. 400 if it has illustrations and ``force`` is False.

    When ``force`` is True we first unassign all dependent illustrations
    (set ``themeId=None``), preserving the legacy behaviour.
    """
    if not await theme_repo.exists(theme_id):
        raise HTTPException(status_code=404, detail="Tema non trovato")

    count = await theme_repo.count_illustrations(theme_id)
    if count > 0 and not force:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tema ha {count} illustrazioni. "
                "Usa force=true per rimuovere comunque."
            ),
        )
    if force and count > 0:
        await theme_repo.unassign_illustrations(theme_id)
    await theme_repo.delete(theme_id)
    return {
        "success": True,
        "message": (
            f"Tema eliminato. {count} illustrazioni riassegnate."
            if count > 0
            else "Tema eliminato."
        ),
    }


# --- Cross-domain helpers -----------------------------------------------------

async def recalc_illustration_count(theme_id: Optional[str]) -> None:
    """Refresh the cached counter for a theme. No-op if the id is falsy."""
    if not theme_id:
        return
    await theme_repo.recalc_illustration_count(theme_id)
