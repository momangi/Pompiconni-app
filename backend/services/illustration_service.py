"""Business rules for illustrations.

This service owns the read/list/CRUD pipelines for the ``illustrations``
domain. GridFS-heavy operations (image streaming, PDF download / attach,
search, generated PDFs, etc.) are intentionally left in ``server.py`` for
this batch — only metadata/CRUD logic is extracted.

R1 fix (approved cleanup, Fase 4B Batch 3): every public/admin read
response now omits the BSON ``_id`` field. The legacy behaviour leaked
``str(_id)`` to clients; this is removed without changing any other key
in the response shape.
"""
from datetime import datetime, timezone
import uuid
from typing import Optional

from fastapi import HTTPException

from repositories import illustration_repo
from services import bundle_service, theme_service


# --- Helpers ----------------------------------------------------------------

def _attach_real_download_counts(
    illustrations: list[dict],
    counts: dict[str, int],
) -> list[dict]:
    """Mutate each illustration with the real ``downloadCount`` value."""
    for i in illustrations:
        i["downloadCount"] = counts.get(i.get("id"), 0)
    return illustrations


# --- Public reads -----------------------------------------------------------

async def list_public_illustrations(
    themeId: Optional[str] = None,
    isFree: Optional[bool] = None,
) -> list[dict]:
    """Return published illustrations matching the optional filters.

    R1 fix applied: ``_id`` is excluded by the repository projection.
    """
    query: dict = {"isPublished": True}
    if themeId:
        query["themeId"] = themeId
    if isFree is not None:
        query["isFree"] = isFree

    illustrations = await illustration_repo.list_by_filter(query)
    counts = await illustration_repo.real_download_counts()
    return _attach_real_download_counts(illustrations, counts)


async def get_public_illustration(illustration_id: str) -> dict:
    """Fetch a single published illustration with real download count.

    R1 fix applied: response no longer contains ``_id``.
    """
    illust = await illustration_repo.find_published_by_id(illustration_id)
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    illust["downloadCount"] = await illustration_repo.real_download_count_for(
        illustration_id
    )
    return illust


# --- Admin reads ------------------------------------------------------------

async def list_admin_illustrations(
    themeId: Optional[str] = None,
    isPublished: Optional[bool] = None,
) -> list[dict]:
    """Return every illustration (including drafts) for admin views.

    R1 fix applied: ``_id`` is excluded by the repository projection.
    """
    query: dict = {}
    if themeId:
        query["themeId"] = themeId
    if isPublished is not None:
        query["isPublished"] = isPublished

    illustrations = await illustration_repo.list_by_filter(query)
    counts = await illustration_repo.real_download_counts()
    return _attach_real_download_counts(illustrations, counts)


# --- Admin mutations --------------------------------------------------------

async def create_illustration(payload) -> dict:
    """Insert a new illustration (drafts by default) and refresh counters."""
    illust_dict = payload.dict()
    now = datetime.now(timezone.utc)
    illust_dict.update({
        "id": str(uuid.uuid4()),
        "downloadCount": 0,
        "pdfFileId": None,
        "imageFileId": None,
        "isPublished": False,  # new illustrations start as draft
        "publishedAt": None,
        "createdAt": now,
        "updatedAt": now,
    })
    await illustration_repo.insert(illust_dict)

    # Refresh dependent counters (mirrors legacy server.py behaviour).
    await theme_service.recalc_illustration_count(payload.themeId)
    await bundle_service.recalculate_named_bundle_counts()

    return illust_dict


async def update_illustration(illustration_id: str, payload) -> dict:
    """Apply a partial update by Pydantic payload and refresh counters."""
    current = await illustration_repo.find_raw(illustration_id)
    if not current:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    old_theme_id = current.get("themeId")
    new_theme_id = payload.themeId

    fields = payload.dict()
    fields["updatedAt"] = datetime.now(timezone.utc)
    await illustration_repo.update_fields(illustration_id, fields)

    if old_theme_id:
        await theme_service.recalc_illustration_count(old_theme_id)
    if new_theme_id and new_theme_id != old_theme_id:
        await theme_service.recalc_illustration_count(new_theme_id)
    await bundle_service.recalculate_named_bundle_counts()

    return {"success": True}


async def delete_illustration(illustration_id: str) -> dict:
    """Delete an illustration and refresh counters."""
    illust = await illustration_repo.find_raw(illustration_id)
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    await illustration_repo.delete(illustration_id)
    await theme_service.recalc_illustration_count(illust.get("themeId"))
    await bundle_service.recalculate_named_bundle_counts()

    return {"success": True}


async def toggle_publish(illustration_id: str) -> dict:
    """Flip the ``isPublished`` flag and set ``publishedAt`` on first publish."""
    illust = await illustration_repo.find_raw(illustration_id)
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    new_status = not illust.get("isPublished", False)
    now = datetime.now(timezone.utc)

    update_data: dict = {"isPublished": new_status, "updatedAt": now}
    if new_status and not illust.get("publishedAt"):
        update_data["publishedAt"] = now

    await illustration_repo.update_fields(illustration_id, update_data)

    return {
        "success": True,
        "isPublished": new_status,
        "publishedAt": update_data.get("publishedAt", illust.get("publishedAt")),
    }


async def toggle_download_enabled(illustration_id: str) -> dict:
    """Flip the ``downloadEnabled`` flag for an illustration."""
    illust = await illustration_repo.find_raw(illustration_id)
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    new_status = not illust.get("downloadEnabled", True)
    await illustration_repo.update_fields(
        illustration_id, {"downloadEnabled": new_status}
    )
    return {"success": True, "downloadEnabled": new_status}
