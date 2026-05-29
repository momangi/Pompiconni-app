"""Public themes media router (Fase 5/M1)."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response_with_variants


router = APIRouter()


@router.get("/themes/{theme_id}/background-image")
async def get_theme_background_image(
    theme_id: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve theme background image (streaming + ETag + responsive variants)."""
    theme = await db.themes.find_one({"id": theme_id})
    if not theme or not theme.get("backgroundImageFileId"):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=theme["backgroundImageFileId"],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )
