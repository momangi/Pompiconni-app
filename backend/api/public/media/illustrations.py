"""Public illustrations media router (Fase 5/M1).

GridFS image stream + responsive variants, PDF download with event log,
and download/image status checks. Logic preserved verbatim.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException, Request

from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response, stream_gridfs_response_with_variants


router = APIRouter()


@router.post("/illustrations/{illustration_id}/download")
async def download_illustration(illustration_id: str, request: Request):
    """Real file download endpoint using GridFS.

    Returns the PDF file as a downloadable attachment. Only for published
    illustrations with download enabled. Logs a download_event row and
    increments the legacy counter (kept for backward compatibility; the
    canonical count is derived from ``download_events``).
    """
    illust = await db.illustrations.find_one(
        {"id": illustration_id, "isPublished": True}
    )
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    if not illust.get("downloadEnabled", True):
        raise HTTPException(
            status_code=403,
            detail="Download non disponibile per questa illustrazione",
        )

    pdf_file_id = illust.get("pdfFileId")
    if not pdf_file_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "File non ancora disponibile. "
                "L'amministratore deve prima caricare il PDF."
            ),
        )

    # Log download event + increment counter (before streaming so we count attempts)
    await db.download_events.insert_one({
        "id": str(uuid.uuid4()),
        "illustrationId": illustration_id,
        "bundleId": None,
        "downloadedAt": datetime.now(timezone.utc),
    })
    await db.illustrations.update_one(
        {"id": illustration_id},
        {"$inc": {"downloadCount": 1}},
    )

    raw_name = f"pompiconni_{illust.get('title') or illustration_id}.pdf"
    filename = raw_name.replace(" ", "_").replace('"', "").replace("'", "")

    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=pdf_file_id,
        request=request,
        fallback_content_type="application/pdf",
        cache_control="no-cache",
        filename=filename,
        as_attachment=True,
        not_found_detail="File non disponibile",
    )


@router.get("/illustrations/{illustration_id}/download-status")
async def get_download_status(illustration_id: str):
    """Check if a file is available for download - only for published illustrations."""
    illust = await db.illustrations.find_one(
        {"id": illustration_id, "isPublished": True}
    )
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    has_pdf = bool(illust.get("pdfFileId"))
    has_image = bool(illust.get("imageFileId"))
    return {
        "available": has_pdf,
        "hasImage": has_image,
        "message": "File disponibile" if has_pdf else "File non ancora disponibile",
    }


@router.get("/illustrations/{illustration_id}/image")
async def get_illustration_image(
    illustration_id: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve the illustration image from GridFS with streaming + ETag + variants."""
    illust = await db.illustrations.find_one(
        {"id": illustration_id, "isPublished": True}
    )
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    image_file_id = illust.get("imageFileId")
    if not image_file_id:
        raise HTTPException(status_code=404, detail="Immagine non ancora disponibile")

    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=image_file_id,
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type="image/jpeg",
        cache_control="public, max-age=31536000, immutable",
        not_found_detail="Immagine non ancora disponibile",
    )


@router.get("/illustrations/{illustration_id}/image-status")
async def get_image_status(illustration_id: str):
    """Check if an image is available - only for published illustrations."""
    illust = await db.illustrations.find_one(
        {"id": illustration_id, "isPublished": True}
    )
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    has_image = bool(illust.get("imageFileId"))
    return {
        "available": has_image,
        "imageUrl": (
            f"/api/illustrations/{illustration_id}/image" if has_image else None
        ),
        "message": (
            "Immagine disponibile"
            if has_image
            else "Immagine non ancora disponibile"
        ),
    }
