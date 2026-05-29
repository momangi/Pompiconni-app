"""Public posters media router (Fase 5/M2).

GridFS preview image stream with responsive variants, and PDF download
with download-enabled / paid / published guards. Logic preserved verbatim
from legacy ``server.py``.
"""
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response, stream_gridfs_response_with_variants


router = APIRouter()


@router.get("/posters/{poster_id}/image")
async def get_poster_image(
    poster_id: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve poster preview image (streaming + ETag + responsive variants)."""
    poster = await db.posters.find_one({"id": poster_id, "status": "published"})
    if not poster or not poster.get('imageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=poster['imageFileId'],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type="image/png",
        cache_control="public, max-age=31536000, immutable",
        not_found_detail="Immagine non trovata",
    )


@router.get("/posters/{poster_id}/download")
async def download_poster_pdf(poster_id: str, request: Request):
    """Download poster PDF (only if published, download enabled, and free or purchased)"""
    poster = await db.posters.find_one({"id": poster_id, "status": "published"})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")

    # Check if download is enabled
    if not poster.get('downloadEnabled', True):
        raise HTTPException(status_code=403, detail="Download non disponibile per questo poster")

    if not poster.get('pdfFileId'):
        raise HTTPException(status_code=404, detail="PDF non disponibile")

    # Check if poster is free
    if poster.get('price', 0) > 0:
        # TODO: Check if user has purchased this poster
        raise HTTPException(status_code=403, detail="Poster a pagamento - acquista per scaricare")

    # Increment download count
    await db.posters.update_one({"id": poster_id}, {"$inc": {"downloadCount": 1}})

    safe_title = re.sub(r'[^\w\s-]', '', poster.get('title', 'poster')).strip().replace(' ', '_')
    filename = f"Poppiconni_Poster_{safe_title}.pdf"

    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=poster['pdfFileId'],
        request=request,
        fallback_content_type="application/pdf",
        cache_control="no-cache",
        filename=filename,
        as_attachment=True,
        not_found_detail="PDF non disponibile",
    )
