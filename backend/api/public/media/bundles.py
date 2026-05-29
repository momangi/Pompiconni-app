"""Public bundles media router (Fase 5/M1).

GridFS background image stream, legacy manual PDF download, and
auto-generated bundle PDF (with cache + rate limit). Logic preserved
verbatim from the legacy ``server.py``.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import io
import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from PIL import Image as PILImage
from PyPDF2 import PdfMerger
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from core.database import db, gridfs_bucket
from streaming import stream_gridfs_response


logger = logging.getLogger(__name__)

router = APIRouter()


# --- Internal helpers (private to this module) ------------------------------

def _calculate_bundle_hash(bundle: dict, illustrations: list) -> str:
    """Calculate hash for bundle PDF cache validation."""
    hash_data = {
        "illustrationIds": bundle.get("illustrationIds", []),
        "files": [],
    }
    for illust in illustrations:
        hash_data["files"].append({
            "id": illust.get("id"),
            "pdfFileId": illust.get("pdfFileId"),
            "imageFileId": illust.get("imageFileId"),
        })
    hash_string = str(sorted(hash_data.items()))
    return hashlib.md5(hash_string.encode()).hexdigest()


def _slugify_bundle_title(title: str) -> str:
    """Generate safe slug for bundle filename (mobile-friendly)."""
    slug = title.lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug if slug else "bundle"


def _generate_bundle_filename(title: str, page_count: int) -> str:
    """Generate clean filename: Poppiconni_Bundle-{slug}-{pages}p.pdf."""
    slug = _slugify_bundle_title(title)
    return f"Poppiconni_Bundle-{slug}-{page_count}p.pdf"


async def _check_free_bundle_rate_limit(ip: str, bundle_id: str, pdf_hash: str) -> bool:
    """Rate-limit free bundle downloads (max 2 per IP+bundle+hash)."""
    rate_limit_key = f"{ip}_{bundle_id}_{pdf_hash}"
    record = await db.download_limits.find_one({"key": rate_limit_key})

    if record:
        if record.get("count", 0) >= 2:
            logger.warning(f"Rate limit reached for {rate_limit_key}")
            return False
        await db.download_limits.update_one(
            {"key": rate_limit_key},
            {
                "$inc": {"count": 1},
                "$set": {
                    "lastDownload": datetime.now(timezone.utc),
                    "expiresAt": datetime.now(timezone.utc) + timedelta(days=30),
                },
            },
        )
    else:
        await db.download_limits.insert_one({
            "key": rate_limit_key,
            "ip": ip,
            "bundleId": bundle_id,
            "pdfHash": pdf_hash,
            "count": 1,
            "createdAt": datetime.now(timezone.utc),
            "lastDownload": datetime.now(timezone.utc),
            "expiresAt": datetime.now(timezone.utc) + timedelta(days=30),
        })
    return True


async def _generate_bundle_pdf(bundle: dict) -> bytes:
    """Generate a merged PDF from bundle illustrations."""
    from bson import ObjectId

    illustration_ids = bundle.get("illustrationIds", [])
    if not illustration_ids:
        raise HTTPException(
            status_code=400, detail="Bundle senza illustrazioni selezionate"
        )

    illustrations = []
    for illust_id in illustration_ids:
        illust = await db.illustrations.find_one({"id": illust_id}, {"_id": 0})
        if illust:
            illustrations.append(illust)

    if not illustrations:
        raise HTTPException(
            status_code=400, detail="Nessuna illustrazione trovata per questo bundle"
        )

    merger = PdfMerger()
    pages_added = 0

    for illust in illustrations:
        pdf_file_id = illust.get("pdfFileId")
        image_file_id = illust.get("imageFileId")

        try:
            if pdf_file_id:
                grid_out = await gridfs_bucket.open_download_stream(ObjectId(pdf_file_id))
                pdf_content = await grid_out.read()
                merger.append(io.BytesIO(pdf_content))
                pages_added += 1
                logger.info(f"Added PDF for illustration {illust.get('id')}")

            elif image_file_id:
                grid_out = await gridfs_bucket.open_download_stream(ObjectId(image_file_id))
                image_content = await grid_out.read()
                img = PILImage.open(io.BytesIO(image_content))
                img_width, img_height = img.size

                page_width, page_height = A4
                scale = min(page_width / img_width, page_height / img_height)
                scaled_width = img_width * scale
                scaled_height = img_height * scale

                pdf_buffer = io.BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                x = (page_width - scaled_width) / 2
                y = (page_height - scaled_height) / 2

                temp_img_buffer = io.BytesIO()
                img.save(temp_img_buffer, format="PNG")
                temp_img_buffer.seek(0)

                from reportlab.lib.utils import ImageReader
                img_reader = ImageReader(temp_img_buffer)
                c.drawImage(img_reader, x, y, scaled_width, scaled_height)
                c.showPage()
                c.save()

                pdf_buffer.seek(0)
                merger.append(pdf_buffer)
                pages_added += 1
                logger.info(f"Converted image to PDF for illustration {illust.get('id')}")

            else:
                logger.warning(
                    f"Illustration {illust.get('id')} has no PDF or image file, skipping"
                )

        except Exception as e:
            logger.error(f"Error processing illustration {illust.get('id')}: {str(e)}")
            continue

    if pages_added == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bundle senza file scaricabili. "
                "Nessuna illustrazione ha PDF o immagini caricate."
            ),
        )

    output_buffer = io.BytesIO()
    merger.write(output_buffer)
    merger.close()
    output_buffer.seek(0)

    logger.info(f"Generated bundle PDF with {pages_added} pages")
    return output_buffer.read()


# --- Routes -----------------------------------------------------------------

@router.get("/bundles/{bundle_id}/background-image")
async def get_bundle_background_image(bundle_id: str, request: Request):
    """Serve bundle background image (true streaming + ETag)."""
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle or not bundle.get("backgroundImageFileId"):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=bundle["backgroundImageFileId"],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )


@router.get("/bundles/{bundle_id}/download")
async def download_bundle_pdf_legacy(bundle_id: str, request: Request):
    """Download bundle PDF (legacy - manual upload)."""
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    if not bundle.get("pdfFileId"):
        raise HTTPException(status_code=404, detail="PDF non disponibile per questo bundle")

    safe_title = bundle.get("title", "bundle").replace(" ", "_")
    filename = f"Poppiconni_{safe_title}.pdf"
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=bundle["pdfFileId"],
        request=request,
        fallback_content_type="application/pdf",
        cache_control="no-cache",
        filename=filename,
        as_attachment=True,
        not_found_detail="PDF non disponibile per questo bundle",
    )


@router.get("/bundles/{bundle_id}/download-pdf")
async def download_bundle_generated_pdf(bundle_id: str, request: Request):
    """Download auto-generated bundle PDF (merged from illustrations)."""
    from bson import ObjectId

    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")

    # Access control for paid bundles
    if not bundle.get("isFree", False):
        raise HTTPException(
            status_code=403, detail="Acquisto richiesto. Pagamenti non ancora attivi."
        )

    illustration_ids = bundle.get("illustrationIds", [])
    if not illustration_ids:
        raise HTTPException(
            status_code=400, detail="Bundle senza illustrazioni. Contatta l'amministratore."
        )

    # Fetch illustrations to calculate hash
    illustrations = []
    for illust_id in illustration_ids:
        illust = await db.illustrations.find_one({"id": illust_id}, {"_id": 0})
        if illust:
            illustrations.append(illust)

    current_hash = _calculate_bundle_hash(bundle, illustrations)
    page_count = len(illustrations)

    # Client IP with proxy header support
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    # Rate limit (max 2 downloads per IP + bundle + hash)
    is_allowed = await _check_free_bundle_rate_limit(client_ip, bundle_id, current_hash)
    if not is_allowed:
        raise HTTPException(
            status_code=429, detail="Limite download gratuito raggiunto per questo bundle"
        )

    filename = _generate_bundle_filename(bundle.get("title", "bundle"), page_count)

    # Cache hit
    if (
        bundle.get("generatedPdfFileId")
        and bundle.get("generatedPdfHash") == current_hash
    ):
        logger.info(f"Serving cached PDF for bundle {bundle_id}")
        try:
            return await stream_gridfs_response(
                gridfs_bucket=gridfs_bucket,
                file_id=bundle["generatedPdfFileId"],
                request=request,
                fallback_content_type="application/pdf",
                cache_control="no-cache",
                filename=filename,
                as_attachment=True,
                not_found_detail="PDF cache non disponibile",
            )
        except Exception as e:
            logger.warning(f"Cache miss, regenerating PDF: {str(e)}")

    # Cache miss: generate, store, stream
    try:
        pdf_content = await _generate_bundle_pdf(bundle)

        if bundle.get("generatedPdfFileId"):
            try:
                await gridfs_bucket.delete(ObjectId(bundle["generatedPdfFileId"]))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(pdf_content),
            metadata={"bundle_id": bundle_id, "content_type": "application/pdf"},
        )

        await db.bundles.update_one(
            {"id": bundle_id},
            {"$set": {
                "generatedPdfFileId": str(file_id),
                "generatedPdfHash": current_hash,
                "updatedAt": datetime.now(timezone.utc),
            }},
        )

        logger.info(f"Generated and cached new PDF for bundle {bundle_id}")

        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating bundle PDF: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Errore nella generazione del PDF: {str(e)}"
        )
