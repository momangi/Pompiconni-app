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
    """Legacy wrapper. Real implementation lives in ``utils.html_sanitizer``;
    kept here for backward-compatible imports from ``server.sanitize_scene_html``.
    """
    from utils.html_sanitizer import sanitize_scene_html as _sanitize
    return _sanitize(html)

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
# `/themes/{id}/background-image` stream and `/search/illustrations`
# were moved to `api/public/media/themes.py` and `api/public/search.py`
# in Fase 5/M1.

# `/api/illustrations/{id}/download`, `/download-status`, `/image`,
# `/image-status` were moved to `api/public/media/illustrations.py`
# in Fase 5/M1.

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

# Bundle media routes + PDF generation helpers moved to
# `api/admin/media/bundles.py` (upload-background, upload-pdf) and
# `api/public/media/bundles.py` (background-image, download,
# download-pdf with hash/cache/rate-limit) in Fase 5/M1.

# ============== ADMIN GENERIC UPLOAD (Fase 5/M3) ==============
# `POST /api/admin/upload` moved to `api/admin/uploads.py`. The local
# uploads directory mount (`/uploads`) remains registered below.

# Admin illustrations media routes (attach-pdf, attach-image,
# generate-illustration AI, PUT theme) moved to
# `api/admin/media/illustrations.py` in Fase 5/M1.

# ============== ADMIN REVIEWS & SETTINGS ==============

# Admin reviews CRUD moved to `api/admin/reviews.py` (Fase 4C).

# Admin maintenance endpoints (`/maintenance/fix-brand-name`,
# `/download-stats`, `/reset-fake-counters`) moved to
# `api/admin/maintenance.py` (Auth & Maintenance mini-batch).

# Admin /settings GET+PUT moved to `api/admin/site_settings.py` (Fase 4C).

# ============== SITE ASSETS (Fase 5/M3) ==============
# Hero image (public stream/status, admin upload/delete) and brand logo
# (public stream, admin status/upload/delete) moved to
# `api/public/media/site_assets.py` and `api/admin/media/site_assets.py`.
# `PUT /api/admin/social-links` moved to `api/admin/site_settings.py`
# (still settings, not media).

# `/theme-colors` (already moved to `api/public/themes.py` in Fase 4C)
# and `PUT /admin/illustrations/{id}/theme` (moved to
# `api/admin/media/illustrations.py` in Fase 5/M1).

# ============== BOOKS MEDIA ENDPOINTS (Fase 5/M2) ==============
# Public scene/cover image streams + free-book PDF download moved to
# `api/public/media/books.py`. Admin book cover + scene image uploads
# + admin PDF preview moved to `api/admin/media/books.py`.
# The `get_gridfs_image` helper used by both PDF endpoints moved to
# `utils/gridfs_helpers.py`.

# ============== POPPICONNI MULTI-AI PIPELINE (Fase 5/M3) ==============
# `/admin/styles` CRUD + upload-reference + reference-image stream moved
# to `api/admin/media/styles.py`. `/admin/generate-poppiconni` and
# `/admin/pipeline-status/{generation_id}` moved to
# `api/admin/media/ai_generation.py`. Pipeline internals (image_pipeline)
# are unchanged.

# ============== GAMES MEDIA ENDPOINTS (Fase 5/M2) ==============
# Public thumbnail/card-image/page-image streams moved to
# `api/public/media/games.py`. Admin thumbnail/card/page image uploads
# and deletes moved to `api/admin/media/games.py`. Public level-background
# image stream moved to `api/public/media/level_backgrounds.py`. Admin
# level-background create/upload/delete moved to
# `api/admin/media/level_backgrounds.py`.

# ============== POSTERS MEDIA ENDPOINTS (Fase 5/M2) ==============
# Public poster image stream + PDF download moved to
# `api/public/media/posters.py`. Admin poster image + PDF upload moved
# to `api/admin/media/posters.py`.

# Admin posters stats moved to `api/admin/posters.py` (Fase 4C).

# ============== POPPICONNI CHARACTER IMAGES (Fase 5/M3) ==============
# Public list + image stream moved to
# `api/public/media/character_images.py`. Admin list + upload + delete +
# text PUT moved to `api/admin/media/character_images.py`. The
# `CHARACTER_TRAITS` constant moved to
# `constants/character_traits.py`.

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
    search as public_search,
)
from api.public.media import (
    themes as public_media_themes,
    illustrations as public_media_illustrations,
    bundles as public_media_bundles,
    books as public_media_books,
    posters as public_media_posters,
    games as public_media_games,
    level_backgrounds as public_media_level_backgrounds,
    site_assets as public_media_site_assets,
    character_images as public_media_character_images,
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
from api.admin.media import (
    themes as admin_media_themes,
    illustrations as admin_media_illustrations,
    bundles as admin_media_bundles,
    books as admin_media_books,
    posters as admin_media_posters,
    games as admin_media_games,
    level_backgrounds as admin_media_level_backgrounds,
    site_assets as admin_media_site_assets,
    character_images as admin_media_character_images,
    styles as admin_media_styles,
    ai_generation as admin_media_ai_generation,
)
from api.admin import uploads as admin_uploads

api_router.include_router(public_themes.router)
api_router.include_router(public_reviews.router)
api_router.include_router(public_site_settings.router)
api_router.include_router(public_bundles.router)
api_router.include_router(public_illustrations.router)
api_router.include_router(public_posters.router)
api_router.include_router(public_games.router)
api_router.include_router(public_level_backgrounds.router)
api_router.include_router(public_books.router)
api_router.include_router(public_search.router)
api_router.include_router(public_media_themes.router)
api_router.include_router(public_media_illustrations.router)
api_router.include_router(public_media_bundles.router)
api_router.include_router(public_media_books.router)
api_router.include_router(public_media_posters.router)
api_router.include_router(public_media_games.router)
api_router.include_router(public_media_level_backgrounds.router)
api_router.include_router(public_media_site_assets.router)
api_router.include_router(public_media_character_images.router)

admin_router.include_router(admin_auth.router)
admin_router.include_router(admin_maintenance.router)
admin_router.include_router(admin_themes.router)
admin_router.include_router(admin_reviews.router)
admin_router.include_router(admin_site_settings.router)
admin_router.include_router(admin_illustrations.router)
admin_router.include_router(admin_bundles.router)
admin_router.include_router(admin_posters.router)
admin_router.include_router(admin_books.router)
admin_router.include_router(admin_media_themes.router)
admin_router.include_router(admin_media_illustrations.router)
admin_router.include_router(admin_media_bundles.router)
admin_router.include_router(admin_media_books.router)
admin_router.include_router(admin_media_posters.router)
admin_router.include_router(admin_media_site_assets.router)
admin_router.include_router(admin_media_character_images.router)
admin_router.include_router(admin_media_styles.router)
admin_router.include_router(admin_media_ai_generation.router)
admin_router.include_router(admin_uploads.router)

# `admin/games` and `admin/games/bolle-magiche/level-backgrounds` were
# originally registered on ``api_router`` (with explicit ``/admin/...``
# path); we keep them functionally identical by mounting them on
# ``admin_router`` (which already has the ``/api/admin`` prefix).
admin_router.include_router(admin_games.router)
admin_router.include_router(admin_level_backgrounds.router)
admin_router.include_router(admin_media_games.router)
admin_router.include_router(admin_media_level_backgrounds.router)

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
