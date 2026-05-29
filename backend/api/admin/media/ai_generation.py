"""Admin AI-generation media router (Fase 5/M3).

Multi-AI Poppiconni pipeline endpoints:
- ``POST /generate-poppiconni``: runs the 4-phase pipeline (LLM → image
  gen → vision QC → post-prod), optionally saves to GridFS + illustration
  row, schedules an async retry on LOW_CONFIDENCE, and recalculates
  bundle counts. Calls ``bundle_service.recalculate_named_bundle_counts``
  directly to avoid importing the legacy wrapper from ``server.py``.
- ``GET /pipeline-status/{generation_id}``: status lookup by pipeline
  generation_id, used by the frontend to poll async retries.

Logic preserved verbatim from legacy ``server.py``. Pipeline internals
(``run_pipeline``, ``run_async_retry``, QC, retries, PDF/PNG generation)
are not modified.
"""
from datetime import datetime, timezone
import base64
import io
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.dependencies import verify_admin
from core.database import db, gridfs_bucket
from image_pipeline import (
    PipelineStatus,
    QCResult,
    run_async_retry,
    run_pipeline,
)
from models import PoppiconniGenerateRequest, PoppiconniGenerateResponse
from services import bundle_service


logger = logging.getLogger(__name__)

router = APIRouter()


async def _resolve_reference_image_base64(request: PoppiconniGenerateRequest, email: str):
    """Resolve the reference image (priority: direct upload > style library).

    Returns the base64-encoded reference image, or ``None`` if no
    reference image is available. Failures while loading the style
    library are logged and swallowed, identical to the legacy behaviour.
    """
    from bson import ObjectId

    # 1. First check if direct reference image was uploaded
    if request.reference_image_base64:
        logger.info("Using directly uploaded reference image for style analysis")
        return request.reference_image_base64

    # 2. Otherwise, check style library
    if request.style_id:
        style = await db.generation_styles.find_one({"id": request.style_id, "userId": email})
        if style and style.get('referenceImageFileId'):
            try:
                grid_out = await gridfs_bucket.open_download_stream(
                    ObjectId(style['referenceImageFileId'])
                )
                content = await grid_out.read()
                ref_b64 = base64.b64encode(content).decode('utf-8')
                logger.info(f"Using reference image from style library: {style.get('styleName')}")
                return ref_b64
            except Exception as e:
                logger.warning(f"Could not load reference image from style: {e}")

    return None


async def _persist_pipeline_result(result, request: PoppiconniGenerateRequest):
    """Persist pipeline outputs to GridFS + illustrations + theme/bundle counts.

    Returns the generated illustration_id, or ``None`` if persistence is
    skipped (no PNG bytes or ``save_to_gallery=False``). Side effects are
    identical to the legacy implementation.
    """
    if not (request.save_to_gallery and result.final_png_bytes):
        return None

    illustration_id = str(uuid.uuid4())

    # Save final PNG to GridFS
    png_file_id = await gridfs_bucket.upload_from_stream(
        f"poppiconni_{illustration_id}.png",
        io.BytesIO(result.final_png_bytes),
        metadata={
            "illustration_id": illustration_id,
            "type": "final_png",
            "content_type": "image/png",
            "dpi": 300,
            "generated_by": "multi_ai_pipeline",
            "generation_id": result.generation_id
        }
    )

    # Save PDF to GridFS (optional)
    pdf_file_id = None
    if result.final_pdf_bytes:
        pdf_file_id = await gridfs_bucket.upload_from_stream(
            f"poppiconni_{illustration_id}.pdf",
            io.BytesIO(result.final_pdf_bytes),
            metadata={
                "illustration_id": illustration_id,
                "type": "final_pdf",
                "content_type": "application/pdf"
            }
        )

    # Create illustration record
    illust_dict = {
        'id': illustration_id,
        'themeId': request.theme_id,
        'title': f"Poppiconni - {request.user_request[:50]}",
        'description': request.user_request,
        'imageUrl': f"/api/illustrations/{illustration_id}/image",
        'imageFileId': str(png_file_id),
        'imageContentType': "image/png",
        'pdfUrl': f"/api/illustrations/{illustration_id}/download" if pdf_file_id else None,
        'pdfFileId': str(pdf_file_id) if pdf_file_id else None,
        'isFree': True,
        'price': 0,
        'downloadCount': 0,
        'generatedByAI': True,
        'aiPrompt': result.optimized_prompt,
        'aiStyle': "multi_ai_pipeline",
        'pipelineGenerationId': result.generation_id,
        'pipelineStatus': result.status.value,
        'qcPassed': result.qc_report.result == QCResult.PASS if result.qc_report else False,
        'qcConfidenceScore': result.qc_report.confidence_score if result.qc_report else 0,
        'createdAt': datetime.now(timezone.utc),
        'updatedAt': datetime.now(timezone.utc)
    }
    await db.illustrations.insert_one(illust_dict)

    # Update theme count if theme provided
    if request.theme_id:
        await db.themes.update_one(
            {"id": request.theme_id},
            {"$inc": {"illustrationCount": 1}}
        )

    # Update bundle counts automatically
    await bundle_service.recalculate_named_bundle_counts()

    return illustration_id


@router.post("/generate-poppiconni", response_model=PoppiconniGenerateResponse)
async def generate_poppiconni_illustration(
    request: PoppiconniGenerateRequest,
    background_tasks: BackgroundTasks,
    email: str = Depends(verify_admin)
):
    """
    Avvia la pipeline Multi-AI per generare un'illustrazione Poppiconni on-brand.

    Pipeline a 4 fasi:
    1. LLM (GPT-4o): Interpreta richiesta → genera prompt ottimizzato
    2. Image Gen (gpt-image-1): Genera immagine candidata
    3. Vision/OCR (GPT-4o): Quality Check automatico
    4. Post-Produzione (Pillow): Export finale (PNG 300DPI, PDF, thumbnail)

    Retry automatico: max 5 tentativi sincroni.
    Se fallisce, salva come LOW_CONFIDENCE e avvia retry asincrono.
    """
    # Get reference image - prioritize direct upload, then style library
    reference_image_base64 = await _resolve_reference_image_base64(request, email)

    # Run the pipeline with reference image for style analysis
    try:
        result = await run_pipeline(
            user_request=request.user_request,
            reference_image_base64=reference_image_base64,
            style_lock=request.style_lock or bool(reference_image_base64),  # Auto-enable style lock if image provided
            user_id=email
        )

        # Save to gallery if requested and pipeline succeeded
        illustration_id = await _persist_pipeline_result(result, request)

        # If LOW_CONFIDENCE, schedule async retry
        if result.status == PipelineStatus.LOW_CONFIDENCE:
            background_tasks.add_task(
                run_async_retry,
                generation_id=result.generation_id,
                user_request=request.user_request,
                original_prompt=result.optimized_prompt or request.user_request,
                reference_image_base64=reference_image_base64,
                style_lock=request.style_lock,
                db=db,
                gridfs_bucket=gridfs_bucket
            )

        # Prepare response
        thumbnail_b64 = None
        if result.thumbnail_bytes:
            thumbnail_b64 = base64.b64encode(result.thumbnail_bytes).decode('utf-8')

        qc_passed = result.qc_report.result == QCResult.PASS if result.qc_report else False
        confidence = result.qc_report.confidence_score if result.qc_report else 0.0
        issues = result.qc_report.issues if result.qc_report else []

        status_messages = {
            PipelineStatus.COMPLETED: "Illustrazione generata con successo! QC superato.",
            PipelineStatus.LOW_CONFIDENCE: "Illustrazione generata ma QC non completamente superato. Retry asincrono avviato.",
            PipelineStatus.FAILED: f"Generazione fallita: {result.error_message}"
        }

        return PoppiconniGenerateResponse(
            success=result.status in [PipelineStatus.COMPLETED, PipelineStatus.LOW_CONFIDENCE],
            generation_id=result.generation_id,
            status=result.status.value,
            optimized_prompt=result.optimized_prompt,
            qc_passed=qc_passed,
            confidence_score=confidence,
            qc_issues=issues,
            has_final_image=result.final_png_bytes is not None,
            thumbnail_base64=thumbnail_b64,
            illustration_id=illustration_id,
            message=status_messages.get(result.status, "Pipeline completata"),
            retry_count=result.retry_count
        )

    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Errore pipeline: {str(e)}")


@router.get("/pipeline-status/{generation_id}")
async def get_pipeline_status(generation_id: str, email: str = Depends(verify_admin)):
    """Check status of a pipeline generation (for async retries)"""
    # Check if there's an illustration with this generation_id
    illust = await db.illustrations.find_one(
        {"pipelineGenerationId": generation_id},
        {"_id": 0}
    )

    if illust:
        return {
            "found": True,
            "status": illust.get('pipelineStatus', 'unknown'),
            "qc_passed": illust.get('qcPassed', False),
            "confidence_score": illust.get('qcConfidenceScore', 0),
            "illustration_id": illust.get('id')
        }

    return {
        "found": False,
        "status": "pending_or_not_found",
        "message": "Generazione in corso o non trovata"
    }
