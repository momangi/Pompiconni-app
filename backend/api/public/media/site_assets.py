"""Public site-assets media router (Fase 5/M3).

Hero image + brand logo: GridFS streaming with responsive variants, and
hero status endpoint. Logic preserved verbatim from legacy ``server.py``.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response_with_variants


router = APIRouter()


@router.get("/site/hero-image")
async def get_hero_image(
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve hero image (streaming + ETag + responsive variants)."""
    settings = await db.site_settings.find_one({"id": "global"})
    if not settings or not settings.get('heroImageFileId'):
        raise HTTPException(status_code=404, detail="Hero image non configurata")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=settings['heroImageFileId'],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type=settings.get('heroImageContentType', 'image/png'),
        cache_control="public, max-age=3600",
        not_found_detail="Hero image non trovata",
    )


@router.get("/site/hero-status")
async def get_hero_status():
    """Check if hero image is configured"""
    settings = await db.site_settings.find_one({"id": "global"})
    has_hero = bool(settings and settings.get('heroImageFileId'))
    return {
        "hasHeroImage": has_hero,
        "heroImageUrl": "/api/site/hero-image" if has_hero else None,
        "updatedAt": settings.get('heroImageUpdatedAt') if settings else None
    }


@router.get("/site/brand-logo")
async def get_brand_logo(
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve brand logo image (streaming + ETag + responsive variants)."""
    settings = await db.site_settings.find_one({"id": "global"})
    if not settings or not settings.get('brandLogoFileId'):
        raise HTTPException(status_code=404, detail="Brand logo non configurato")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=settings['brandLogoFileId'],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type=settings.get('brandLogoContentType', 'image/png'),
        cache_control="public, max-age=3600",
        not_found_detail="Brand logo non trovato",
    )
