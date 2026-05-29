"""Admin generic-upload router (Fase 5/M3).

Single generic upload endpoint used by the Admin UI to store an arbitrary
image or PDF on GridFS, and (for images) also on the local
``UPLOAD_DIR`` so they can be served via the legacy ``/uploads/*`` static
mount.

Logic preserved verbatim from legacy ``server.py``. The ``UPLOAD_DIR``
path is resolved via ``core.config.settings.upload_dir`` (single source
of truth) — **not** imported from ``server.py`` to avoid circular
imports. The ``/uploads`` static mount remains registered in
``server.py``.
"""
from datetime import datetime, timezone
import io
import logging
from pathlib import Path
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from api.dependencies import verify_admin
from core.config import settings as core_settings
from core.database import db, gridfs_bucket  # noqa: F401  (db kept for parity with legacy module env)


logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR: Path = core_settings.upload_dir


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form("image"),
    email: str = Depends(verify_admin)
):
    """Upload file to GridFS for persistent storage"""
    # Validate file type
    allowed_extensions = {
        "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "pdf": [".pdf"]
    }

    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions.get(file_type, []):
        raise HTTPException(status_code=400, detail=f"Tipo file non permesso: {ext}")

    try:
        # Read file content
        content = await file.read()

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{ext}"

        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(content),
            metadata={
                "original_filename": file.filename,
                "file_type": file_type,
                "content_type": file.content_type,
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )

        # Also save to local uploads folder for image preview (images only)
        if file_type == "image":
            file_path = UPLOAD_DIR / unique_filename
            async with aiofiles.open(file_path, 'wb') as out_file:
                await out_file.write(content)

        # Return GridFS file ID and URL
        file_url = f"/uploads/{unique_filename}" if file_type == "image" else None

        return {
            "url": file_url,
            "filename": unique_filename,
            "fileId": str(file_id),
            "fileType": file_type
        }

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento del file")
