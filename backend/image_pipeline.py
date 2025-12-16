"""
Poppiconni Multi-AI Image Generation Pipeline
==============================================
Pipeline automatica a 4 fasi per generare illustrazioni on-brand per libri da colorare.

Fasi:
1. LLM (GPT-4o): Interpreta richiesta utente → genera prompt ottimizzato
2. Image Gen (gpt-image-1): Genera immagine candidata
3. Vision/OCR (GPT-4o): Quality Check automatico (conformità brand)
4. Post-Produzione (Pillow): Pulizia, normalizzazione, export (PNG 300DPI, PDF, thumbnail)
"""

import os
import io
import uuid
import base64
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from enum import Enum
from dataclasses import dataclass, field
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ============== CONFIGURAZIONE (NON HARDCODED) ==============

# Limite reference images per utente - CONFIGURABILE
MAX_REFERENCE_IMAGES_PER_USER = int(os.environ.get('MAX_REFERENCE_IMAGES_PER_USER', '20'))

# Tentativi retry
MAX_SYNC_RETRIES = int(os.environ.get('MAX_SYNC_RETRIES', '5'))
MAX_ASYNC_RETRIES = int(os.environ.get('MAX_ASYNC_RETRIES', '5'))

# Output DPI per stampa
OUTPUT_DPI = 300
THUMBNAIL_SIZE = (400, 400)

# ============== BRAND RULES (SEMPRE ATTIVE) ==============

BRAND_RULES = """
REGOLE DEL MARCHIO POPPICONNI (OBBLIGATORIE):

1. STILE VISIVO:
   - Disegno per bambini, line-art pulita
   - Linee spesse e chiare (thick outlines)
   - NESSUNA ombreggiatura realistica
   - Sfondo bianco pulito
   - Stile kawaii/cute adatto alla colorazione

2. ELEMENTO OBBLIGATORIO - BARATTOLO DI POPCORN:
   - Deve SEMPRE essere presente un barattolo/secchiello di popcorn
   - La scritta "POPPICONNI" deve essere:
     * Chiaramente LEGGIBILE
     * FRONTALE (non curva, non distorta)
     * In MAIUSCOLO
     * Ad ALTO CONTRASTO (nero su bianco o bianco su rosso)
   - Il barattolo deve essere visibile e non nascosto

3. CONTENUTI VIETATI:
   - Nessun contenuto violento
   - Nessun contenuto per adulti
   - Nessun contenuto spaventoso
   - Composizione semplice adatta ai bambini

4. COMPOSIZIONE:
   - Aree ampie per colorare
   - Dettagli non troppo piccoli
   - Personaggio principale ben visibile
   - Spazi bianchi equilibrati
"""

POPPICONNI_CHARACTER_DESCRIPTION = """
POPPICONNI - Descrizione del Personaggio:
- Unicorno tenero e goffo
- Occhi grandi ed espressivi
- Guance rosee
- Corno arcobaleno
- Criniera fluffy e morbida
- Espressione dolce e simpatica
- Postura giocosa e amichevole
"""

# ============== ENUMS E DATACLASSES ==============

class PipelineStatus(str, Enum):
    PENDING = "pending"
    PHASE1_PROMPT = "phase1_prompt"
    PHASE2_GENERATION = "phase2_generation"
    PHASE3_QC = "phase3_qc"
    PHASE4_POSTPROD = "phase4_postprod"
    COMPLETED = "completed"
    LOW_CONFIDENCE = "low_confidence"
    FAILED = "failed"
    ASYNC_RETRY = "async_retry"

class QCResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"

@dataclass
class QCReport:
    """Report del Quality Check (Fase 3)"""
    result: QCResult
    popcorn_bucket_present: bool = False
    poppiconni_text_readable: bool = False
    lineart_style_ok: bool = False
    colorability_ok: bool = False
    no_forbidden_content: bool = True
    confidence_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    prompt_patch: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "popcorn_bucket_present": self.popcorn_bucket_present,
            "poppiconni_text_readable": self.poppiconni_text_readable,
            "lineart_style_ok": self.lineart_style_ok,
            "colorability_ok": self.colorability_ok,
            "no_forbidden_content": self.no_forbidden_content,
            "confidence_score": self.confidence_score,
            "issues": self.issues,
            "prompt_patch": self.prompt_patch
        }

@dataclass
class PipelineResult:
    """Risultato finale della pipeline"""
    status: PipelineStatus
    generation_id: str
    user_request: str
    optimized_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_spec: Optional[str] = None
    candidate_image_base64: Optional[str] = None
    qc_report: Optional[QCReport] = None
    final_png_bytes: Optional[bytes] = None
    final_pdf_bytes: Optional[bytes] = None
    thumbnail_bytes: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "generation_id": self.generation_id,
            "user_request": self.user_request,
            "optimized_prompt": self.optimized_prompt,
            "negative_prompt": self.negative_prompt,
            "style_spec": self.style_spec,
            "has_candidate_image": self.candidate_image_base64 is not None,
            "qc_report": self.qc_report.to_dict() if self.qc_report else None,
            "has_final_png": self.final_png_bytes is not None,
            "has_final_pdf": self.final_pdf_bytes is not None,
            "has_thumbnail": self.thumbnail_bytes is not None,
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "error_message": self.error_message
        }

# ============== FASE 1: LLM PROMPT ENGINEERING ==============

async def phase1_prompt_engineering(
    user_request: str,
    reference_image_base64: Optional[str] = None,
    style_lock: bool = False
) -> Tuple[str, str, Optional[str]]:
    """
    Fase 1: Usa GPT-4o per interpretare la richiesta utente e generare prompt ottimizzati.
    
    Returns:
        Tuple[generation_prompt, negative_prompt, style_spec]
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise ValueError("EMERGENT_LLM_KEY non configurata")
    
    session_id = f"poppiconni_phase1_{uuid.uuid4()}"
    
    system_message = f"""Sei un esperto di prompt engineering per generazione di immagini AI.
Il tuo compito è creare prompt ottimizzati per gpt-image-1 che rispettino RIGOROSAMENTE le regole del brand Poppiconni.

{BRAND_RULES}

{POPPICONNI_CHARACTER_DESCRIPTION}

ISTRUZIONI:
1. Analizza la richiesta dell'utente
2. Genera un prompt dettagliato che includa TUTTI gli elementi obbligatori del brand
3. Il barattolo di popcorn con scritta "POPPICONNI" deve essere ESPLICITAMENTE richiesto
4. Specifica sempre lo stile line-art per libro da colorare

FORMATO OUTPUT (JSON):
{{
  "generation_prompt": "prompt completo per generare l'immagine",
  "negative_prompt": "elementi da evitare",
  "style_spec": "specifica dello stile estratta da immagine di riferimento (se presente)"
}}
"""
    
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=system_message
    )
    chat = chat.with_model("openai", "gpt-4o")
    
    # Costruisci il messaggio
    user_text = f"""Richiesta utente: {user_request}

Genera i prompt ottimizzati per creare un'illustrazione da libro da colorare con Poppiconni.
RICORDA: Il barattolo di popcorn con scritta "POPPICONNI" è OBBLIGATORIO.
"""
    
    file_contents = []
    if reference_image_base64:
        user_text += """

⚠️ IMPORTANTE: È presente un'IMMAGINE DI RIFERIMENTO (prototipo).
DEVI analizzare attentamente questa immagine e nel tuo prompt includere:

1. ANALISI DELLO STILE dell'immagine di riferimento:
   - Tipo di tratti (spessi/sottili, uniformi/variabili)
   - Stile delle linee (curve morbide, angoli netti, etc.)
   - Livello di dettaglio
   - Proporzioni del personaggio
   - Stile degli occhi, espressioni, pose

2. Nel "generation_prompt" DEVI specificare di replicare esattamente:
   - Lo stesso spessore delle linee
   - Lo stesso stile di tratto
   - Le stesse proporzioni del personaggio
   - Lo stesso livello di dettaglio
   - Lo stesso stile kawaii/cartoon se presente

3. Nel "style_spec" descrivi in dettaglio lo stile estratto dall'immagine.

L'obiettivo è che l'immagine generata sembri disegnata dalla STESSA MANO dell'immagine di riferimento.
"""
        file_contents.append(ImageContent(image_base64=reference_image_base64))
    
    message = UserMessage(text=user_text, file_contents=file_contents if file_contents else None)
    
    response = await chat.send_message(message)
    
    # Parse JSON response
    import json
    try:
        # Cerca il JSON nella risposta
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            data = json.loads(json_str)
            return (
                data.get("generation_prompt", ""),
                data.get("negative_prompt", ""),
                data.get("style_spec")
            )
    except json.JSONDecodeError:
        logger.warning(f"Impossibile parsare JSON da risposta LLM: {response[:200]}")
    
    # Fallback: usa la risposta come prompt
    return (response, "realistic shading, scary elements, adult content, violence", None)

# ============== FASE 2: IMAGE GENERATION ==============

async def phase2_image_generation(
    generation_prompt: str,
    reference_image_base64: Optional[str] = None,
    style_lock: bool = False
) -> bytes:
    """
    Fase 2: Genera l'immagine candidata usando gpt-image-1.
    
    Returns:
        bytes dell'immagine generata (PNG)
    """
    from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise ValueError("EMERGENT_LLM_KEY non configurata")
    
    # Aggiungi sempre le specifiche di stile al prompt
    full_prompt = f"""{generation_prompt}

STILE OBBLIGATORIO:
- Simple black and white line art
- Coloring book page for children
- Thick clean outlines
- No shading, no colors
- White background
- Cute kawaii style
- A popcorn bucket with text "POPPICONNI" clearly visible and readable
"""
    
    logger.info(f"Fase 2 - Generazione immagine con prompt: {full_prompt[:150]}...")
    
    image_gen = OpenAIImageGeneration(api_key=api_key)
    
    images = await image_gen.generate_images(
        prompt=full_prompt,
        model="gpt-image-1",
        number_of_images=1
    )
    
    if not images or len(images) == 0:
        raise ValueError("Nessuna immagine generata da gpt-image-1")
    
    return images[0]

# ============== FASE 3: QUALITY CHECK (VISION + OCR) ==============

async def phase3_quality_check(
    image_bytes: bytes,
    original_prompt: str
) -> QCReport:
    """
    Fase 3: Esegue Quality Check automatico sull'immagine candidata.
    Usa GPT-4o Vision per analizzare l'immagine e verificare la conformità al brand.
    
    Returns:
        QCReport con risultati dettagliati
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise ValueError("EMERGENT_LLM_KEY non configurata")
    
    session_id = f"poppiconni_qc_{uuid.uuid4()}"
    
    system_message = f"""Sei un ispettore di qualità per le illustrazioni del brand Poppiconni.
Il tuo compito è verificare che l'immagine rispetti TUTTE le regole del brand.

{BRAND_RULES}

ISTRUZIONI DI VERIFICA:
1. Verifica presenza del barattolo di popcorn
2. Verifica che la scritta "POPPICONNI" sia LEGGIBILE (usa OCR mentale)
3. Verifica che lo stile sia line-art adatto alla colorazione
4. Verifica assenza di contenuti vietati
5. Valuta la "colorabilità" (aree ampie, linee chiare)

FORMATO OUTPUT (JSON):
{{
  "popcorn_bucket_present": true/false,
  "poppiconni_text_readable": true/false,
  "poppiconni_text_found": "testo effettivamente letto (se presente)",
  "lineart_style_ok": true/false,
  "colorability_ok": true/false,
  "no_forbidden_content": true/false,
  "confidence_score": 0.0-1.0,
  "issues": ["lista di problemi riscontrati"],
  "prompt_patch": "suggerimento per migliorare il prompt (se fallisce)"
}}
"""
    
    chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=system_message
    )
    chat = chat.with_model("openai", "gpt-4o")
    
    # Converti immagine in base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    message = UserMessage(
        text=f"""Analizza questa immagine generata per il brand Poppiconni.

Prompt originale usato: {original_prompt}

Esegui il Quality Check completo e restituisci il report in formato JSON.
IMPORTANTE: Verifica ATTENTAMENTE che la scritta "POPPICONNI" sia presente e LEGGIBILE.
""",
        file_contents=[ImageContent(image_base64=image_base64)]
    )
    
    response = await chat.send_message(message)
    
    # Parse JSON response
    import json
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            data = json.loads(json_str)
            
            # Calcola il risultato
            checks = [
                data.get("popcorn_bucket_present", False),
                data.get("poppiconni_text_readable", False),
                data.get("lineart_style_ok", False),
                data.get("colorability_ok", False),
                data.get("no_forbidden_content", True)
            ]
            
            passed = sum(checks)
            if passed == 5:
                result = QCResult.PASS
            elif passed >= 3:
                result = QCResult.PARTIAL
            else:
                result = QCResult.FAIL
            
            return QCReport(
                result=result,
                popcorn_bucket_present=data.get("popcorn_bucket_present", False),
                poppiconni_text_readable=data.get("poppiconni_text_readable", False),
                lineart_style_ok=data.get("lineart_style_ok", False),
                colorability_ok=data.get("colorability_ok", False),
                no_forbidden_content=data.get("no_forbidden_content", True),
                confidence_score=data.get("confidence_score", 0.0),
                issues=data.get("issues", []),
                prompt_patch=data.get("prompt_patch")
            )
    except json.JSONDecodeError:
        logger.warning(f"Impossibile parsare JSON da risposta QC: {response[:200]}")
    
    # Fallback: QC fallito
    return QCReport(
        result=QCResult.FAIL,
        issues=["Impossibile eseguire il Quality Check automatico"],
        prompt_patch="Riprova con un prompt più specifico per il barattolo di popcorn POPPICONNI"
    )

# ============== FASE 4: POST-PRODUZIONE ==============

def phase4_postproduction(
    image_bytes: bytes,
    generation_id: str,
    metadata: Dict[str, Any]
) -> Tuple[bytes, bytes, bytes, Dict[str, Any]]:
    """
    Fase 4: Post-produzione dell'immagine approvata.
    - Pulizia e normalizzazione
    - Export PNG 300 DPI
    - Export PDF pronto per stampa
    - Generazione thumbnail
    
    Returns:
        Tuple[final_png_bytes, final_pdf_bytes, thumbnail_bytes, updated_metadata]
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    
    # Apri l'immagine con Pillow
    img = Image.open(io.BytesIO(image_bytes))
    
    # Converti in RGB se necessario (rimuovi alpha)
    if img.mode in ('RGBA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 1. PULIZIA E NORMALIZZAZIONE
    # Migliora il contrasto per line-art
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    
    # Aumenta leggermente la nitidezza
    img = img.filter(ImageFilter.SHARPEN)
    
    # Auto-contrasto per normalizzare i livelli
    img = ImageOps.autocontrast(img, cutoff=0.5)
    
    # 2. EXPORT PNG 300 DPI
    png_buffer = io.BytesIO()
    # Calcola la dimensione per 300 DPI (assumendo output A4-ish)
    # A4 = 210x297mm = 8.27x11.69 inch → a 300 DPI = 2480x3508 pixel
    target_width = 2480
    target_height = 3508
    
    # Ridimensiona mantenendo aspect ratio
    img_ratio = img.width / img.height
    target_ratio = target_width / target_height
    
    if img_ratio > target_ratio:
        new_width = target_width
        new_height = int(target_width / img_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * img_ratio)
    
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Salva PNG con DPI info
    img_resized.save(png_buffer, format='PNG', dpi=(OUTPUT_DPI, OUTPUT_DPI))
    final_png_bytes = png_buffer.getvalue()
    
    # 3. EXPORT PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    
    # Centra l'immagine sulla pagina A4
    a4_width, a4_height = A4
    img_reader = ImageReader(io.BytesIO(final_png_bytes))
    
    # Calcola dimensioni per adattare all'A4 con margini
    margin = 36  # 0.5 inch
    available_width = a4_width - 2 * margin
    available_height = a4_height - 2 * margin
    
    img_aspect = new_width / new_height
    available_aspect = available_width / available_height
    
    if img_aspect > available_aspect:
        draw_width = available_width
        draw_height = available_width / img_aspect
    else:
        draw_height = available_height
        draw_width = available_height * img_aspect
    
    x = (a4_width - draw_width) / 2
    y = (a4_height - draw_height) / 2
    
    c.drawImage(img_reader, x, y, draw_width, draw_height)
    
    # Aggiungi copyright footer
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(a4_width / 2, 20, "© Poppiconni - Tutti i diritti riservati - Solo per uso personale")
    
    c.save()
    final_pdf_bytes = pdf_buffer.getvalue()
    
    # 4. GENERA THUMBNAIL
    thumbnail = img.copy()
    thumbnail.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    thumb_buffer = io.BytesIO()
    thumbnail.save(thumb_buffer, format='PNG', optimize=True)
    thumbnail_bytes = thumb_buffer.getvalue()
    
    # 5. AGGIORNA METADATA
    updated_metadata = {
        **metadata,
        "final_png_width": new_width,
        "final_png_height": new_height,
        "final_png_dpi": OUTPUT_DPI,
        "final_png_size_bytes": len(final_png_bytes),
        "final_pdf_size_bytes": len(final_pdf_bytes),
        "thumbnail_width": thumbnail.width,
        "thumbnail_height": thumbnail.height,
        "processed_at": datetime.now(timezone.utc).isoformat()
    }
    
    return final_png_bytes, final_pdf_bytes, thumbnail_bytes, updated_metadata

# ============== ORCHESTRATORE PIPELINE ==============

async def run_pipeline(
    user_request: str,
    reference_image_base64: Optional[str] = None,
    style_lock: bool = False,
    user_id: str = "admin"
) -> PipelineResult:
    """
    Orchestratore principale della pipeline Multi-AI.
    Esegue le 4 fasi in sequenza con retry automatico.
    
    Args:
        user_request: Richiesta dell'utente in linguaggio naturale
        reference_image_base64: Immagine di riferimento (opzionale)
        style_lock: Se True, usa l'immagine di riferimento come guida di stile
        user_id: ID dell'utente per tracciamento
    
    Returns:
        PipelineResult con tutti i risultati della pipeline
    """
    generation_id = str(uuid.uuid4())
    result = PipelineResult(
        status=PipelineStatus.PENDING,
        generation_id=generation_id,
        user_request=user_request,
        metadata={
            "user_id": user_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "has_reference": reference_image_base64 is not None,
            "style_lock": style_lock
        }
    )
    
    current_prompt = None
    best_candidate = None
    best_qc_score = 0.0
    
    try:
        # ===== FASE 1: PROMPT ENGINEERING =====
        logger.info(f"[{generation_id}] Avvio Fase 1 - Prompt Engineering")
        result.status = PipelineStatus.PHASE1_PROMPT
        
        generation_prompt, negative_prompt, style_spec = await phase1_prompt_engineering(
            user_request=user_request,
            reference_image_base64=reference_image_base64,
            style_lock=style_lock
        )
        
        result.optimized_prompt = generation_prompt
        result.negative_prompt = negative_prompt
        result.style_spec = style_spec
        current_prompt = generation_prompt
        
        logger.info(f"[{generation_id}] Fase 1 completata. Prompt: {generation_prompt[:100]}...")
        
        # ===== LOOP SINCRONO: FASE 2-3 =====
        for attempt in range(MAX_SYNC_RETRIES):
            result.retry_count = attempt + 1
            logger.info(f"[{generation_id}] Tentativo {attempt + 1}/{MAX_SYNC_RETRIES}")
            
            # ===== FASE 2: IMAGE GENERATION =====
            result.status = PipelineStatus.PHASE2_GENERATION
            logger.info(f"[{generation_id}] Avvio Fase 2 - Generazione Immagine")
            
            image_bytes = await phase2_image_generation(
                generation_prompt=current_prompt,
                reference_image_base64=reference_image_base64,
                style_lock=style_lock
            )
            
            result.candidate_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"[{generation_id}] Fase 2 completata. Immagine generata ({len(image_bytes)} bytes)")
            
            # ===== FASE 3: QUALITY CHECK =====
            result.status = PipelineStatus.PHASE3_QC
            logger.info(f"[{generation_id}] Avvio Fase 3 - Quality Check")
            
            qc_report = await phase3_quality_check(
                image_bytes=image_bytes,
                original_prompt=current_prompt
            )
            
            result.qc_report = qc_report
            logger.info(f"[{generation_id}] Fase 3 completata. Risultato: {qc_report.result.value}, Score: {qc_report.confidence_score}")
            
            # Salva il miglior candidato
            if qc_report.confidence_score > best_qc_score:
                best_qc_score = qc_report.confidence_score
                best_candidate = image_bytes
            
            # Se QC passa, procedi a Fase 4
            if qc_report.result == QCResult.PASS:
                logger.info(f"[{generation_id}] QC PASSATO! Procedo a Fase 4")
                break
            
            # Se QC fallisce e abbiamo altri tentativi, applica patch
            if attempt < MAX_SYNC_RETRIES - 1 and qc_report.prompt_patch:
                current_prompt = f"{generation_prompt}\n\nCORREZIONI RICHIESTE: {qc_report.prompt_patch}"
                logger.info(f"[{generation_id}] QC fallito. Applico patch: {qc_report.prompt_patch[:100]}...")
        
        # ===== GESTIONE POST-RETRY =====
        if result.qc_report and result.qc_report.result != QCResult.PASS:
            # QC fallito dopo tutti i tentativi
            logger.warning(f"[{generation_id}] QC fallito dopo {MAX_SYNC_RETRIES} tentativi. Salvo come LOW_CONFIDENCE")
            result.status = PipelineStatus.LOW_CONFIDENCE
            
            # Usa il miglior candidato per la post-produzione comunque
            if best_candidate:
                result.candidate_image_base64 = base64.b64encode(best_candidate).decode('utf-8')
                image_bytes = best_candidate
            
            result.metadata["low_confidence_reason"] = result.qc_report.issues
            result.metadata["best_qc_score"] = best_qc_score
        
        # ===== FASE 4: POST-PRODUZIONE =====
        result.status = PipelineStatus.PHASE4_POSTPROD
        logger.info(f"[{generation_id}] Avvio Fase 4 - Post-Produzione")
        
        final_png, final_pdf, thumbnail, updated_metadata = phase4_postproduction(
            image_bytes=image_bytes,
            generation_id=generation_id,
            metadata=result.metadata
        )
        
        result.final_png_bytes = final_png
        result.final_pdf_bytes = final_pdf
        result.thumbnail_bytes = thumbnail
        result.metadata = updated_metadata
        
        logger.info(f"[{generation_id}] Fase 4 completata. PNG: {len(final_png)} bytes, PDF: {len(final_pdf)} bytes")
        
        # ===== COMPLETAMENTO =====
        if result.status != PipelineStatus.LOW_CONFIDENCE:
            result.status = PipelineStatus.COMPLETED
        
        result.metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[{generation_id}] Pipeline completata con stato: {result.status.value}")
        
    except Exception as e:
        logger.error(f"[{generation_id}] Errore pipeline: {str(e)}", exc_info=True)
        result.status = PipelineStatus.FAILED
        result.error_message = str(e)
    
    return result

# ============== RETRY ASINCRONO ==============

async def run_async_retry(
    generation_id: str,
    user_request: str,
    original_prompt: str,
    reference_image_base64: Optional[str] = None,
    style_lock: bool = False,
    db=None,
    gridfs_bucket=None
) -> Optional[PipelineResult]:
    """
    Ciclo di retry asincrono per generazioni LOW_CONFIDENCE.
    Esegue fino a MAX_ASYNC_RETRIES tentativi addizionali.
    
    Questo metodo viene chiamato in background dopo che la pipeline sincrona
    ha restituito uno stato LOW_CONFIDENCE.
    """
    logger.info(f"[{generation_id}] Avvio retry asincrono ({MAX_ASYNC_RETRIES} tentativi)")
    
    best_result = None
    best_score = 0.0
    
    for attempt in range(MAX_ASYNC_RETRIES):
        try:
            logger.info(f"[{generation_id}] Retry asincrono {attempt + 1}/{MAX_ASYNC_RETRIES}")
            
            # Modifica il prompt per enfatizzare gli elementi mancanti
            enhanced_prompt = f"""{original_prompt}

CORREZIONE CRITICA - ELEMENTI OBBLIGATORI:
- Il barattolo di popcorn DEVE essere ben visibile in primo piano
- La scritta "POPPICONNI" DEVE essere scritta chiaramente sul barattolo
- Il testo deve essere LEGGIBILE, FRONTALE e in MAIUSCOLO
- Stile: line-art semplice per libro da colorare per bambini
"""
            
            # Genera nuova immagine
            image_bytes = await phase2_image_generation(
                generation_prompt=enhanced_prompt,
                reference_image_base64=reference_image_base64,
                style_lock=style_lock
            )
            
            # Quality Check
            qc_report = await phase3_quality_check(
                image_bytes=image_bytes,
                original_prompt=enhanced_prompt
            )
            
            if qc_report.confidence_score > best_score:
                best_score = qc_report.confidence_score
                
                # Post-produzione
                final_png, final_pdf, thumbnail, metadata = phase4_postproduction(
                    image_bytes=image_bytes,
                    generation_id=generation_id,
                    metadata={"async_retry_attempt": attempt + 1}
                )
                
                best_result = PipelineResult(
                    status=PipelineStatus.COMPLETED if qc_report.result == QCResult.PASS else PipelineStatus.LOW_CONFIDENCE,
                    generation_id=generation_id,
                    user_request=user_request,
                    optimized_prompt=enhanced_prompt,
                    candidate_image_base64=base64.b64encode(image_bytes).decode('utf-8'),
                    qc_report=qc_report,
                    final_png_bytes=final_png,
                    final_pdf_bytes=final_pdf,
                    thumbnail_bytes=thumbnail,
                    metadata=metadata,
                    retry_count=attempt + 1
                )
            
            # Se QC passa, interrompi il retry
            if qc_report.result == QCResult.PASS:
                logger.info(f"[{generation_id}] Retry asincrono SUCCESSO al tentativo {attempt + 1}")
                break
            
            # Attendi un po' prima del prossimo tentativo
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"[{generation_id}] Errore retry asincrono {attempt + 1}: {str(e)}")
            continue
    
    if best_result:
        logger.info(f"[{generation_id}] Retry asincrono completato. Stato: {best_result.status.value}, Score: {best_score}")
        
        # Salva nel database se disponibile
        if db and gridfs_bucket and best_result.status == PipelineStatus.COMPLETED:
            # TODO: Implementare salvataggio su DB
            pass
    
    return best_result
