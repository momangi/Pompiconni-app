"""Public games media router (Fase 5/M2).

GridFS image streams (thumbnail, card image, page image) with responsive
variants. Card/page-image endpoints return 204 No Content if missing or
on stream failure, preserving legacy behaviour verbatim.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response

from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response_with_variants


router = APIRouter()


@router.get("/games/{slug}/thumbnail")
async def get_game_thumbnail(
    slug: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Get game thumbnail image (streaming + ETag + responsive variants)."""
    game = await db.games.find_one({"slug": slug})
    if not game or not game.get('thumbnailFileId'):
        raise HTTPException(status_code=404, detail="Thumbnail non trovata")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=game['thumbnailFileId'],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Thumbnail non trovata",
    )


@router.get("/games/{slug}/card-image")
async def get_game_card_image(
    slug: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Get card image for a game. Returns 204 No Content if no image exists."""
    game = await db.games.find_one({"slug": slug})
    if not game or not game.get('cardImageFileId'):
        return Response(status_code=204)
    try:
        return await stream_gridfs_response_with_variants(
            db=db,
            gridfs_bucket=gridfs_bucket,
            original_file_id=game['cardImageFileId'],
            request=request,
            size_param=w,
            format_param=format,
            fallback_content_type="image/jpeg",
            cache_control="public, max-age=3600, must-revalidate",
            not_found_detail="Immagine non trovata",
        )
    except HTTPException:
        return Response(status_code=204)


@router.get("/games/{slug}/page-image")
async def get_game_page_image(
    slug: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Get page background image for a game. Returns 204 No Content if no image exists."""
    game = await db.games.find_one({"slug": slug})
    if not game or not game.get('pageImageFileId'):
        return Response(status_code=204)
    try:
        return await stream_gridfs_response_with_variants(
            db=db,
            gridfs_bucket=gridfs_bucket,
            original_file_id=game['pageImageFileId'],
            request=request,
            size_param=w,
            format_param=format,
            fallback_content_type="image/jpeg",
            cache_control="public, max-age=3600, must-revalidate",
            not_found_detail="Immagine non trovata",
        )
    except HTTPException:
        return Response(status_code=204)
