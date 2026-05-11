"""Business rules for game level backgrounds (Bolle Magiche).

GridFS-tied endpoints (image serve, upload-on-create, upload-replace,
delete-with-cleanup) keep their logic in ``server.py`` for this batch.
This service covers the JSON-only flows: list, partial update, validation
helpers and the small cross-domain helpers required by media routes.
"""
from fastapi import HTTPException

from repositories import level_background_repo


DEFAULT_GAME_SLUG = level_background_repo.DEFAULT_GAME_SLUG
_RANGE_SPAN = 5  # 5 livelli per range (1-5, 6-10, ...)


# --- Internal helpers ---------------------------------------------------------

def _decorate(bg: dict) -> dict:
    """Add ``backgroundImageUrl`` in-place when an image is attached."""
    if bg.get("backgroundImageFileId"):
        bg["backgroundImageUrl"] = (
            f"/api/games/bolle-magiche/level-backgrounds/{bg['id']}/image"
        )
    return bg


# --- Public/Admin reads (same shape, different auth at the route) -----------

async def list_public_backgrounds() -> list[dict]:
    backgrounds = await level_background_repo.list_for_game(DEFAULT_GAME_SLUG)
    for bg in backgrounds:
        _decorate(bg)
    return backgrounds


async def list_admin_backgrounds() -> list[dict]:
    """Identical shape to public list — legacy admin route returns the same."""
    return await list_public_backgrounds()


# --- Validation used by create endpoint --------------------------------------

def validate_range(level_range_start: int, level_range_end: int) -> None:
    """Raise 400 if the level range is invalid (legacy rules)."""
    if level_range_start >= level_range_end:
        raise HTTPException(
            status_code=400,
            detail="levelRangeStart deve essere minore di levelRangeEnd",
        )
    if level_range_end - level_range_start != (_RANGE_SPAN - 1):
        raise HTTPException(
            status_code=400,
            detail=f"Il range deve essere di {_RANGE_SPAN} livelli (es. 1-5, 6-10)",
        )


async def ensure_no_overlap(level_range_start: int, level_range_end: int) -> None:
    """Raise 400 if an existing background overlaps the given range."""
    existing = await level_background_repo.find_overlapping(
        level_range_start, level_range_end, DEFAULT_GAME_SLUG
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Esiste già uno sfondo per questo range di livelli",
        )


# --- Update -------------------------------------------------------------------

async def update_background(
    bg_id: str,
    level_range_start: int | None,
    level_range_end: int | None,
    background_opacity: int | None,
) -> dict:
    """Apply a partial update from the admin form."""
    bg = await level_background_repo.find_by_id(bg_id)
    if not bg:
        raise HTTPException(status_code=404, detail="Sfondo non trovato")

    update_data: dict = {}
    if level_range_start is not None:
        update_data["levelRangeStart"] = level_range_start
    if level_range_end is not None:
        update_data["levelRangeEnd"] = level_range_end
    if background_opacity is not None:
        update_data["backgroundOpacity"] = background_opacity

    updated = await level_background_repo.update_fields(bg_id, update_data)
    return _decorate(updated) if updated else None


# --- Cross-domain helpers (used by media routes still in server.py) ---------

async def get_raw_background(bg_id: str) -> dict:
    """Return the raw doc with ``_id``/FileID for image upload/delete flows."""
    bg = await level_background_repo.find_raw_by_id(bg_id)
    if not bg:
        raise HTTPException(status_code=404, detail="Sfondo non trovato")
    return bg


def public_image_url(bg_id: str) -> str:
    """Stable URL builder, kept here so server.py uses one source of truth."""
    return f"/api/games/bolle-magiche/level-backgrounds/{bg_id}/image"
