"""Admin illustrations media router (Fase 5/M1).

PDF attach, image attach (with variant fire-and-forget), AI image
generation (Emergent LLM key), and theme re-assignment. Logic preserved
verbatim from legacy server.py.
"""
from datetime import datetime, timezone
import base64
import io
import logging
import os
from pathlib import Path
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket
from media_pipeline import ensure_variants
from models import GenerateRequest
from services import bundle_service, theme_service


logger = logging.getLogger(__name__)

router = APIRouter()


def _fire_variants(file_id) -> None:
    """Schedule responsive-variant generation. Best-effort."""
    import asyncio

    try:
        asyncio.create_task(ensure_variants(db, gridfs_bucket, file_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not schedule variants for {file_id}: {e}")


# --- Attach PDF -------------------------------------------------------------

@router.post("/illustrations/{illustration_id}/attach-pdf")
async def attach_pdf_to_illustration(
    illustration_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin),
):
    """Upload and attach a PDF file directly to an illustration."""
    from bson import ObjectId

    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Solo file PDF sono permessi")

    try:
        content = await file.read()
        safe_title = (
            illust.get("title", illustration_id)
            .replace(" ", "_")
            .replace('"', "")
            .replace("'", "")
        )
        unique_filename = f"pompiconni_{safe_title}.pdf"

        old_file_id = illust.get("pdfFileId")
        if old_file_id:
            try:
                await gridfs_bucket.delete(ObjectId(old_file_id))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(content),
            metadata={
                "illustration_id": illustration_id,
                "original_filename": file.filename,
                "file_type": "pdf",
                "content_type": "application/pdf",
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        await db.illustrations.update_one(
            {"id": illustration_id},
            {"$set": {
                "pdfFileId": str(file_id),
                "pdfUrl": f"/api/illustrations/{illustration_id}/download",
                "updatedAt": datetime.now(timezone.utc),
            }},
        )

        await theme_service.recalc_illustration_count(illust.get("themeId"))
        await bundle_service.recalculate_named_bundle_counts()

        return {
            "success": True,
            "fileId": str(file_id),
            "message": "PDF caricato e collegato all'illustrazione",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error attaching PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento del PDF")


# --- Attach image -----------------------------------------------------------

_IMAGE_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


@router.post("/illustrations/{illustration_id}/attach-image")
async def attach_image_to_illustration(
    illustration_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_admin),
):
    """Upload and attach an image file (jpg, jpeg, png) to an illustration."""
    from bson import ObjectId

    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    ext = Path(file.filename).suffix.lower()
    if ext not in _IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Solo file immagine sono permessi: {', '.join(_IMAGE_CONTENT_TYPES)}",
        )
    content_type = _IMAGE_CONTENT_TYPES[ext]

    try:
        content = await file.read()
        safe_title = (
            illust.get("title", illustration_id)
            .replace(" ", "_")
            .replace('"', "")
            .replace("'", "")
        )
        unique_filename = f"pompiconni_{safe_title}{ext}"

        old_file_id = illust.get("imageFileId")
        if old_file_id:
            try:
                await gridfs_bucket.delete(ObjectId(old_file_id))
            except Exception:
                pass

        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(content),
            metadata={
                "illustration_id": illustration_id,
                "original_filename": file.filename,
                "file_type": "image",
                "content_type": content_type,
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        await db.illustrations.update_one(
            {"id": illustration_id},
            {"$set": {
                "imageFileId": str(file_id),
                "imageUrl": f"/api/illustrations/{illustration_id}/image",
                "updatedAt": datetime.now(timezone.utc),
            }},
        )

        await theme_service.recalc_illustration_count(illust.get("themeId"))
        await bundle_service.recalculate_named_bundle_counts()

        _fire_variants(file_id)

        return {
            "success": True,
            "fileId": str(file_id),
            "imageUrl": f"/api/illustrations/{illustration_id}/image",
            "message": "Immagine caricata e collegata all'illustrazione",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error attaching image: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Errore durante il caricamento dell'immagine"
        )


# --- AI image generation ----------------------------------------------------

@router.post("/generate-illustration")
async def generate_illustration(request: GenerateRequest, email: str = Depends(verify_admin)):
    """Generate AI illustration and save to GridFS."""
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="API key non configurata")

        style_prompts = {
            "lineart": (
                "simple black and white line art coloring book page for children, "
                "thick clean outlines, no shading, no colors, white background, "
                "cute kawaii style"
            ),
            "sketch": (
                "pencil sketch style drawing, light lines, suitable for tracing, "
                "cute cartoon style"
            ),
            "colored": (
                "cute colorful illustration for children, soft pastel colors, "
                "kawaii style"
            ),
        }

        full_prompt = (
            "Poppiconni the cute clumsy unicorn with big eyes, rosy cheeks, "
            "rainbow horn, fluffy mane: "
            f"{request.prompt}. Style: "
            f"{style_prompts.get(request.style, style_prompts['lineart'])}"
        )

        logger.info(f"Generating image with prompt: {full_prompt[:100]}...")

        image_gen = OpenAIImageGeneration(api_key=api_key)
        images = await image_gen.generate_images(
            prompt=full_prompt,
            model="gpt-image-1",
            number_of_images=1,
        )

        if not images or len(images) == 0:
            raise HTTPException(status_code=500, detail="Nessuna immagine generata")

        illustration_id = str(uuid.uuid4())
        safe_prompt = (
            request.prompt[:30].replace(" ", "_").replace('"', "").replace("'", "")
        )
        unique_filename = f"ai_pompiconni_{safe_prompt}_{illustration_id[:8]}.png"

        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(images[0]),
            metadata={
                "illustration_id": illustration_id,
                "original_filename": unique_filename,
                "file_type": "image",
                "content_type": "image/png",
                "generated_by": "ai",
                "prompt": request.prompt,
                "style": request.style,
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        image_base64 = base64.b64encode(images[0]).decode("utf-8")

        illust_dict = {
            "id": illustration_id,
            "themeId": request.themeId if request.themeId else None,
            "title": f"Poppiconni - {request.prompt[:30]}",
            "description": request.prompt,
            "imageUrl": f"/api/illustrations/{illustration_id}/image",
            "imageFileId": str(file_id),
            "imageContentType": "image/png",
            "imageOriginalFilename": unique_filename,
            "pdfUrl": None,
            "pdfFileId": None,
            "isFree": True,
            "price": 0,
            "downloadCount": 0,
            "generatedByAI": True,
            "aiPrompt": request.prompt,
            "aiStyle": request.style,
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc),
        }
        await db.illustrations.insert_one(illust_dict)

        if request.themeId:
            await db.themes.update_one(
                {"id": request.themeId}, {"$inc": {"illustrationCount": 1}}
            )

        # R1 fix already applied here in legacy code: pop _id before returning.
        illust_dict.pop("_id", None)

        return {
            "success": True,
            "imageUrl": f"/api/illustrations/{illustration_id}/image",
            "imageBase64": image_base64,
            "illustration": illust_dict,
            "message": "Illustrazione generata e salvata con successo",
        }

    except ImportError:
        raise HTTPException(status_code=500, detail="Libreria AI non installata")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore generazione: {str(e)}")


# --- Theme re-assignment ----------------------------------------------------

@router.put("/illustrations/{illustration_id}/theme")
async def change_illustration_theme(
    illustration_id: str,
    theme_id: Optional[str] = None,
    email: str = Depends(verify_admin),
):
    """Change or remove theme assignment for an illustration."""
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    old_theme_id = illust.get("themeId")

    if theme_id:
        theme = await db.themes.find_one({"id": theme_id})
        if not theme:
            raise HTTPException(status_code=404, detail="Nuovo tema non trovato")

    await db.illustrations.update_one(
        {"id": illustration_id},
        {"$set": {"themeId": theme_id, "updatedAt": datetime.now(timezone.utc)}},
    )

    if old_theme_id:
        await db.themes.update_one(
            {"id": old_theme_id}, {"$inc": {"illustrationCount": -1}}
        )
    if theme_id:
        await db.themes.update_one(
            {"id": theme_id}, {"$inc": {"illustrationCount": 1}}
        )

    return {"success": True, "message": "Tema aggiornato"}
