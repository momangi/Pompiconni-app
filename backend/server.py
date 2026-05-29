from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, Response, JSONResponse
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
import base64
import aiofiles
import io
from pdf_generator import generate_book_pdf
from PyPDF2 import PdfMerger, PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image as PILImage
from streaming import stream_gridfs_response, stream_gridfs_response_with_variants
from media_pipeline import ensure_variants

# Core infrastructure (Fase 4A refactor) ---------------------------------------
# Centralized configuration, database client, security helpers and logging
# previously inlined in this file. Existing module-level symbols below are
# preserved as aliases so the rest of server.py keeps working unchanged.
from core.config import settings
from core.database import client, db, gridfs_bucket, ping_db, close_client
from core.security import create_token, verify_token, security_bearer as security

# Domain services (Fase 4B Batch 1) --------------------------------------------
# Encapsulate the data access for reviews/site_settings/themes. The legacy
# route bodies are kept intact for every other domain and will be migrated
# in subsequent batches.
from services import review_service, settings_service, theme_service

# Domain services (Fase 4B Batch 2) --------------------------------------------
# Posters / games / level_backgrounds. GridFS-heavy flows (image streaming,
# upload, PDF download) intentionally stay in server.py for this batch.
from services import poster_service, game_service, level_background_service

# Domain services (Fase 4B Batch 3) --------------------------------------------
# Bundles / illustrations CRUD + metadata. Heavy GridFS, generated-PDF,
# upload/attach/streaming routes intentionally stay in server.py for this
# batch. The illustration service applies the R1 fix (no _id leak).
from services import bundle_service, illustration_service

# Domain services (Fase 4B Batch 4) --------------------------------------------
# Books / book_scenes / reading_progress CRUD + metadata. GridFS (cover,
# scene images), generated PDF (public/admin) and uploads intentionally
# stay in server.py for this batch. The book service applies the R1 fix
# (no _id leak on books and book_scenes responses).
from services import book_service

# Domain models (Fase 4A refactor) ---------------------------------------------
# All Pydantic classes now live in /app/backend/models/*.py and are re-exported
# via the package __init__. Importing them here keeps every existing route
# signature compatible with no further changes.
from models import (
    # auth
    LoginRequest, LoginResponse,
    # theme
    Theme, ThemeBase, ThemeCreate, ThemeUpdate, THEME_COLOR_PALETTE,
    # illustration
    Illustration, IllustrationBase, IllustrationCreate, GenerateRequest,
    # bundle
    Bundle, BundleBase, BundleCreate, BundleUpdate,
    # review
    Review, ReviewUpdate,
    # game
    Game,
    # level background
    GameLevelBackground, GameLevelBackgroundBase,
    GameLevelBackgroundCreate, GameLevelBackgroundUpdate,
    # site settings
    SiteSettings, SiteSettingsUpdate, HeroImageResponse,
    # book
    Book, BookBase, BookCreate, BookScene, BookSceneCreate, BookSceneText,
    ReadingProgress, MAX_SCENES_PER_BOOK,
    # generation
    GenerationStyle, GenerationStyleBase, GenerationStyleCreate,
    PoppiconniGenerateRequest, PoppiconniGenerateResponse,
    # poster
    Poster, PosterBase, PosterCreate, PosterUpdate, PosterStatus,
    # character
    CharacterTextUpdate,
    # common
    DownloadEvent,
)

# Legacy module-level aliases — kept so existing route bodies that still
# reference `JWT_SECRET`, `ADMIN_PASSWORD`, etc. continue to work unchanged.
ROOT_DIR = settings.root_dir
UPLOAD_DIR = settings.upload_dir
mongo_url = settings.mongo_uri
mongo_db_name = settings.mongo_db_name
JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = settings.jwt_algorithm
JWT_EXPIRATION_HOURS = settings.jwt_expiration_hours
ADMIN_EMAIL = settings.admin_email
ADMIN_PASSWORD = settings.admin_password
STRIPE_SECRET_KEY = settings.stripe_secret_key
STRIPE_PUBLISHABLE_KEY = settings.stripe_publishable_key
STRIPE_WEBHOOK_SECRET = settings.stripe_webhook_secret

# Create the main app
app = FastAPI(title="Poppiconni API", version="1.0.0")

# Create routers
api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin")

# Logger
logger = logging.getLogger(__name__)

# ============== MEDIA PIPELINE HELPERS (Fase 2) ==============

import asyncio as _asyncio

async def _generate_variants_silent(file_id):
    """Background variant generation that never raises; logs failures."""
    try:
        report = await ensure_variants(
            db=db,
            gridfs_bucket=gridfs_bucket,
            source_file_id=file_id,
            skip_if_exists=True,
        )
        created = sum(1 for v in report.get("variants", []) if v.get("created"))
        if created:
            logger.info(f"Variants generated for {file_id}: {created} new")
        if report.get("errors"):
            logger.warning(f"Variant partial errors for {file_id}: {report['errors']}")
    except Exception as e:
        logger.warning(f"Variant generation failed for {file_id}: {str(e)[:200]}")


def fire_variants(file_id):
    """Fire-and-forget variant generation. Safe to call after any image upload."""
    try:
        _asyncio.create_task(_generate_variants_silent(file_id))
    except Exception as e:
        logger.warning(f"Could not schedule variants for {file_id}: {e}")

# ============== MODELS ==============
# All Pydantic models moved to /app/backend/models/*.py in Fase 4A.
# They are imported at the top of this file via `from models import ...`
# and kept available under the same names for backward compatibility.

# ============== AUTH HELPERS ==============
# `create_token` and `verify_token` moved to `core/security.py` in Fase 4A.
# They are imported at the top of this file and remain usable everywhere
# in this module under the same names.

def sanitize_scene_html(html: str) -> str:
    """
    Sanitize HTML from TipTap editor.
    Only allows: p, br, ul, li, strong, em, span (with specific classes)
    Removes: scripts, styles, links, images, colors, fonts, etc.
    """
    if not html:
        return ""
    
    # Allowed tags
    allowed_tags = {'p', 'br', 'ul', 'li', 'strong', 'em', 'span'}
    # Allowed classes for alignment and font size
    allowed_classes = {'text-left', 'text-center', 'text-right', 'font-size-s', 'font-size-m', 'font-size-l'}
    
    # Remove script/style tags completely
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove on* event handlers
    html = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    html = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Remove style attributes (no inline colors/fonts)
    html = re.sub(r'\s+style\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Clean class attributes - only keep allowed classes
    def clean_class(match):
        classes = match.group(1).split()
        kept = [c for c in classes if c in allowed_classes]
        if kept:
            return f' class="{" ".join(kept)}"'
        return ''
    
    html = re.sub(r'\s+class\s*=\s*["\']([^"\']*)["\']', clean_class, html, flags=re.IGNORECASE)
    
    # Remove disallowed tags but keep their content
    disallowed_pattern = r'</?(?!(?:' + '|'.join(allowed_tags) + r')\b)[a-z][^>]*>'
    html = re.sub(disallowed_pattern, '', html, flags=re.IGNORECASE)
    
    return html.strip()

# ============== SEED DATA ==============

SEED_REVIEWS = [
    {"id": "1", "name": "Maria R.", "role": "Mamma di Sofia, 5 anni", "text": "Sofia adora Poppiconni! Le tavole sono perfette per le sue manine e il personaggio è dolcissimo.", "rating": 5, "is_approved": True},
    {"id": "2", "name": "Luca B.", "role": "Papà di Marco e Giulia", "text": "Finalmente disegni da colorare con linee spesse e chiare. I miei bimbi non escono mai dai bordi!", "rating": 5, "is_approved": True},
    {"id": "3", "name": "Anna T.", "role": "Maestra d'asilo", "text": "Uso le tavole di Poppiconni in classe. I bambini adorano il personaggio e i temi sono educativi.", "rating": 5, "is_approved": True},
    {"id": "4", "name": "Giuseppe M.", "role": "Nonno di 3 nipotini", "text": "Ho stampato tutte le tavole gratuite. I nipotini sono entusiasti di colorare questo unicorno buffo!", "rating": 5, "is_approved": True},
    {"id": "5", "name": "Francesca L.", "role": "Mamma di Emma, 4 anni", "text": "Emma chiede sempre 'il cavallino con il corno'! Poppiconni è diventato il suo personaggio preferito.", "rating": 5, "is_approved": True},
    {"id": "6", "name": "Roberto S.", "role": "Papà di Matteo, 6 anni", "text": "Qualità eccellente delle illustrazioni. Mio figlio si diverte tantissimo a colorare ogni dettaglio.", "rating": 5, "is_approved": True},
    {"id": "7", "name": "Claudia P.", "role": "Educatrice", "text": "I temi sono ben pensati e adatti a diverse età. Uso molto il tema dei mestieri per attività didattiche.", "rating": 5, "is_approved": True},
    {"id": "8", "name": "Marco V.", "role": "Papà di due gemelle", "text": "Le mie bambine adorano Poppiconni! Il personaggio è tenero e le linee sono perfette per colorare.", "rating": 5, "is_approved": True},
    {"id": "9", "name": "Silvia G.", "role": "Mamma di Leonardo, 7 anni", "text": "Anche mio figlio grande ama Poppiconni. I disegni sono abbastanza dettagliati da non annoiare.", "rating": 5, "is_approved": True},
    {"id": "10", "name": "Andrea C.", "role": "Papà di Aurora, 3 anni", "text": "Aurora sta imparando i colori grazie a Poppiconni. Un progetto davvero ben fatto!", "rating": 5, "is_approved": True},
    {"id": "11", "name": "Elena B.", "role": "Zia di 4 nipoti", "text": "Regalo sempre album di Poppiconni ai miei nipotini. Sono sempre un successo!", "rating": 5, "is_approved": True},
    {"id": "12", "name": "Davide R.", "role": "Papà di Chiara, 5 anni", "text": "Il tema dello zoo è fantastico! Chiara ha imparato tanti animali colorando con Poppiconni.", "rating": 5, "is_approved": True},
    {"id": "13", "name": "Paola M.", "role": "Mamma di Tommaso, 4 anni", "text": "Tommaso porta sempre i disegni di Poppiconni all'asilo per mostrarli agli amichetti!", "rating": 5, "is_approved": True},
    {"id": "14", "name": "Stefano L.", "role": "Papà di Sofia e Mattia", "text": "Ottimo per tenere i bambini impegnati in modo creativo. Consiglio il bundle completo!", "rating": 5, "is_approved": True},
    {"id": "15", "name": "Valentina F.", "role": "Mamma di Giulia, 6 anni", "text": "Giulia ama il tema delle stagioni. Abbiamo stampato tutto per ogni periodo dell'anno!", "rating": 5, "is_approved": True}
]

SEED_THEMES = [
    {"id": "mestieri", "name": "I Mestieri", "description": "Poppiconni scopre i mestieri: pompiere, dottore, cuoco, pilota e tanti altri!", "icon": "Briefcase", "color": "#FFB6C1", "illustrationCount": 12},
    {"id": "fattoria", "name": "La Fattoria", "description": "Poppiconni in fattoria tra mucche, galline, maialini e trattori!", "icon": "Tractor", "color": "#98D8AA", "illustrationCount": 10},
    {"id": "zoo", "name": "Lo Zoo", "description": "Poppiconni visita lo zoo e incontra leoni, elefanti, giraffe e scimmie!", "icon": "Cat", "color": "#FFE5B4", "illustrationCount": 14},
    {"id": "sport", "name": "Lo Sport", "description": "Poppiconni si diverte con calcio, nuoto, tennis e tanti sport!", "icon": "Trophy", "color": "#B4D4FF", "illustrationCount": 8},
    {"id": "stagioni", "name": "Le Stagioni", "description": "Poppiconni attraverso primavera, estate, autunno e inverno!", "icon": "Sun", "color": "#FFDAB9", "illustrationCount": 16},
    {"id": "quotidiano", "name": "Vita Quotidiana", "description": "Poppiconni a scuola, al parco, in cucina e nelle avventure di ogni giorno!", "icon": "Home", "color": "#E6E6FA", "illustrationCount": 11}
]

SEED_ILLUSTRATIONS = [
    {"id": "1", "themeId": "mestieri", "title": "Poppiconni Pompiere", "description": "Il nostro unicorno salva la giornata!", "downloadCount": 234, "isFree": True, "price": 0},
    {"id": "2", "themeId": "mestieri", "title": "Poppiconni Dottore", "description": "Con lo stetoscopio e tanto amore", "downloadCount": 189, "isFree": True, "price": 0},
    {"id": "3", "themeId": "mestieri", "title": "Poppiconni Cuoco", "description": "Prepara dolcetti magici!", "downloadCount": 156, "isFree": False, "price": 0.99},
    {"id": "4", "themeId": "mestieri", "title": "Poppiconni Pilota", "description": "Vola tra le nuvole arcobaleno", "downloadCount": 201, "isFree": False, "price": 0.99},
    {"id": "5", "themeId": "mestieri", "title": "Poppiconni Astronauta", "description": "Alla scoperta delle stelle", "downloadCount": 178, "isFree": True, "price": 0},
    {"id": "6", "themeId": "fattoria", "title": "Poppiconni e la Mucca", "description": "Nuovi amici in fattoria", "downloadCount": 145, "isFree": True, "price": 0},
    {"id": "7", "themeId": "fattoria", "title": "Poppiconni sul Trattore", "description": "Guidando tra i campi", "downloadCount": 167, "isFree": False, "price": 0.99},
    {"id": "8", "themeId": "fattoria", "title": "Poppiconni e le Galline", "description": "A caccia di uova colorate", "downloadCount": 134, "isFree": True, "price": 0},
    {"id": "9", "themeId": "fattoria", "title": "Poppiconni e il Maialino", "description": "Amici nel fango!", "downloadCount": 112, "isFree": False, "price": 0.99},
    {"id": "10", "themeId": "zoo", "title": "Poppiconni e il Leone", "description": "Un incontro coraggioso", "downloadCount": 198, "isFree": True, "price": 0},
    {"id": "11", "themeId": "zoo", "title": "Poppiconni e l'Elefante", "description": "Grande amicizia!", "downloadCount": 223, "isFree": True, "price": 0},
    {"id": "12", "themeId": "zoo", "title": "Poppiconni e la Giraffa", "description": "Guardando in alto", "downloadCount": 187, "isFree": False, "price": 0.99},
    {"id": "13", "themeId": "zoo", "title": "Poppiconni e le Scimmie", "description": "Acrobazie divertenti", "downloadCount": 156, "isFree": True, "price": 0},
    {"id": "14", "themeId": "sport", "title": "Poppiconni Calciatore", "description": "Gol magico!", "downloadCount": 245, "isFree": True, "price": 0},
    {"id": "15", "themeId": "sport", "title": "Poppiconni Nuotatore", "description": "Splash tra le onde", "downloadCount": 134, "isFree": False, "price": 0.99},
    {"id": "16", "themeId": "sport", "title": "Poppiconni Tennista", "description": "Ace arcobaleno!", "downloadCount": 98, "isFree": True, "price": 0},
    {"id": "17", "themeId": "stagioni", "title": "Poppiconni in Primavera", "description": "Tra fiori e farfalle", "downloadCount": 278, "isFree": True, "price": 0},
    {"id": "18", "themeId": "stagioni", "title": "Poppiconni d'Estate", "description": "Al mare con il gelato", "downloadCount": 312, "isFree": True, "price": 0},
    {"id": "19", "themeId": "stagioni", "title": "Poppiconni d'Autunno", "description": "Tra le foglie colorate", "downloadCount": 189, "isFree": False, "price": 0.99},
    {"id": "20", "themeId": "stagioni", "title": "Poppiconni d'Inverno", "description": "Pupazzo di neve magico", "downloadCount": 267, "isFree": True, "price": 0},
    {"id": "21", "themeId": "quotidiano", "title": "Poppiconni a Scuola", "description": "Primo giorno di scuola", "downloadCount": 145, "isFree": True, "price": 0},
    {"id": "22", "themeId": "quotidiano", "title": "Poppiconni al Parco", "description": "Giochi sull'altalena", "downloadCount": 167, "isFree": False, "price": 0.99},
    {"id": "23", "themeId": "quotidiano", "title": "Poppiconni in Cucina", "description": "Biscotti con la mamma", "downloadCount": 198, "isFree": True, "price": 0}
]

SEED_BUNDLES = [
    {"id": "1", "title": "Starter Pack Poppiconni", "subtitle": "10 tavole gratuite per iniziare a colorare!", "illustrationCount": 0, "price": 0, "currency": "EUR", "isFree": True, "badgeText": "GRATIS", "isActive": True, "sortOrder": 1, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None},
    {"id": "2", "title": "Album Mestieri Completo", "subtitle": "Tutte le 12 tavole dei mestieri in PDF", "illustrationCount": 0, "price": 4.99, "currency": "EUR", "isFree": False, "badgeText": "", "isActive": True, "sortOrder": 2, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None},
    {"id": "3", "title": "Mega Pack Stagioni", "subtitle": "16 tavole per tutte le stagioni + bonus festività", "illustrationCount": 0, "price": 6.99, "currency": "EUR", "isFree": False, "badgeText": "", "isActive": True, "sortOrder": 3, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None},
    {"id": "4", "title": "Collezione Completa", "subtitle": "Tutti i temi + bonus esclusivi", "illustrationCount": 0, "price": 19.99, "currency": "EUR", "isFree": False, "badgeText": "BEST VALUE", "isActive": True, "sortOrder": 4, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None}
]

# ============== DATABASE INIT ==============

async def init_database():
    """Initialize database with seed data if empty"""
    # Check if themes exist - use insert_many for batch performance
    themes_count = await db.themes.count_documents({})
    if themes_count == 0:
        now = datetime.now(timezone.utc)
        themes_to_insert = []
        for theme in SEED_THEMES:
            theme['createdAt'] = now
            theme['updatedAt'] = now
            theme['backgroundImageFileId'] = None
            theme['backgroundImageUrl'] = None
            theme['backgroundOpacity'] = 30
            themes_to_insert.append(theme)
        await db.themes.insert_many(themes_to_insert)
        logger.info("Seed themes inserted")
    else:
        # Migrate existing themes to add background fields if missing
        await db.themes.update_many(
            {"backgroundOpacity": {"$exists": False}},
            {"$set": {
                "backgroundOpacity": 30,
                "backgroundImageFileId": None,
                "backgroundImageUrl": None
            }}
        )
        logger.info("Existing themes migrated with background fields")
    
    # Check if illustrations exist - use insert_many for batch performance
    illustrations_count = await db.illustrations.count_documents({})
    if illustrations_count == 0:
        now = datetime.now(timezone.utc)
        illustrations_to_insert = []
        for illust in SEED_ILLUSTRATIONS:
            # Reset download count to 0 - no fake numbers
            illust['downloadCount'] = 0
            illust['createdAt'] = now
            illust['updatedAt'] = now
            # Set pdfFileId and imageFileId to None initially (files not uploaded yet)
            illust['pdfFileId'] = None
            illust['imageFileId'] = None
            illustrations_to_insert.append(illust)
        await db.illustrations.insert_many(illustrations_to_insert)
        logger.info("Seed illustrations inserted with zero download counts")
    
    # Check if bundles exist - use insert_many for batch performance
    bundles_count = await db.bundles.count_documents({})
    if bundles_count == 0:
        now = datetime.now(timezone.utc)
        bundles_to_insert = []
        for bundle in SEED_BUNDLES:
            bundle['createdAt'] = now
            bundle['updatedAt'] = now
            bundles_to_insert.append(bundle)
        await db.bundles.insert_many(bundles_to_insert)
        logger.info("Seed bundles inserted")
    else:
        # Migrate existing bundles to add new fields if missing
        await db.bundles.update_many(
            {"isActive": {"$exists": False}},
            {"$set": {
                "isActive": True,
                "sortOrder": 0,
                "badgeText": "",
                "subtitle": "",
                "currency": "EUR",
                "backgroundImageFileId": None,
                "backgroundImageUrl": None,
                "pdfFileId": None,
                "pdfUrl": None,
                "backgroundOpacity": 30,
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        # Add backgroundOpacity to bundles that don't have it
        await db.bundles.update_many(
            {"backgroundOpacity": {"$exists": False}},
            {"$set": {"backgroundOpacity": 30}}
        )
        # Add generatedPdf fields for auto-generation cache
        await db.bundles.update_many(
            {"generatedPdfFileId": {"$exists": False}},
            {"$set": {"generatedPdfFileId": None, "generatedPdfHash": None}}
        )
        # Migrate name to title if needed
        await db.bundles.update_many(
            {"title": {"$exists": False}, "name": {"$exists": True}},
            [{"$set": {"title": "$name", "subtitle": "$description"}}]
        )
        # Set sortOrder based on existing order
        bundles = await db.bundles.find({}, {"id": 1}).to_list(100)
        for idx, b in enumerate(bundles, 1):
            await db.bundles.update_one({"id": b['id'], "sortOrder": 0}, {"$set": {"sortOrder": idx}})
        logger.info("Existing bundles migrated with new fields")
    
    # Check if reviews exist - use insert_many for batch performance
    reviews_count = await db.reviews.count_documents({})
    if reviews_count == 0:
        await db.reviews.insert_many(SEED_REVIEWS)
        logger.info("Seed reviews inserted with is_approved field")
    
    # Initialize site_settings if not exists
    settings = await db.site_settings.find_one({"id": "global"})
    if not settings:
        await db.site_settings.insert_one({
            "id": "global",
            "show_reviews": True,
            "stripe_enabled": bool(STRIPE_SECRET_KEY),
            "createdAt": datetime.now(timezone.utc)
        })
        logger.info("Site settings initialized")
    
    # Initialize default games if not exist
    games_count = await db.games.count_documents({})
    if games_count == 0:
        default_games = [
            {
                "id": str(uuid.uuid4()),
                "slug": "bolle-magiche",
                "title": "Bolle Magiche",
                "shortDescription": "Scoppia le bolle colorate con Poppiconni! Un gioco divertente per tutti.",
                "longDescription": "Aiuta Poppiconni a scoppiare tutte le bolle colorate che fluttuano nel cielo! Un gioco semplice e divertente, perfetto per i più piccoli. Tocca le bolle per farle scoppiare e accumula punti. Attenzione: le bolle diventano sempre più veloci!",
                "status": "available",
                "ageRecommended": "3+",
                "howToPlay": [
                    "Tocca o clicca sulle bolle per farle scoppiare",
                    "Accumula punti scoppiando più bolle possibili",
                    "Non lasciare che le bolle raggiungano il fondo!"
                ],
                "thumbnailFileId": None,
                "sortOrder": 1,
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            },
            {
                "id": str(uuid.uuid4()),
                "slug": "puzzle-poppiconni",
                "title": "Puzzle Poppiconni",
                "shortDescription": "Ricomponi le immagini di Poppiconni in tanti puzzle colorati!",
                "longDescription": "Metti alla prova le tue abilità con i puzzle di Poppiconni! Ricomponi le immagini delle avventure del nostro amico elefantino.",
                "status": "coming_soon",
                "ageRecommended": "4+",
                "howToPlay": [
                    "Trascina i pezzi nella posizione corretta",
                    "Completa il puzzle per sbloccare nuove immagini",
                    "Sfida te stesso con puzzle sempre più difficili!"
                ],
                "thumbnailFileId": None,
                "sortOrder": 2,
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            },
            {
                "id": str(uuid.uuid4()),
                "slug": "memory-poppiconni",
                "title": "Memory Poppiconni",
                "shortDescription": "Trova le coppie e allena la memoria con le carte di Poppiconni!",
                "longDescription": "Allena la tua memoria con il gioco di carte Memory! Trova tutte le coppie delle carte con le immagini di Poppiconni.",
                "status": "coming_soon",
                "ageRecommended": "3+",
                "howToPlay": [
                    "Gira due carte alla volta",
                    "Cerca di trovare le coppie uguali",
                    "Completa il gioco con meno mosse possibili!"
                ],
                "thumbnailFileId": None,
                "sortOrder": 3,
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
        ]
        await db.games.insert_many(default_games)
        logger.info("Default games initialized")

@app.on_event("startup")
async def startup_event():
    """
    Best-effort startup: seed data + index creation are wrapped in try/except
    so the pod never enters CrashLoopBackOff if Atlas is momentarily slow or
    a single migration fails. Health endpoints work regardless.
    """
    try:
        await init_database()
    except Exception as e:
        logger.error(f"init_database failed (non-fatal): {str(e)[:200]}")
    
    # Create TTL index for download_limits (auto-delete after 30 days)
    try:
        await db.download_limits.create_index("expiresAt", expireAfterSeconds=0)
        logger.info("TTL index created for download_limits")
    except Exception as e:
        # Index might already exist
        logger.debug(f"TTL index creation: {str(e)}")

    # ============== PERFORMANCE INDEXES (Fase 1) ==============
    # create_index is idempotent: no-op when an equivalent index already exists.
    # All indexes here support hot-path queries grepped from the codebase.
    perf_indexes = [
        # illustrations
        ("illustrations", [("id", 1), ("isPublished", 1)], {"name": "ix_id_isPublished"}),
        ("illustrations", [("isPublished", 1)],            {"name": "ix_isPublished"}),
        # posters
        ("posters",       [("id", 1), ("status", 1)],      {"name": "ix_id_status"}),
        ("posters",       [("status", 1)],                 {"name": "ix_status"}),
        # books
        ("books",         [("id", 1)],                     {"name": "ix_id"}),
        ("books",         [("slug", 1)],                   {"name": "ix_slug"}),
        # book_scenes
        ("book_scenes",   [("bookId", 1), ("sceneNumber", 1)], {"name": "ix_bookId_sceneNumber"}),
        ("book_scenes",   [("id", 1), ("bookId", 1)],      {"name": "ix_id_bookId"}),
        # bundles
        ("bundles",       [("id", 1)],                     {"name": "ix_id"}),
        # games
        ("games",         [("id", 1)],                     {"name": "ix_id"}),
        ("games",         [("slug", 1)],                   {"name": "ix_slug"}),
        # themes
        ("themes",        [("id", 1)],                     {"name": "ix_id"}),
        # game_level_backgrounds
        ("game_level_backgrounds", [("id", 1)],            {"name": "ix_id"}),
        # generation_styles
        ("generation_styles", [("id", 1), ("userId", 1)],  {"name": "ix_id_userId"}),
        # character_images
        ("character_images", [("trait", 1)],               {"name": "ix_trait"}),
        # reviews
        ("reviews",       [("is_approved", 1)],            {"name": "ix_is_approved"}),
        # reading_progress
        ("reading_progress", [("bookId", 1), ("visitorId", 1)], {"name": "ix_bookId_visitorId"}),
        # download_limits (extra: key lookup for rate limiting)
        ("download_limits", [("key", 1)],                  {"name": "ix_key"}),
        # admins
        ("admins",        [("email", 1)],                  {"name": "ix_email", "unique": True}),
        # site_settings (single doc, but cheap)
        ("site_settings", [("id", 1)],                     {"name": "ix_id"}),
    ]
    created, skipped = 0, 0
    for coll_name, keys, opts in perf_indexes:
        try:
            await db[coll_name].create_index(keys, **opts)
            created += 1
        except Exception as e:
            skipped += 1
            logger.debug(f"Index {coll_name}.{opts.get('name')} skipped: {str(e)[:80]}")
    logger.info(f"Performance indexes ensured: created_or_existing={created}, skipped={skipped}")
    
    # Migrate existing illustrations: set isPublished=True if field missing
    migration_result = await db.illustrations.update_many(
        {"isPublished": {"$exists": False}},
        {"$set": {"isPublished": True, "publishedAt": datetime.now(timezone.utc)}}
    )
    if migration_result.modified_count > 0:
        logger.info(f"Migrated {migration_result.modified_count} illustrations to published status")
    
    # Migrate existing illustrations: set downloadEnabled=True if field missing
    download_migration = await db.illustrations.update_many(
        {"downloadEnabled": {"$exists": False}},
        {"$set": {"downloadEnabled": True}}
    )
    if download_migration.modified_count > 0:
        logger.info(f"Migrated {download_migration.modified_count} illustrations with downloadEnabled=True")
    
    # Migrate existing posters: set downloadEnabled=True if field missing
    poster_migration = await db.posters.update_many(
        {"downloadEnabled": {"$exists": False}},
        {"$set": {"downloadEnabled": True}}
    )
    if poster_migration.modified_count > 0:
        logger.info(f"Migrated {poster_migration.modified_count} posters with downloadEnabled=True")
    
    logger.info("Database initialized")

# ============== PUBLIC ENDPOINTS ==============

@api_router.get("/")
async def root():
    return {"message": "Poppiconni API v1.0", "status": "online"}

# Public themes/illustrations/bundles/reviews/site-settings/brand-kit
# routes moved to `api/public/*` in Fase 4C. The GridFS
# `/themes/{id}/background-image` stream stays here below.

@api_router.get("/themes/{theme_id}/background-image")
async def get_theme_background_image(
    theme_id: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve theme background image (streaming + ETag + responsive variants)."""
    theme = await db.themes.find_one({"id": theme_id})
    if not theme or not theme.get('backgroundImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=theme['backgroundImageFileId'],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )

@api_router.get("/search/illustrations")
async def search_illustrations(q: str = "", limit: int = 48):
    """
    Public search endpoint for illustrations.
    Returns both free and premium illustrations sorted by relevance score.
    """
    # Validate and normalize query
    if not q or not q.strip():
        return {"q": "", "results": []}
    
    # Normalize: lowercase, trim, remove basic punctuation
    query_normalized = q.lower().strip()
    query_normalized = re.sub(r'[^\w\s]', '', query_normalized)
    
    if not query_normalized:
        return {"q": q, "results": []}
    
    # Tokenize query
    tokens = [t for t in query_normalized.split() if len(t) >= 2]
    if not tokens:
        return {"q": q, "results": []}
    
    # Get only published illustrations (public endpoint)
    illustrations = await db.illustrations.find({"isPublished": True}, {"_id": 0}).to_list(1000)
    
    # Get all themes for name lookup
    themes = await db.themes.find({}, {"_id": 0}).to_list(100)
    theme_map = {t['id']: t.get('name', '') for t in themes}
    
    # Calculate relevance score for each illustration
    results = []
    for illust in illustrations:
        score = 0
        title = (illust.get('title', '') or '').lower()
        description = (illust.get('description', '') or '').lower()
        theme_name = theme_map.get(illust.get('themeId', ''), '').lower()
        keywords = (illust.get('keywords', '') or '').lower()
        
        # +20 if title contains entire query
        if query_normalized in title:
            score += 20
        
        # Per-token scoring
        for token in tokens:
            # +10 for token in title
            if token in title:
                score += 10
            # +6 for token in description
            if token in description:
                score += 6
            # +4 for token in theme name
            if token in theme_name:
                score += 4
            # +3 for token in keywords
            if token in keywords:
                score += 3
        
        if score > 0:
            results.append({
                "id": illust.get('id'),
                "title": illust.get('title', ''),
                "description": illust.get('description', ''),
                "isFree": illust.get('isFree', True),
                "price": illust.get('price', 0),
                "imageFileId": illust.get('imageFileId'),
                "themeName": theme_map.get(illust.get('themeId', ''), ''),
                "themeId": illust.get('themeId'),
                "score": score
            })
    
    # Sort by score (descending), then by title (alphabetical) for tie-break
    results.sort(key=lambda x: (-x['score'], x['title'].lower()))
    
    # Apply limit
    results = results[:limit]
    
    return {
        "q": q,
        "results": results
    }

@api_router.post("/illustrations/{illustration_id}/download")
async def download_illustration(illustration_id: str, request: Request):
    """
    Real file download endpoint using GridFS.
    Returns the PDF file as a downloadable attachment.
    Only for published illustrations with download enabled.
    """
    # Find the illustration - only if published
    illust = await db.illustrations.find_one({"id": illustration_id, "isPublished": True})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    # Check if download is enabled
    if not illust.get('downloadEnabled', True):
        raise HTTPException(status_code=403, detail="Download non disponibile per questa illustrazione")
    
    # Check if file exists in GridFS
    pdf_file_id = illust.get('pdfFileId')
    if not pdf_file_id:
        raise HTTPException(
            status_code=404, 
            detail="File non ancora disponibile. L'amministratore deve prima caricare il PDF."
        )

    # Log download event + increment counter (before streaming so we count attempts)
    await db.download_events.insert_one({
        "id": str(uuid.uuid4()),
        "illustrationId": illustration_id,
        "bundleId": None,
        "downloadedAt": datetime.now(timezone.utc)
    })
    await db.illustrations.update_one(
        {"id": illustration_id},
        {"$inc": {"downloadCount": 1}}
    )

    # Resolve filename (sanitize spaces/quotes)
    raw_name = f"pompiconni_{illust.get('title') or illustration_id}.pdf"
    filename = raw_name.replace(' ', '_').replace('"', '').replace("'", "")

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

@api_router.get("/illustrations/{illustration_id}/download-status")
async def get_download_status(illustration_id: str):
    """Check if a file is available for download - only for published illustrations"""
    illust = await db.illustrations.find_one({"id": illustration_id, "isPublished": True})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    has_pdf = bool(illust.get('pdfFileId'))
    has_image = bool(illust.get('imageFileId'))
    return {
        "available": has_pdf,
        "hasImage": has_image,
        "message": "File disponibile" if has_pdf else "File non ancora disponibile"
    }

@api_router.get("/illustrations/{illustration_id}/image")
async def get_illustration_image(
    illustration_id: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """
    Serve the illustration image from GridFS with true streaming + ETag.
    Supports responsive variants via `?w=400|800|1600` and `?format=webp|jpg|png`.
    Falls back to the original when the requested variant is missing.
    Only for published illustrations.
    """
    illust = await db.illustrations.find_one({"id": illustration_id, "isPublished": True})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")

    image_file_id = illust.get('imageFileId')
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

@api_router.get("/illustrations/{illustration_id}/image-status")
async def get_image_status(illustration_id: str):
    """Check if an image is available - only for published illustrations"""
    illust = await db.illustrations.find_one({"id": illustration_id, "isPublished": True})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    has_image = bool(illust.get('imageFileId'))
    return {
        "available": has_image,
        "imageUrl": f"/api/illustrations/{illustration_id}/image" if has_image else None,
        "message": "Immagine disponibile" if has_image else "Immagine non ancora disponibile"
    }

# Public `/bundles`, `/reviews`, `/site-settings`, `/brand-kit` moved to
# `api/public/*` in Fase 4C router split.

# ============== HELPER FUNCTIONS ==============

async def recalculate_bundle_counts():
    """
    Ricalcola automaticamente i conteggi dei bundle basandosi sui dati reali.
    Delegates to ``bundle_service`` (Fase 4B Batch 3). Wrapper kept for
    backward compatibility with the existing call sites in this module
    (admin attach-pdf, attach-image, AI generation flows).
    """
    await bundle_service.recalculate_named_bundle_counts()

async def recalculate_theme_count(theme_id: str):
    """
    Ricalcola il conteggio di TUTTE le illustrazioni per un singolo tema.
    Delegates to ``theme_service`` (Fase 4B Batch 1). Wrapper kept for
    backward compatibility with the existing call sites in this module.
    """
    await theme_service.recalc_illustration_count(theme_id)

# ============== ADMIN ENDPOINTS ==============

# Admin /login + /dashboard moved to `api/admin/auth.py` and
# `api/admin/maintenance.py` (Auth & Maintenance mini-batch).

# Admin themes CRUD moved to `api/admin/themes.py` (Fase 4C). The
# GridFS `/themes/{id}/upload-background` route stays below.

@admin_router.post("/themes/{theme_id}/upload-background")
async def upload_theme_background(
    theme_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload background image for a theme"""
    from bson import ObjectId
    
    theme = await db.themes.find_one({"id": theme_id})
    if not theme:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"theme_bg_{theme_id}{ext}"
        
        # Delete old image if exists
        if theme.get('backgroundImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(theme['backgroundImageFileId']))
            except Exception:
                pass
        
        # Upload new image
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"theme_id": theme_id, "type": "theme_background", "content_type": content_type}
        )
        
        await db.themes.update_one(
            {"id": theme_id},
            {"$set": {
                "backgroundImageFileId": str(file_id),
                "backgroundImageUrl": f"/api/themes/{theme_id}/background-image",
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        
        return {"success": True, "backgroundImageUrl": f"/api/themes/{theme_id}/background-image?v={datetime.now(timezone.utc).timestamp()}"}
    except Exception as e:
        logger.error(f"Error uploading theme background: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@admin_router.post("/bundles/{bundle_id}/upload-background")
async def upload_bundle_background(
    bundle_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload background image for a bundle"""
    from bson import ObjectId
    
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"bundle_bg_{bundle_id}{ext}"
        
        # Delete old image if exists
        if bundle.get('backgroundImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(bundle['backgroundImageFileId']))
            except Exception:
                pass
        
        # Upload new image
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"bundle_id": bundle_id, "type": "bundle_background", "content_type": content_type}
        )
        
        await db.bundles.update_one(
            {"id": bundle_id},
            {"$set": {
                "backgroundImageFileId": str(file_id),
                "backgroundImageUrl": f"/api/bundles/{bundle_id}/background-image",
                "updatedAt": datetime.now(timezone.utc)
            }}
        )

        fire_variants(file_id)

        return {"success": True, "backgroundImageUrl": f"/api/bundles/{bundle_id}/background-image"}
    except Exception as e:
        logger.error(f"Error uploading bundle background: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@admin_router.post("/bundles/{bundle_id}/upload-pdf")
async def upload_bundle_pdf(
    bundle_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload PDF for a bundle"""
    from bson import ObjectId
    
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Solo file PDF permessi")
    
    try:
        content = await file.read()
        filename = f"bundle_{bundle_id}.pdf"
        
        # Delete old PDF if exists
        if bundle.get('pdfFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(bundle['pdfFileId']))
            except Exception:
                pass
        
        # Upload new PDF
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"bundle_id": bundle_id, "type": "bundle_pdf", "content_type": "application/pdf"}
        )
        
        await db.bundles.update_one(
            {"id": bundle_id},
            {"$set": {
                "pdfFileId": str(file_id),
                "pdfUrl": f"/api/bundles/{bundle_id}/download",
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        
        return {"success": True, "pdfUrl": f"/api/bundles/{bundle_id}/download"}
    except Exception as e:
        logger.error(f"Error uploading bundle PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@api_router.get("/bundles/{bundle_id}/background-image")
async def get_bundle_background_image(bundle_id: str, request: Request):
    """Serve bundle background image (true streaming + ETag)."""
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle or not bundle.get('backgroundImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=bundle['backgroundImageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )

@api_router.get("/bundles/{bundle_id}/download")
async def download_bundle_pdf_legacy(bundle_id: str, request: Request):
    """Download bundle PDF (legacy - manual upload)"""
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    if not bundle.get('pdfFileId'):
        raise HTTPException(status_code=404, detail="PDF non disponibile per questo bundle")

    safe_title = bundle.get('title', 'bundle').replace(' ', '_')
    filename = f"Poppiconni_{safe_title}.pdf"
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=bundle['pdfFileId'],
        request=request,
        fallback_content_type="application/pdf",
        cache_control="no-cache",
        filename=filename,
        as_attachment=True,
        not_found_detail="PDF non disponibile per questo bundle",
    )


def calculate_bundle_hash(bundle: dict, illustrations: list) -> str:
    """Calculate hash for bundle PDF cache validation"""
    hash_data = {
        "illustrationIds": bundle.get('illustrationIds', []),
        "files": []
    }
    for illust in illustrations:
        hash_data["files"].append({
            "id": illust.get('id'),
            "pdfFileId": illust.get('pdfFileId'),
            "imageFileId": illust.get('imageFileId')
        })
    hash_string = str(sorted(hash_data.items()))
    return hashlib.md5(hash_string.encode()).hexdigest()


def slugify_bundle_title(title: str) -> str:
    """Generate safe slug for bundle filename (mobile-friendly)"""
    # Lowercase
    slug = title.lower()
    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')
    # Keep only [a-z0-9-]
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Reduce multiple hyphens to single
    slug = re.sub(r'-+', '-', slug)
    # Trim hyphens at start/end
    slug = slug.strip('-')
    # Fallback if empty
    return slug if slug else 'bundle'


def generate_bundle_filename(title: str, page_count: int) -> str:
    """Generate clean filename: Poppiconni_Bundle-{slug}-{pages}p.pdf"""
    slug = slugify_bundle_title(title)
    return f"Poppiconni_Bundle-{slug}-{page_count}p.pdf"


async def check_free_bundle_rate_limit(ip: str, bundle_id: str, pdf_hash: str) -> bool:
    """
    Check rate limit for free bundle downloads.
    Returns True if download is allowed, False if limit reached.
    Limit: max 2 downloads per IP + bundleId + hash combination.
    """
    rate_limit_key = f"{ip}_{bundle_id}_{pdf_hash}"
    
    # Find existing record
    record = await db.download_limits.find_one({"key": rate_limit_key})
    
    if record:
        # Check if limit reached (block at count >= 2)
        if record.get('count', 0) >= 2:
            logger.warning(f"Rate limit reached for {rate_limit_key}")
            return False
        
        # Increment counter
        await db.download_limits.update_one(
            {"key": rate_limit_key},
            {
                "$inc": {"count": 1},
                "$set": {
                    "lastDownload": datetime.now(timezone.utc),
                    "expiresAt": datetime.now(timezone.utc) + timedelta(days=30)
                }
            }
        )
    else:
        # Create new record with TTL
        await db.download_limits.insert_one({
            "key": rate_limit_key,
            "ip": ip,
            "bundleId": bundle_id,
            "pdfHash": pdf_hash,
            "count": 1,
            "createdAt": datetime.now(timezone.utc),
            "lastDownload": datetime.now(timezone.utc),
            "expiresAt": datetime.now(timezone.utc) + timedelta(days=30)
        })
    
    return True


async def generate_bundle_pdf(bundle: dict) -> bytes:
    """Generate a merged PDF from bundle illustrations"""
    from bson import ObjectId
    
    illustration_ids = bundle.get('illustrationIds', [])
    if not illustration_ids:
        raise HTTPException(status_code=400, detail="Bundle senza illustrazioni selezionate")
    
    # Fetch all illustrations in order
    illustrations = []
    for illust_id in illustration_ids:
        illust = await db.illustrations.find_one({"id": illust_id}, {"_id": 0})
        if illust:
            illustrations.append(illust)
    
    if not illustrations:
        raise HTTPException(status_code=400, detail="Nessuna illustrazione trovata per questo bundle")
    
    # Merge PDFs
    merger = PdfMerger()
    pages_added = 0
    
    for illust in illustrations:
        pdf_file_id = illust.get('pdfFileId')
        image_file_id = illust.get('imageFileId')
        
        try:
            if pdf_file_id:
                # Use existing PDF
                grid_out = await gridfs_bucket.open_download_stream(ObjectId(pdf_file_id))
                pdf_content = await grid_out.read()
                merger.append(io.BytesIO(pdf_content))
                pages_added += 1
                logger.info(f"Added PDF for illustration {illust.get('id')}")
                
            elif image_file_id:
                # Convert image to PDF
                grid_out = await gridfs_bucket.open_download_stream(ObjectId(image_file_id))
                image_content = await grid_out.read()
                
                # Create PDF from image using reportlab
                img = PILImage.open(io.BytesIO(image_content))
                img_width, img_height = img.size
                
                # Calculate page size to fit image (A4 or image aspect ratio)
                page_width, page_height = A4
                scale = min(page_width / img_width, page_height / img_height)
                scaled_width = img_width * scale
                scaled_height = img_height * scale
                
                # Create PDF with image
                pdf_buffer = io.BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=A4)
                
                # Center image on page
                x = (page_width - scaled_width) / 2
                y = (page_height - scaled_height) / 2
                
                # Save image temporarily for reportlab
                temp_img_buffer = io.BytesIO()
                img.save(temp_img_buffer, format='PNG')
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
                logger.warning(f"Illustration {illust.get('id')} has no PDF or image file, skipping")
                
        except Exception as e:
            logger.error(f"Error processing illustration {illust.get('id')}: {str(e)}")
            continue
    
    if pages_added == 0:
        raise HTTPException(status_code=400, detail="Bundle senza file scaricabili. Nessuna illustrazione ha PDF o immagini caricate.")
    
    # Output merged PDF
    output_buffer = io.BytesIO()
    merger.write(output_buffer)
    merger.close()
    output_buffer.seek(0)
    
    logger.info(f"Generated bundle PDF with {pages_added} pages")
    return output_buffer.read()


@api_router.get("/bundles/{bundle_id}/download-pdf")
async def download_bundle_generated_pdf(bundle_id: str, request: Request):
    """Download auto-generated bundle PDF (merged from illustrations)"""
    from bson import ObjectId
    
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    
    # Access control for paid bundles
    if not bundle.get('isFree', False):
        # For paid bundles, check Stripe purchase (future implementation)
        # For now, block paid bundles
        raise HTTPException(status_code=403, detail="Acquisto richiesto. Pagamenti non ancora attivi.")
    
    illustration_ids = bundle.get('illustrationIds', [])
    if not illustration_ids:
        raise HTTPException(status_code=400, detail="Bundle senza illustrazioni. Contatta l'amministratore.")
    
    # Fetch illustrations to calculate hash
    illustrations = []
    for illust_id in illustration_ids:
        illust = await db.illustrations.find_one({"id": illust_id}, {"_id": 0})
        if illust:
            illustrations.append(illust)
    
    current_hash = calculate_bundle_hash(bundle, illustrations)
    page_count = len(illustrations)
    
    # Get client IP for rate limiting
    client_ip = request.client.host if request.client else "unknown"
    # Check for proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Rate limit check for free bundles (max 2 downloads per IP + bundle + hash)
    is_allowed = await check_free_bundle_rate_limit(client_ip, bundle_id, current_hash)
    if not is_allowed:
        raise HTTPException(
            status_code=429, 
            detail="Limite download gratuito raggiunto per questo bundle"
        )
    
    # Generate clean filename
    filename = generate_bundle_filename(bundle.get('title', 'bundle'), page_count)
    
    # Check cache
    if bundle.get('generatedPdfFileId') and bundle.get('generatedPdfHash') == current_hash:
        logger.info(f"Serving cached PDF for bundle {bundle_id}")
        try:
            return await stream_gridfs_response(
                gridfs_bucket=gridfs_bucket,
                file_id=bundle['generatedPdfFileId'],
                request=request,
                fallback_content_type="application/pdf",
                cache_control="no-cache",
                filename=filename,
                as_attachment=True,
                not_found_detail="PDF cache non disponibile",
            )
        except Exception as e:
            logger.warning(f"Cache miss, regenerating PDF: {str(e)}")
    
    # Generate new PDF
    try:
        pdf_content = await generate_bundle_pdf(bundle)
        
        # Delete old cached PDF if exists
        if bundle.get('generatedPdfFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(bundle['generatedPdfFileId']))
            except:
                pass
        
        # Store new cached PDF in GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(pdf_content),
            metadata={"bundle_id": bundle_id, "content_type": "application/pdf"}
        )
        
        # Update bundle with new cache
        await db.bundles.update_one(
            {"id": bundle_id},
            {"$set": {
                "generatedPdfFileId": str(file_id),
                "generatedPdfHash": current_hash,
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"Generated and cached new PDF for bundle {bundle_id}")
        
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating bundle PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore nella generazione del PDF: {str(e)}")

@admin_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form("image"),
    email: str = Depends(verify_token)
):
    """Upload file to GridFS for persistent storage"""
    from bson import ObjectId
    
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

@admin_router.post("/illustrations/{illustration_id}/attach-pdf")
async def attach_pdf_to_illustration(
    illustration_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload and attach a PDF file directly to an illustration"""
    from bson import ObjectId
    
    # Verify illustration exists
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Solo file PDF sono permessi")
    
    try:
        # Read file content
        content = await file.read()
        
        # Generate filename based on illustration title
        safe_title = illust.get('title', illustration_id).replace(' ', '_').replace('"', '').replace("'", "")
        unique_filename = f"pompiconni_{safe_title}.pdf"
        
        # Delete old PDF if exists
        old_file_id = illust.get('pdfFileId')
        if old_file_id:
            try:
                await gridfs_bucket.delete(ObjectId(old_file_id))
            except Exception:
                pass  # Old file might not exist
        
        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(content),
            metadata={
                "illustration_id": illustration_id,
                "original_filename": file.filename,
                "file_type": "pdf",
                "content_type": "application/pdf",
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Update illustration with file ID
        await db.illustrations.update_one(
            {"id": illustration_id},
            {
                "$set": {
                    "pdfFileId": str(file_id),
                    "pdfUrl": f"/api/illustrations/{illustration_id}/download",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        # Ricalcola conteggi (ora l'illustrazione è scaricabile)
        await recalculate_theme_count(illust.get('themeId'))
        await recalculate_bundle_counts()
        
        return {
            "success": True,
            "fileId": str(file_id),
            "message": "PDF caricato e collegato all'illustrazione"
        }
        
    except Exception as e:
        logger.error(f"Error attaching PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento del PDF")

@admin_router.post("/illustrations/{illustration_id}/attach-image")
async def attach_image_to_illustration(
    illustration_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload and attach an image file (jpg, jpeg, png) to an illustration"""
    from bson import ObjectId
    
    # Verify illustration exists
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    allowed_extensions = [".jpg", ".jpeg", ".png"]
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Solo file immagine sono permessi: {', '.join(allowed_extensions)}")
    
    # Determine content type
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png"
    }
    content_type = content_types.get(ext, "image/jpeg")
    
    try:
        # Read file content
        content = await file.read()
        
        # Generate filename based on illustration title
        safe_title = illust.get('title', illustration_id).replace(' ', '_').replace('"', '').replace("'", "")
        unique_filename = f"pompiconni_{safe_title}{ext}"
        
        # Delete old image if exists
        old_file_id = illust.get('imageFileId')
        if old_file_id:
            try:
                await gridfs_bucket.delete(ObjectId(old_file_id))
            except Exception:
                pass  # Old file might not exist
        
        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(content),
            metadata={
                "illustration_id": illustration_id,
                "original_filename": file.filename,
                "file_type": "image",
                "content_type": content_type,
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Update illustration with image file ID and URL
        await db.illustrations.update_one(
            {"id": illustration_id},
            {
                "$set": {
                    "imageFileId": str(file_id),
                    "imageUrl": f"/api/illustrations/{illustration_id}/image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        # Ricalcola conteggi (ora l'illustrazione è scaricabile)
        await recalculate_theme_count(illust.get('themeId'))
        await recalculate_bundle_counts()

        # Fire-and-forget: generate responsive variants for this image
        fire_variants(file_id)

        return {
            "success": True,
            "fileId": str(file_id),
            "imageUrl": f"/api/illustrations/{illustration_id}/image",
            "message": "Immagine caricata e collegata all'illustrazione"
        }
        
    except Exception as e:
        logger.error(f"Error attaching image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento dell'immagine")

@admin_router.post("/generate-illustration")
async def generate_illustration(request: GenerateRequest, email: str = Depends(verify_token)):
    """Generate AI illustration and save to GridFS"""
    from bson import ObjectId
    
    try:
        from emergentintegrations.llm.openai.image_generation import OpenAIImageGeneration
        
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="API key non configurata")
        
        # Build the prompt for coloring book style
        style_prompts = {
            "lineart": "simple black and white line art coloring book page for children, thick clean outlines, no shading, no colors, white background, cute kawaii style",
            "sketch": "pencil sketch style drawing, light lines, suitable for tracing, cute cartoon style",
            "colored": "cute colorful illustration for children, soft pastel colors, kawaii style"
        }
        
        full_prompt = f"Poppiconni the cute clumsy unicorn with big eyes, rosy cheeks, rainbow horn, fluffy mane: {request.prompt}. Style: {style_prompts.get(request.style, style_prompts['lineart'])}"
        
        logger.info(f"Generating image with prompt: {full_prompt[:100]}...")
        
        image_gen = OpenAIImageGeneration(api_key=api_key)
        images = await image_gen.generate_images(
            prompt=full_prompt,
            model="gpt-image-1",
            number_of_images=1
        )
        
        if not images or len(images) == 0:
            raise HTTPException(status_code=500, detail="Nessuna immagine generata")
        
        # Create illustration record first to get ID
        illustration_id = str(uuid.uuid4())
        safe_prompt = request.prompt[:30].replace(' ', '_').replace('"', '').replace("'", "")
        unique_filename = f"ai_pompiconni_{safe_prompt}_{illustration_id[:8]}.png"
        
        # Save to GridFS for persistent storage
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
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Convert to base64 for immediate preview
        image_base64 = base64.b64encode(images[0]).decode('utf-8')
        
        # Create illustration record with GridFS reference
        illust_dict = {
            'id': illustration_id,
            'themeId': request.themeId if request.themeId else None,
            'title': f"Poppiconni - {request.prompt[:30]}",
            'description': request.prompt,
            'imageUrl': f"/api/illustrations/{illustration_id}/image",
            'imageFileId': str(file_id),
            'imageContentType': "image/png",
            'imageOriginalFilename': unique_filename,
            'pdfUrl': None,
            'pdfFileId': None,
            'isFree': True,
            'price': 0,
            'downloadCount': 0,
            'generatedByAI': True,
            'aiPrompt': request.prompt,
            'aiStyle': request.style,
            'createdAt': datetime.now(timezone.utc),
            'updatedAt': datetime.now(timezone.utc)
        }
        await db.illustrations.insert_one(illust_dict)
        
        # Update theme illustration count if theme provided
        if request.themeId:
            await db.themes.update_one(
                {"id": request.themeId},
                {"$inc": {"illustrationCount": 1}}
            )
        
        # Remove _id for response
        illust_dict.pop('_id', None)
        
        return {
            "success": True,
            "imageUrl": f"/api/illustrations/{illustration_id}/image",
            "imageBase64": image_base64,
            "illustration": illust_dict,
            "message": "Illustrazione generata e salvata con successo"
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Libreria AI non installata")
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore generazione: {str(e)}")

# ============== ADMIN REVIEWS & SETTINGS ==============

# Admin reviews CRUD moved to `api/admin/reviews.py` (Fase 4C).

# Admin maintenance endpoints (`/maintenance/fix-brand-name`,
# `/download-stats`, `/reset-fake-counters`) moved to
# `api/admin/maintenance.py` (Auth & Maintenance mini-batch).

# Admin /settings GET+PUT moved to `api/admin/site_settings.py` (Fase 4C).

# ============== HERO IMAGE & SITE SETTINGS ==============

@api_router.get("/site/hero-image")
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

@api_router.get("/site/hero-status")
async def get_hero_status():
    """Check if hero image is configured"""
    settings = await db.site_settings.find_one({"id": "global"})
    has_hero = bool(settings and settings.get('heroImageFileId'))
    return {
        "hasHeroImage": has_hero,
        "heroImageUrl": "/api/site/hero-image" if has_hero else None,
        "updatedAt": settings.get('heroImageUpdatedAt') if settings else None
    }

@admin_router.post("/site/hero-image")
async def upload_hero_image(
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload or replace hero image"""
    from bson import ObjectId
    
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    allowed_extensions = [".jpg", ".jpeg", ".png"]
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Solo file immagine sono permessi: {', '.join(allowed_extensions)}")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        unique_filename = f"hero_pompiconni_{uuid.uuid4()}{ext}"
        
        # Delete old hero image if exists
        settings = await db.site_settings.find_one({"id": "global"})
        if settings and settings.get('heroImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(settings['heroImageFileId']))
            except Exception:
                pass
        
        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            unique_filename,
            io.BytesIO(content),
            metadata={
                "type": "hero_image",
                "original_filename": file.filename,
                "content_type": content_type,
                "uploaded_by": email,
                "uploaded_at": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Update site settings
        await db.site_settings.update_one(
            {"id": "global"},
            {
                "$set": {
                    "heroImageFileId": str(file_id),
                    "heroImageContentType": content_type,
                    "heroImageFileName": file.filename,
                    "heroImageUpdatedAt": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )

        # Fire-and-forget: generate responsive variants for hero
        fire_variants(file_id)

        return {
            "success": True,
            "heroImageUrl": "/api/site/hero-image",
            "message": "Hero image aggiornata con successo"
        }
        
    except Exception as e:
        logger.error(f"Error uploading hero image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento dell'immagine")

@admin_router.delete("/site/hero-image")
async def delete_hero_image(email: str = Depends(verify_token)):
    """Delete hero image (restore to default)"""
    from bson import ObjectId
    
    settings = await db.site_settings.find_one({"id": "global"})
    if settings and settings.get('heroImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(settings['heroImageFileId']))
        except Exception:
            pass
        
        await db.site_settings.update_one(
            {"id": "global"},
            {
                "$unset": {
                    "heroImageFileId": "",
                    "heroImageContentType": "",
                    "heroImageFileName": "",
                    "heroImageUpdatedAt": ""
                }
            }
        )
    
    return {"success": True, "message": "Hero image rimossa, ripristinato default"}

# ============== BRAND LOGO ==============

@api_router.get("/site/brand-logo")
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

@admin_router.get("/brand-logo-status")
async def get_brand_logo_status(email: str = Depends(verify_token)):
    """Get brand logo status"""
    settings = await db.site_settings.find_one({"id": "global"})
    has_logo = bool(settings and settings.get('brandLogoFileId'))
    return {
        "hasBrandLogo": has_logo,
        "brandLogoUrl": "/api/site/brand-logo" if has_logo else None
    }

@admin_router.post("/upload-brand-logo")
async def upload_brand_logo(
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload brand logo image"""
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"brand_logo{ext}"
        
        settings = await db.site_settings.find_one({"id": "global"})
        
        # Delete old logo if exists
        if settings and settings.get('brandLogoFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(settings['brandLogoFileId']))
            except Exception:
                pass
        
        # Upload new logo
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"type": "brand_logo", "content_type": content_type}
        )
        
        await db.site_settings.update_one(
            {"id": "global"},
            {
                "$set": {
                    "brandLogoFileId": str(file_id),
                    "brandLogoContentType": content_type,
                    "brandLogoUpdatedAt": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )

        # Fire-and-forget: generate responsive variants for the brand logo
        fire_variants(file_id)

        return {"success": True, "brandLogoUrl": f"/api/site/brand-logo?v={datetime.now(timezone.utc).timestamp()}"}
    except Exception as e:
        logger.error(f"Error uploading brand logo: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@admin_router.delete("/brand-logo")
async def delete_brand_logo(email: str = Depends(verify_token)):
    """Delete brand logo"""
    settings = await db.site_settings.find_one({"id": "global"})
    
    if settings and settings.get('brandLogoFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(settings['brandLogoFileId']))
        except Exception:
            pass
        
        await db.site_settings.update_one(
            {"id": "global"},
            {"$set": {"brandLogoFileId": "", "brandLogoContentType": "", "brandLogoUpdatedAt": ""}}
        )
    
    return {"success": True}

# ============== SOCIAL LINKS ==============

@admin_router.put("/social-links")
async def update_social_links(
    instagramUrl: str = "",
    tiktokUrl: str = "",
    email: str = Depends(verify_token)
):
    """Update social media links"""
    return await settings_service.update_social_links(instagramUrl, tiktokUrl)

@api_router.get("/theme-colors")
async def get_theme_color_palette():
    """Get available theme colors"""
    return THEME_COLOR_PALETTE

# ============== ENHANCED THEME CRUD ==============

# Admin themes check-delete + DELETE moved to `api/admin/themes.py` (Fase 4C).

@admin_router.put("/illustrations/{illustration_id}/theme")
async def change_illustration_theme(
    illustration_id: str, 
    theme_id: Optional[str] = None,
    email: str = Depends(verify_token)
):
    """Change or remove theme assignment for an illustration"""
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    old_theme_id = illust.get('themeId')
    
    # Validate new theme exists if provided
    if theme_id:
        theme = await db.themes.find_one({"id": theme_id})
        if not theme:
            raise HTTPException(status_code=404, detail="Nuovo tema non trovato")
    
    # Update illustration
    await db.illustrations.update_one(
        {"id": illustration_id},
        {"$set": {"themeId": theme_id, "updatedAt": datetime.now(timezone.utc)}}
    )
    
    # Update theme counters
    if old_theme_id:
        await db.themes.update_one({"id": old_theme_id}, {"$inc": {"illustrationCount": -1}})
    if theme_id:
        await db.themes.update_one({"id": theme_id}, {"$inc": {"illustrationCount": 1}})
    
    return {"success": True, "message": "Tema aggiornato"}

# ============== BOOKS PUBLIC ENDPOINTS ==============

# Public `/books`, `/books/{id}` and reading-progress endpoints moved to
# `api/public/books.py` (Fase 4C). The GridFS scene/cover image streams
# and PDF generation stay below.

@api_router.get("/books/{book_id}/scene/{scene_number}/colored-image")
async def get_scene_colored_image(book_id: str, scene_number: int, request: Request):
    """Serve colored image for a scene (true streaming + ETag)."""
    scene = await db.book_scenes.find_one({"bookId": book_id, "sceneNumber": scene_number})
    if not scene or not scene.get('coloredImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=scene['coloredImageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=31536000, immutable",
        not_found_detail="Immagine non trovata",
    )

@api_router.get("/books/{book_id}/scene/{scene_number}/lineart-image")
async def get_scene_lineart_image(book_id: str, scene_number: int, request: Request):
    """Serve line art image for a scene (true streaming + ETag)."""
    scene = await db.book_scenes.find_one({"bookId": book_id, "sceneNumber": scene_number})
    if not scene or not scene.get('lineArtImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=scene['lineArtImageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=31536000, immutable",
        not_found_detail="Immagine non trovata",
    )

@api_router.get("/books/{book_id}/cover")
async def get_book_cover(
    book_id: str,
    request: Request,
    w: Optional[int] = None,
    format: Optional[str] = None,
):
    """Serve book cover image (streaming + ETag + responsive variants)."""
    book = await db.books.find_one({"id": book_id})
    if not book or not book.get('coverImageFileId'):
        raise HTTPException(status_code=404, detail="Copertina non disponibile")
    return await stream_gridfs_response_with_variants(
        db=db,
        gridfs_bucket=gridfs_bucket,
        original_file_id=book['coverImageFileId'],
        request=request,
        size_param=w,
        format_param=format,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Copertina non trovata",
    )

# Reading Progress endpoints moved to `api/public/books.py` (Fase 4C).

# ============== BOOK PDF DOWNLOAD ==============

async def get_gridfs_image(file_id: str) -> bytes:
    """Helper function to get image bytes from GridFS"""
    from bson import ObjectId
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(file_id))
        return await grid_out.read()
    except Exception as e:
        logger.error(f"Error reading GridFS file {file_id}: {e}")
        raise

@api_router.get("/books/{book_id}/pdf")
async def download_book_pdf_public(book_id: str):
    """
    Download PDF for a FREE book (public access).
    Premium books cannot be downloaded without payment.
    """
    # Get book
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    
    # Check visibility
    if not book.get('isVisible', True):
        raise HTTPException(status_code=404, detail="Libro non disponibile")
    
    # Check if free
    if not book.get('isFree', True):
        raise HTTPException(status_code=403, detail="Pagamenti non ancora attivi. Questo libro è premium.")
    
    # Check if download is allowed
    if not book.get('allowDownload', True):
        raise HTTPException(status_code=403, detail="Download non abilitato per questo libro")
    
    # Get scenes
    scenes = await db.book_scenes.find({"bookId": book_id}).sort("sceneNumber", 1).to_list(MAX_SCENES_PER_BOOK)
    if not scenes:
        raise HTTPException(status_code=404, detail="Questo libro non ha ancora scene")
    
    # Generate PDF
    try:
        pdf_buffer = await generate_book_pdf(book, scenes, get_gridfs_image)
        
        # Increment download count
        await db.books.update_one({"id": book_id}, {"$inc": {"downloadCount": 1}})
        
        # Create filename
        filename = f"poppiconni_{book_id}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"Error generating PDF for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Errore nella generazione del PDF")

# ============== BOOKS ADMIN ENDPOINTS ==============

# Admin books CRUD + scenes CRUD moved to `api/admin/books.py` (Fase 4C).
# Heavy GridFS routes (cover upload, scene image upload, PDF generation)
# stay below.

@admin_router.get("/books/{book_id}/pdf")
async def admin_download_book_pdf(book_id: str, email: str = Depends(verify_token)):
    """
    Download PDF for ANY book (admin access).
    Admin can download both free and premium books for preview/testing.
    """
    # Get book
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    
    # Get scenes
    scenes = await db.book_scenes.find({"bookId": book_id}).sort("sceneNumber", 1).to_list(MAX_SCENES_PER_BOOK)
    if not scenes:
        raise HTTPException(status_code=404, detail="Questo libro non ha ancora scene")
    
    # Generate PDF
    try:
        pdf_buffer = await generate_book_pdf(book, scenes, get_gridfs_image)
        
        # Create filename
        filename = f"poppiconni_{book_id}.pdf"
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"Error generating PDF for book {book_id}: {e}")
        raise HTTPException(status_code=500, detail="Errore nella generazione del PDF")

@admin_router.post("/books/{book_id}/cover")
async def admin_upload_book_cover(
    book_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload book cover image"""
    from bson import ObjectId
    
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"book_cover_{book_id}{ext}"
        
        # Delete old cover if exists
        if book.get('coverImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(book['coverImageFileId']))
            except Exception:
                pass
        
        # Upload to GridFS
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"book_id": book_id, "type": "cover", "content_type": content_type}
        )
        
        # Update book
        await db.books.update_one(
            {"id": book_id},
            {
                "$set": {
                    "coverImageFileId": str(file_id),
                    "coverImageUrl": f"/api/books/{book_id}/cover",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        fire_variants(file_id)

        return {"success": True, "coverUrl": f"/api/books/{book_id}/cover"}
    except Exception as e:
        logger.error(f"Error uploading book cover: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

# ============== BOOK SCENES ADMIN ==============

# Admin scenes CRUD (list/create/update/delete metadata) moved to
# `api/admin/books.py` (Fase 4C). Scene image upload routes stay below.

@admin_router.post("/books/{book_id}/scenes/{scene_id}/colored-image")
async def admin_upload_scene_colored_image(
    book_id: str,
    scene_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload colored image for a scene"""
    from bson import ObjectId
    
    scene = await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"scene_colored_{scene_id}{ext}"
        
        # Delete old image
        if scene.get('coloredImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(scene['coloredImageFileId']))
            except Exception:
                pass
        
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"scene_id": scene_id, "type": "colored", "content_type": content_type}
        )
        
        await db.book_scenes.update_one(
            {"id": scene_id},
            {
                "$set": {
                    "coloredImageFileId": str(file_id),
                    "coloredImageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/colored-image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        return {"success": True, "imageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/colored-image"}
    except Exception as e:
        logger.error(f"Error uploading colored image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@admin_router.post("/books/{book_id}/scenes/{scene_id}/lineart-image")
async def admin_upload_scene_lineart_image(
    book_id: str,
    scene_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload line art image for a scene"""
    from bson import ObjectId
    
    scene = await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"scene_lineart_{scene_id}{ext}"
        
        # Delete old image
        if scene.get('lineArtImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(scene['lineArtImageFileId']))
            except Exception:
                pass
        
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={"scene_id": scene_id, "type": "lineart", "content_type": content_type}
        )
        
        await db.book_scenes.update_one(
            {"id": scene_id},
            {
                "$set": {
                    "lineArtImageFileId": str(file_id),
                    "lineArtImageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/lineart-image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        return {"success": True, "imageUrl": f"/api/books/{book_id}/scene/{scene['sceneNumber']}/lineart-image"}
    except Exception as e:
        logger.error(f"Error uploading lineart image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

# ============== POPPICONNI MULTI-AI PIPELINE ==============

from image_pipeline import (
    run_pipeline, run_async_retry, PipelineStatus, QCResult,
    MAX_REFERENCE_IMAGES_PER_USER
)

@admin_router.get("/styles")
async def get_generation_styles(email: str = Depends(verify_token)):
    """Get all generation styles for the current user"""
    styles = await db.generation_styles.find(
        {"userId": email},
        {"_id": 0}
    ).to_list(MAX_REFERENCE_IMAGES_PER_USER + 10)
    return {
        "styles": styles,
        "count": len(styles),
        "limit": MAX_REFERENCE_IMAGES_PER_USER
    }

@admin_router.post("/styles")
async def create_generation_style(
    style: GenerationStyleCreate,
    email: str = Depends(verify_token)
):
    """Create a new generation style (reference image library)"""
    # Check limit
    count = await db.generation_styles.count_documents({"userId": email})
    if count >= MAX_REFERENCE_IMAGES_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Limite raggiunto: massimo {MAX_REFERENCE_IMAGES_PER_USER} stili per utente"
        )
    
    style_dict = {
        "id": str(uuid.uuid4()),
        "userId": email,
        "styleName": style.styleName,
        "description": style.description,
        "isActive": style.isActive,
        "referenceImageFileId": None,
        "referenceImageUrl": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.generation_styles.insert_one(style_dict)
    style_dict.pop('_id', None)
    
    return {"success": True, "style": style_dict}

@admin_router.delete("/styles/{style_id}")
async def delete_generation_style(style_id: str, email: str = Depends(verify_token)):
    """Delete a generation style and its reference image"""
    from bson import ObjectId
    
    style = await db.generation_styles.find_one({"id": style_id, "userId": email})
    if not style:
        raise HTTPException(status_code=404, detail="Stile non trovato")
    
    # Delete reference image from GridFS if exists
    if style.get('referenceImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(style['referenceImageFileId']))
        except Exception:
            pass
    
    await db.generation_styles.delete_one({"id": style_id})
    return {"success": True}

@admin_router.post("/styles/{style_id}/upload-reference")
async def upload_style_reference(
    style_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload reference image for a generation style"""
    from bson import ObjectId
    
    style = await db.generation_styles.find_one({"id": style_id, "userId": email})
    if not style:
        raise HTTPException(status_code=404, detail="Stile non trovato")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"style_reference_{style_id}{ext}"
        
        # Delete old reference if exists
        if style.get('referenceImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(style['referenceImageFileId']))
            except Exception:
                pass
        
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "style_id": style_id,
                "type": "style_reference",
                "content_type": content_type,
                "uploaded_by": email
            }
        )
        
        await db.generation_styles.update_one(
            {"id": style_id},
            {
                "$set": {
                    "referenceImageFileId": str(file_id),
                    "referenceImageUrl": f"/api/admin/styles/{style_id}/reference-image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        return {
            "success": True,
            "imageUrl": f"/api/admin/styles/{style_id}/reference-image"
        }
    except Exception as e:
        logger.error(f"Error uploading style reference: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@admin_router.get("/styles/{style_id}/reference-image")
async def get_style_reference_image(style_id: str, request: Request, email: str = Depends(verify_token)):
    """Serve reference image for a style (true streaming + ETag)."""
    style = await db.generation_styles.find_one({"id": style_id, "userId": email})
    if not style or not style.get('referenceImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine di riferimento non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=style['referenceImageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="private, max-age=3600",
        not_found_detail="Immagine di riferimento non trovata",
    )

@admin_router.post("/generate-poppiconni", response_model=PoppiconniGenerateResponse)
async def generate_poppiconni_illustration(
    request: PoppiconniGenerateRequest,
    background_tasks: BackgroundTasks,
    email: str = Depends(verify_token)
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
    from bson import ObjectId
    
    # Get reference image - prioritize direct upload, then style library
    reference_image_base64 = None
    
    # 1. First check if direct reference image was uploaded
    if request.reference_image_base64:
        reference_image_base64 = request.reference_image_base64
        logger.info("Using directly uploaded reference image for style analysis")
    # 2. Otherwise, check style library
    elif request.style_id:
        style = await db.generation_styles.find_one({"id": request.style_id, "userId": email})
        if style and style.get('referenceImageFileId'):
            try:
                grid_out = await gridfs_bucket.open_download_stream(
                    ObjectId(style['referenceImageFileId'])
                )
                content = await grid_out.read()
                reference_image_base64 = base64.b64encode(content).decode('utf-8')
                logger.info(f"Using reference image from style library: {style.get('styleName')}")
            except Exception as e:
                logger.warning(f"Could not load reference image from style: {e}")
    
    # Run the pipeline with reference image for style analysis
    try:
        result = await run_pipeline(
            user_request=request.user_request,
            reference_image_base64=reference_image_base64,
            style_lock=request.style_lock or bool(reference_image_base64),  # Auto-enable style lock if image provided
            user_id=email
        )
        
        illustration_id = None
        
        # Save to gallery if requested and pipeline succeeded
        if request.save_to_gallery and result.final_png_bytes:
            illustration_id = str(uuid.uuid4())
            safe_prompt = request.user_request[:30].replace(' ', '_').replace('"', '').replace("'", "")
            
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
            
            # Save PDF to GridFS
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
            await recalculate_bundle_counts()
        
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

@admin_router.get("/pipeline-status/{generation_id}")
async def get_pipeline_status(generation_id: str, email: str = Depends(verify_token)):
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

# ============== GAMES ENDPOINTS ==============

# --- PUBLIC GAMES ENDPOINTS ---

# Public `/games` list+detail moved to `api/public/games.py` (Fase 4C).
# GridFS thumbnail / card-image / page-image streams stay below.

@api_router.get("/games/{slug}/thumbnail")
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


# --- ADMIN GAMES ENDPOINTS ---

# Admin games CRUD (list/create/update/delete) moved to
# `api/admin/games.py` (Fase 4C). GridFS upload routes stay below.

@api_router.post("/admin/games/{game_id}/thumbnail")
async def upload_game_thumbnail(game_id: str, file: UploadFile = File(...), email: str = Depends(verify_token)):
    """Upload game thumbnail"""
    from bson import ObjectId
    
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Gioco non trovato")
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Tipo file non supportato")
    
    content = await file.read()
    
    # Delete old thumbnail if exists
    if game.get('thumbnailFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['thumbnailFileId']))
        except:
            pass
    
    # Upload new thumbnail
    file_id = await gridfs_bucket.upload_from_stream(
        f"game_thumbnail_{game['slug']}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "game_id": game_id}
    )
    
    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "thumbnailFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    fire_variants(file_id)

    return {"success": True, "thumbnailUrl": f"/api/games/{game['slug']}/thumbnail"}


# ============== GAME CARD IMAGE (for /giochi list page) ==============

@api_router.post("/admin/games/{game_id}/card-image")
async def upload_game_card_image(
    game_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload card image for game (used in /giochi list page)"""
    from bson import ObjectId
    
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Delete old card image if exists
    if game.get('cardImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['cardImageFileId']))
        except Exception:
            pass
    
    content = await file.read()
    file_id = await gridfs_bucket.upload_from_stream(
        f"game_card_{game_id}_{file.filename}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "game_id": game_id, "type": "card"}
    )
    
    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "cardImageFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    fire_variants(file_id)
    
    return {"success": True, "cardImageUrl": f"/api/games/{game['slug']}/card-image"}

@api_router.get("/games/{slug}/card-image")
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

@api_router.delete("/admin/games/{game_id}/card-image")
async def delete_game_card_image(
    game_id: str,
    email: str = Depends(verify_token)
):
    """Delete card image for game"""
    from bson import ObjectId
    
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Delete from GridFS
    if game.get('cardImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['cardImageFileId']))
        except Exception:
            pass
    
    # Clear DB fields (set to null)
    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "cardImageFileId": None,
            "cardImageUrl": None,
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    return {"success": True, "message": "Card image removed"}


# ============== GAME PAGE IMAGE (for /giochi/:slug detail page) ==============

@api_router.post("/admin/games/{game_id}/page-image")
async def upload_game_page_image(
    game_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload page background image for game (used in /giochi/:slug page)"""
    from bson import ObjectId
    
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Delete old page image if exists
    if game.get('pageImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['pageImageFileId']))
        except Exception:
            pass
    
    content = await file.read()
    file_id = await gridfs_bucket.upload_from_stream(
        f"game_page_{game_id}_{file.filename}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "game_id": game_id, "type": "page"}
    )
    
    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "pageImageFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )

    fire_variants(file_id)

    return {"success": True, "pageImageUrl": f"/api/games/{game['slug']}/page-image"}

@api_router.get("/games/{slug}/page-image")
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

@api_router.delete("/admin/games/{game_id}/page-image")
async def delete_game_page_image(
    game_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete page background image for game"""
    from bson import ObjectId
    verify_token(credentials.credentials)
    
    game = await db.games.find_one({"id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Delete from GridFS
    if game.get('pageImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(game['pageImageFileId']))
        except Exception:
            pass
    
    # Clear DB fields (set to null)
    await db.games.update_one(
        {"id": game_id},
        {"$set": {
            "pageImageFileId": None,
            "pageImageUrl": None,
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    return {"success": True, "message": "Page image removed"}


# ============== GAME LEVEL BACKGROUNDS (SFONDI LIVELLI) ==============

# Public `/games/bolle-magiche/level-backgrounds` list moved to
# `api/public/level_backgrounds.py` (Fase 4C). GridFS image stream stays
# below.

@api_router.get("/games/bolle-magiche/level-backgrounds/{bg_id}/image")
async def get_level_background_image(bg_id: str, request: Request):
    """Serve level background image from GridFS (true streaming + ETag)."""
    bg = await db.game_level_backgrounds.find_one({"id": bg_id})
    if not bg or not bg.get('backgroundImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=bg['backgroundImageFileId'],
        request=request,
        fallback_content_type="image/jpeg",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )

# --- ADMIN LEVEL BACKGROUNDS ---

# Admin list + update for level-backgrounds moved to
# `api/admin/level_backgrounds.py` (Fase 4C). Create / image-upload /
# delete keep GridFS calls inline and stay below.

@api_router.post("/admin/games/bolle-magiche/level-backgrounds")
async def admin_create_level_background(
    levelRangeStart: int = Form(...),
    levelRangeEnd: int = Form(...),
    backgroundOpacity: int = Form(30),
    backgroundImage: UploadFile = File(None),
    user_id: str = Depends(verify_token)
):
    """Admin: Create a new level background"""
    
    # Validate range
    if levelRangeStart >= levelRangeEnd:
        raise HTTPException(status_code=400, detail="levelRangeStart deve essere minore di levelRangeEnd")
    
    if levelRangeEnd - levelRangeStart != 4:
        raise HTTPException(status_code=400, detail="Il range deve essere di 5 livelli (es. 1-5, 6-10)")
    
    # Check for overlapping ranges
    existing = await db.game_level_backgrounds.find_one({
        "gameSlug": "bolle-magiche",
        "$or": [
            {"levelRangeStart": {"$lte": levelRangeEnd, "$gte": levelRangeStart}},
            {"levelRangeEnd": {"$lte": levelRangeEnd, "$gte": levelRangeStart}}
        ]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Esiste già uno sfondo per questo range di livelli")
    
    new_bg = {
        "id": str(uuid.uuid4()),
        "gameSlug": "bolle-magiche",
        "levelRangeStart": levelRangeStart,
        "levelRangeEnd": levelRangeEnd,
        "backgroundOpacity": backgroundOpacity,
        "backgroundImageFileId": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    # Upload image if provided
    if backgroundImage:
        content = await backgroundImage.read()
        file_id = await gridfs_bucket.upload_from_stream(
            f"level_bg_{levelRangeStart}_{levelRangeEnd}",
            io.BytesIO(content),
            metadata={"content_type": backgroundImage.content_type, "bg_id": new_bg["id"]}
        )
        new_bg["backgroundImageFileId"] = str(file_id)
    
    await db.game_level_backgrounds.insert_one(new_bg)
    
    result = {k: v for k, v in new_bg.items() if k != "_id"}
    if result.get('backgroundImageFileId'):
        result['backgroundImageUrl'] = f"/api/games/bolle-magiche/level-backgrounds/{result['id']}/image"
    
    return result

# Admin level-background PUT moved to `api/admin/level_backgrounds.py`
# (Fase 4C). Image upload + delete (with GridFS cleanup inline) stay
# below.

@api_router.post("/admin/games/bolle-magiche/level-backgrounds/{bg_id}/image")
async def admin_upload_level_background_image(
    bg_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(verify_token)
):
    """Admin: Upload/replace level background image"""
    from bson import ObjectId
    
    bg = await db.game_level_backgrounds.find_one({"id": bg_id})
    if not bg:
        raise HTTPException(status_code=404, detail="Sfondo non trovato")
    
    # Delete old image if exists
    if bg.get('backgroundImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(bg['backgroundImageFileId']))
        except Exception:
            pass
    
    # Upload new image
    content = await file.read()
    file_id = await gridfs_bucket.upload_from_stream(
        f"level_bg_{bg['levelRangeStart']}_{bg['levelRangeEnd']}",
        io.BytesIO(content),
        metadata={"content_type": file.content_type, "bg_id": bg_id}
    )
    
    await db.game_level_backgrounds.update_one(
        {"id": bg_id},
        {"$set": {
            "backgroundImageFileId": str(file_id),
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    return {"success": True, "backgroundImageUrl": f"/api/games/bolle-magiche/level-backgrounds/{bg_id}/image"}

@api_router.delete("/admin/games/bolle-magiche/level-backgrounds/{bg_id}")
async def admin_delete_level_background(
    bg_id: str,
    user_id: str = Depends(verify_token)
):
    """Admin: Delete a level background"""
    from bson import ObjectId

    bg = await level_background_service.get_raw_background(bg_id)

    # GridFS cleanup remains in server.py (Fase 4B Batch 2 scope).
    if bg.get('backgroundImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(bg['backgroundImageFileId']))
        except Exception:
            pass

    await db.game_level_backgrounds.delete_one({"id": bg_id})
    return {"success": True}


# ============== POSTER ENDPOINTS ==============

# --- PUBLIC POSTER ENDPOINTS ---

# Public `/posters` list+detail moved to `api/public/posters.py` (Fase 4C).
# GridFS image stream + PDF download stay below.

@api_router.get("/posters/{poster_id}/image")
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

@api_router.get("/posters/{poster_id}/download")
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

# --- ADMIN POSTER ENDPOINTS ---

# Admin posters CRUD + toggle-download + stats moved to
# `api/admin/posters.py` (Fase 4C). GridFS upload-image / upload-pdf
# routes stay below.

@admin_router.post("/posters/{poster_id}/upload-image")
async def admin_upload_poster_image(
    poster_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload preview image for a poster"""
    from bson import ObjectId
    
    poster = await db.posters.find_one({"id": poster_id})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Solo JPG, JPEG, PNG permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"poster_{poster_id}{ext}"
        
        # Delete old image if exists
        if poster.get('imageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(poster['imageFileId']))
            except Exception:
                pass
        
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "poster_id": poster_id,
                "type": "poster_image",
                "content_type": content_type
            }
        )
        
        await db.posters.update_one(
            {"id": poster_id},
            {
                "$set": {
                    "imageFileId": str(file_id),
                    "imageUrl": f"/api/posters/{poster_id}/image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )

        fire_variants(file_id)

        return {
            "success": True,
            "imageUrl": f"/api/posters/{poster_id}/image"
        }
    except Exception as e:
        logger.error(f"Error uploading poster image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@admin_router.post("/posters/{poster_id}/upload-pdf")
async def admin_upload_poster_pdf(
    poster_id: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload print-ready PDF for a poster"""
    from bson import ObjectId
    
    poster = await db.posters.find_one({"id": poster_id})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Solo file PDF permessi")
    
    try:
        content = await file.read()
        filename = f"poster_{poster_id}.pdf"
        
        # Delete old PDF if exists
        if poster.get('pdfFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(poster['pdfFileId']))
            except Exception:
                pass
        
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "poster_id": poster_id,
                "type": "poster_pdf",
                "content_type": "application/pdf"
            }
        )
        
        await db.posters.update_one(
            {"id": poster_id},
            {
                "$set": {
                    "pdfFileId": str(file_id),
                    "pdfUrl": f"/api/posters/{poster_id}/download",
                    "updatedAt": datetime.now(timezone.utc)
                }
            }
        )
        
        return {
            "success": True,
            "pdfUrl": f"/api/posters/{poster_id}/download"
        }
    except Exception as e:
        logger.error(f"Error uploading poster PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

# Admin posters stats moved to `api/admin/posters.py` (Fase 4C).

# ============== POPPICONNI CHARACTER IMAGES ==============

# Character traits with their images (for "Chi è Poppiconni?" section)
CHARACTER_TRAITS = ["dolce", "simpatico", "impacciato"]

@api_router.get("/character-images")
async def get_character_images():
    """Get all character trait images for public display"""
    images = await db.character_images.find({}, {"_id": 0}).to_list(10)
    # Return as dict for easy access
    result = {}
    for img in images:
        result[img['trait']] = img
    return result

@admin_router.get("/character-images")
async def admin_get_character_images(email: str = Depends(verify_token)):
    """Get all character trait images for admin"""
    images = await db.character_images.find({}, {"_id": 0}).to_list(10)
    # Ensure all traits exist
    existing_traits = {img['trait'] for img in images}
    for trait in CHARACTER_TRAITS:
        if trait not in existing_traits:
            images.append({
                "trait": trait,
                "imageFileId": None,
                "imageUrl": None
            })
    return images

@admin_router.post("/character-images/{trait}/upload")
async def admin_upload_character_image(
    trait: str,
    file: UploadFile = File(...),
    email: str = Depends(verify_token)
):
    """Upload image for a character trait (dolce, simpatico, impacciato)"""
    from bson import ObjectId
    
    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail=f"Trait must be one of: {CHARACTER_TRAITS}")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Solo JPG, PNG, WEBP permessi")
    
    content_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    content_type = content_types.get(ext, "image/png")
    
    try:
        content = await file.read()
        filename = f"character_{trait}{ext}"
        
        # Check if image already exists for this trait
        existing = await db.character_images.find_one({"trait": trait})
        if existing and existing.get('imageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(existing['imageFileId']))
            except Exception:
                pass
        
        # Upload new image
        file_id = await gridfs_bucket.upload_from_stream(
            filename,
            io.BytesIO(content),
            metadata={
                "trait": trait,
                "type": "character_image",
                "content_type": content_type
            }
        )
        
        # Upsert character image record
        await db.character_images.update_one(
            {"trait": trait},
            {
                "$set": {
                    "trait": trait,
                    "imageFileId": str(file_id),
                    "imageUrl": f"/api/character-images/{trait}/image",
                    "updatedAt": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )

        fire_variants(file_id)
        
        return {
            "success": True,
            "trait": trait,
            "imageUrl": f"/api/character-images/{trait}/image"
        }
    except Exception as e:
        logger.error(f"Error uploading character image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@api_router.get("/character-images/{trait}/image")
async def get_character_image(trait: str, request: Request):
    """Serve character trait image (true streaming + ETag)."""
    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail="Invalid trait")
    record = await db.character_images.find_one({"trait": trait})
    if not record or not record.get('imageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    return await stream_gridfs_response(
        gridfs_bucket=gridfs_bucket,
        file_id=record['imageFileId'],
        request=request,
        fallback_content_type="image/png",
        cache_control="public, max-age=3600",
        not_found_detail="Immagine non trovata",
    )

@admin_router.delete("/character-images/{trait}")
async def admin_delete_character_image(trait: str, email: str = Depends(verify_token)):
    """Delete character trait image"""
    from bson import ObjectId
    
    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail="Invalid trait")
    
    record = await db.character_images.find_one({"trait": trait})
    if record and record.get('imageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(record['imageFileId']))
        except Exception:
            pass
    
    await db.character_images.delete_one({"trait": trait})
    return {"success": True}

# CharacterTextUpdate model moved to /app/backend/models/character.py (Fase 4A)

@admin_router.put("/character-images/{trait}/text")
async def admin_update_character_text(
    trait: str,
    data: CharacterTextUpdate,
    email: str = Depends(verify_token)
):
    """Update text content for a character trait"""
    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail=f"Trait must be one of: {CHARACTER_TRAITS}")
    
    update_data = {"trait": trait, "updatedAt": datetime.now(timezone.utc)}
    
    if data.title is not None:
        update_data["title"] = data.title
    if data.shortDescription is not None:
        update_data["shortDescription"] = data.shortDescription
    if data.longDescription is not None:
        update_data["longDescription"] = data.longDescription
    
    await db.character_images.update_one(
        {"trait": trait},
        {"$set": update_data},
        upsert=True
    )
    
    # Return updated record
    record = await db.character_images.find_one({"trait": trait}, {"_id": 0})
    return {"success": True, "data": record}

# ============== STATIC FILES ==============

from fastapi.staticfiles import StaticFiles

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Fase 4C router split: include domain-specific routers BEFORE mounting the
# top-level api/admin routers. The new routers re-implement the public/admin
# routes that have already been migrated to the service layer; legacy route
# bodies are removed from this file in the same commit. Paths, status codes,
# auth requirements and response shapes are preserved verbatim.
from api.public import (
    themes as public_themes,
    reviews as public_reviews,
    site_settings as public_site_settings,
    bundles as public_bundles,
    illustrations as public_illustrations,
    posters as public_posters,
    games as public_games,
    level_backgrounds as public_level_backgrounds,
    books as public_books,
)
from api.admin import (
    auth as admin_auth,
    maintenance as admin_maintenance,
    themes as admin_themes,
    reviews as admin_reviews,
    site_settings as admin_site_settings,
    illustrations as admin_illustrations,
    bundles as admin_bundles,
    posters as admin_posters,
    games as admin_games,
    level_backgrounds as admin_level_backgrounds,
    books as admin_books,
)

api_router.include_router(public_themes.router)
api_router.include_router(public_reviews.router)
api_router.include_router(public_site_settings.router)
api_router.include_router(public_bundles.router)
api_router.include_router(public_illustrations.router)
api_router.include_router(public_posters.router)
api_router.include_router(public_games.router)
api_router.include_router(public_level_backgrounds.router)
api_router.include_router(public_books.router)

admin_router.include_router(admin_auth.router)
admin_router.include_router(admin_maintenance.router)
admin_router.include_router(admin_themes.router)
admin_router.include_router(admin_reviews.router)
admin_router.include_router(admin_site_settings.router)
admin_router.include_router(admin_illustrations.router)
admin_router.include_router(admin_bundles.router)
admin_router.include_router(admin_posters.router)
admin_router.include_router(admin_books.router)

# `admin/games` and `admin/games/bolle-magiche/level-backgrounds` were
# originally registered on ``api_router`` (with explicit ``/admin/...``
# path); we keep them functionally identical by mounting them on
# ``admin_router`` (which already has the ``/api/admin`` prefix).
admin_router.include_router(admin_games.router)
admin_router.include_router(admin_level_backgrounds.router)

# Include routers
app.include_router(api_router)
app.include_router(admin_router)


# Health endpoints.
#
# `/`  and `/health`  : K8s LIVENESS probes. Must NOT touch the DB so the pod
#                       is reported alive even if Atlas is momentarily slow
#                       during cold start or index creation.
# `/api/health`       : READINESS probe. Pings MongoDB with a short timeout
#                       and returns HTTP 503 if the database is unreachable,
#                       so load balancers can take this instance out of
#                       rotation until Atlas is back.
@app.get("/")
async def _root_health():
    return {"status": "ok", "service": "poppiconni"}


@app.get("/health")
async def _liveness():
    return {"status": "ok"}


@app.get("/api/health")
async def _readiness():
    db_ok = await ping_db(timeout_seconds=2.0)
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unreachable"},
        )
    return {"status": "ok", "db": "ok"}


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_client()
