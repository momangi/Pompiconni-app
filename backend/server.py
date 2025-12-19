from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import base64
import aiofiles
import io
from pdf_generator import generate_book_pdf

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'pompiconni_db')]

# GridFS bucket for file storage
gridfs_bucket = AsyncIOMotorGridFSBucket(db)

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'pompiconni_secret_key_2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Admin credentials
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@pompiconni.it')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Create the main app
app = FastAPI(title="Poppiconni API", version="1.0.0")

# Create routers
api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin")

security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ============== MODELS ==============

class ThemeBase(BaseModel):
    name: str
    description: str
    icon: str = "BookOpen"
    color: str = "#FFB6C1"
    coverImage: Optional[str] = None
    backgroundOpacity: int = 30  # 10-80%

class ThemeCreate(ThemeBase):
    pass

class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    coverImage: Optional[str] = None
    backgroundOpacity: Optional[int] = None

class Theme(ThemeBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    illustrationCount: int = 0
    backgroundImageFileId: Optional[str] = None
    backgroundImageUrl: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Predefined color palette for themes (coherent with site design)
THEME_COLOR_PALETTE = [
    {"name": "Rosa Poppiconni", "value": "#FFB6C1", "hex": "#FFB6C1"},
    {"name": "Azzurro Cielo", "value": "#87CEEB", "hex": "#87CEEB"},
    {"name": "Verde Prato", "value": "#90EE90", "hex": "#90EE90"},
    {"name": "Giallo Sole", "value": "#FFD700", "hex": "#FFD700"},
    {"name": "Arancio Tramonto", "value": "#FFA07A", "hex": "#FFA07A"},
    {"name": "Lavanda", "value": "#E6E6FA", "hex": "#E6E6FA"},
    {"name": "Pesca", "value": "#FFDAB9", "hex": "#FFDAB9"},
    {"name": "Menta", "value": "#98FB98", "hex": "#98FB98"},
    {"name": "Corallo", "value": "#F08080", "hex": "#F08080"},
    {"name": "Turchese", "value": "#40E0D0", "hex": "#40E0D0"},
    {"name": "Lilla", "value": "#DDA0DD", "hex": "#DDA0DD"},
    {"name": "Albicocca", "value": "#FBCEB1", "hex": "#FBCEB1"}
]

class IllustrationBase(BaseModel):
    title: str
    description: str
    themeId: str
    isFree: bool = True
    price: float = 0.99

class IllustrationCreate(IllustrationBase):
    imageUrl: Optional[str] = None
    pdfUrl: Optional[str] = None

class Illustration(IllustrationBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    imageUrl: Optional[str] = None
    pdfUrl: Optional[str] = None
    downloadCount: int = 0
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class BundleBase(BaseModel):
    title: str
    subtitle: str = ""
    price: float = 0
    currency: str = "EUR"
    isFree: bool = True
    badgeText: str = ""
    isActive: bool = True
    sortOrder: int = 0
    backgroundOpacity: int = 30  # 10-80%

class BundleCreate(BundleBase):
    illustrationIds: List[str] = []

class BundleUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    isFree: Optional[bool] = None
    badgeText: Optional[str] = None
    isActive: Optional[bool] = None
    sortOrder: Optional[int] = None
    illustrationIds: Optional[List[str]] = None
    backgroundOpacity: Optional[int] = None

class Bundle(BundleBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    illustrationIds: List[str] = []
    illustrationCount: int = 0
    pdfFileId: Optional[str] = None
    pdfUrl: Optional[str] = None
    backgroundImageFileId: Optional[str] = None
    backgroundImageUrl: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    text: str
    rating: int = 5

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    email: str

class GenerateRequest(BaseModel):
    prompt: str
    themeId: Optional[str] = None
    style: str = "lineart"

class DownloadEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    illustrationId: str
    bundleId: Optional[str] = None
    downloadedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ipHash: Optional[str] = None  # Privacy-friendly tracking

class SiteSettings(BaseModel):
    show_reviews: bool = True
    stripe_enabled: bool = False

class SiteSettingsUpdate(BaseModel):
    show_reviews: Optional[bool] = None

class ReviewUpdate(BaseModel):
    is_approved: bool

class HeroImageResponse(BaseModel):
    hasHeroImage: bool
    heroImageUrl: Optional[str] = None
    updatedAt: Optional[str] = None

# ============== BOOK MODELS ==============

MAX_SCENES_PER_BOOK = 15  # Limite fisso e non modificabile

class BookSceneText(BaseModel):
    """Text content for a scene with TipTap HTML formatting"""
    html: str = ""  # Sanitized HTML from TipTap editor
    # Allowed tags: p, br, ul, li, strong, em, span (for font-size class)
    # Allowed classes: text-left, text-center, text-right, text-sm, text-base, text-lg

class BookSceneCreate(BaseModel):
    """Create a new scene"""
    sceneNumber: int
    text: BookSceneText = BookSceneText()

class BookScene(BaseModel):
    """A single scene in a book (2 logical pages)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bookId: str
    sceneNumber: int  # 1-15
    text: BookSceneText = BookSceneText()
    coloredImageFileId: Optional[str] = None  # GridFS ID for colored/soft image
    coloredImageUrl: Optional[str] = None
    lineArtImageFileId: Optional[str] = None  # GridFS ID for line art
    lineArtImageUrl: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BookBase(BaseModel):
    title: str
    description: str
    isFree: bool = True
    price: float = 4.99
    isVisible: bool = True
    allowDownload: bool = True

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    coverImageFileId: Optional[str] = None
    coverImageUrl: Optional[str] = None
    sceneCount: int = 0
    viewCount: int = 0
    downloadCount: int = 0
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReadingProgress(BaseModel):
    """Track reading progress per user/browser"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bookId: str
    visitorId: str  # Browser fingerprint or user ID
    currentScene: int = 1
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============== GENERATION STYLES MODELS (PIPELINE AI) ==============

class GenerationStyleBase(BaseModel):
    """Reference style for AI generation"""
    styleName: str
    description: Optional[str] = None
    isActive: bool = True

class GenerationStyleCreate(GenerationStyleBase):
    pass

class GenerationStyle(GenerationStyleBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    referenceImageFileId: Optional[str] = None
    referenceImageUrl: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PoppiconniGenerateRequest(BaseModel):
    """Request for Poppiconni Multi-AI Pipeline"""
    user_request: str  # User's description in natural language
    style_id: Optional[str] = None  # Reference style from library
    style_lock: bool = False  # If true, strictly follow reference style
    save_to_gallery: bool = True  # Auto-save to illustrations
    theme_id: Optional[str] = None  # Optional theme for categorization
    reference_image_base64: Optional[str] = None  # Direct reference image upload (base64)

class PoppiconniGenerateResponse(BaseModel):
    """Response from Poppiconni Multi-AI Pipeline"""
    success: bool
    generation_id: str
    status: str
    optimized_prompt: Optional[str] = None
    qc_passed: bool = False
    confidence_score: float = 0.0
    qc_issues: List[str] = []
    has_final_image: bool = False
    thumbnail_base64: Optional[str] = None
    illustration_id: Optional[str] = None
    message: str = ""
    retry_count: int = 0

# ============== POSTER MODELS ==============

class PosterStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

class PosterBase(BaseModel):
    """Base model for Poster (decorative colored illustrations for framing)"""
    title: str
    description: str = ""
    price: float = 0.0  # 0 = free
    status: str = "draft"  # draft or published

class PosterCreate(PosterBase):
    pass

class PosterUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None

class Poster(PosterBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    imageFileId: Optional[str] = None  # GridFS ID for preview image
    imageUrl: Optional[str] = None
    pdfFileId: Optional[str] = None  # GridFS ID for print-ready PDF
    pdfUrl: Optional[str] = None
    downloadCount: int = 0
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============== AUTH HELPERS ==============

def create_token(email: str) -> str:
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token scaduto")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token non valido")

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
            themes_to_insert.append(theme)
        await db.themes.insert_many(themes_to_insert)
        logger.info("Seed themes inserted")
    
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

@app.on_event("startup")
async def startup_event():
    await init_database()
    logger.info("Database initialized")

# ============== PUBLIC ENDPOINTS ==============

@api_router.get("/")
async def root():
    return {"message": "Poppiconni API v1.0", "status": "online"}

@api_router.get("/themes", response_model=List[dict])
async def get_themes():
    themes = await db.themes.find().to_list(100)
    for t in themes:
        t['_id'] = str(t.get('_id', ''))
    return themes

@api_router.get("/themes/{theme_id}")
async def get_theme(theme_id: str):
    theme = await db.themes.find_one({"id": theme_id})
    if not theme:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    theme['_id'] = str(theme.get('_id', ''))
    return theme

@api_router.get("/illustrations", response_model=List[dict])
async def get_illustrations(themeId: Optional[str] = None, isFree: Optional[bool] = None):
    query = {}
    if themeId:
        query["themeId"] = themeId
    if isFree is not None:
        query["isFree"] = isFree
    illustrations = await db.illustrations.find(query).to_list(1000)
    
    # Get real download counts from download_events
    download_counts = {}
    pipeline = [{"$group": {"_id": "$illustrationId", "count": {"$sum": 1}}}]
    events = await db.download_events.aggregate(pipeline).to_list(1000)
    for e in events:
        download_counts[e["_id"]] = e["count"]
    
    # Override downloadCount with real counts
    for i in illustrations:
        i['_id'] = str(i.get('_id', ''))
        i['downloadCount'] = download_counts.get(i['id'], 0)
    
    return illustrations

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
    
    # Get all illustrations (public endpoint shows all)
    illustrations = await db.illustrations.find({}, {"_id": 0}).to_list(1000)
    
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

@api_router.get("/illustrations/{illustration_id}")
async def get_illustration(illustration_id: str):
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    illust['_id'] = str(illust.get('_id', ''))
    
    # Get real download count from download_events
    real_count = await db.download_events.count_documents({"illustrationId": illustration_id})
    illust['downloadCount'] = real_count
    
    return illust

@api_router.post("/illustrations/{illustration_id}/download")
async def download_illustration(illustration_id: str):
    """
    Real file download endpoint using GridFS.
    Returns the PDF file as a downloadable attachment.
    """
    # Find the illustration
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    # Check if file exists in GridFS
    pdf_file_id = illust.get('pdfFileId')
    if not pdf_file_id:
        raise HTTPException(
            status_code=404, 
            detail="File non ancora disponibile. L'amministratore deve prima caricare il PDF."
        )
    
    try:
        from bson import ObjectId
        # Get file from GridFS
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(pdf_file_id))
        
        # Read file content
        content = await grid_out.read()
        
        # Log download event
        await db.download_events.insert_one({
            "id": str(uuid.uuid4()),
            "illustrationId": illustration_id,
            "bundleId": None,
            "downloadedAt": datetime.now(timezone.utc)
        })
        
        # Increment download counter
        await db.illustrations.update_one(
            {"id": illustration_id},
            {"$inc": {"downloadCount": 1}}
        )
        
        # Get filename from GridFS metadata or generate one
        filename = grid_out.filename or f"pompiconni_{illust.get('title', illustration_id)}.pdf"
        # Sanitize filename
        filename = filename.replace(' ', '_').replace('"', '').replace("'", "")
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Errore durante il download del file"
        )

@api_router.get("/illustrations/{illustration_id}/download-status")
async def get_download_status(illustration_id: str):
    """Check if a file is available for download"""
    illust = await db.illustrations.find_one({"id": illustration_id})
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
async def get_illustration_image(illustration_id: str):
    """
    Serve the illustration image from GridFS.
    Returns the image for preview/display purposes.
    """
    from bson import ObjectId
    
    # Find the illustration
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    # Check if image exists in GridFS
    image_file_id = illust.get('imageFileId')
    if not image_file_id:
        raise HTTPException(
            status_code=404, 
            detail="Immagine non ancora disponibile"
        )
    
    try:
        # Get file from GridFS
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(image_file_id))
        
        # Read file content
        content = await grid_out.read()
        
        # Get content type from metadata
        metadata = grid_out.metadata or {}
        content_type = metadata.get('content_type', 'image/jpeg')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=31536000"  # Cache for 1 year
            }
        )
        
    except Exception as e:
        logger.error(f"Error serving image: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Errore durante il caricamento dell'immagine"
        )

@api_router.get("/illustrations/{illustration_id}/image-status")
async def get_image_status(illustration_id: str):
    """Check if an image is available"""
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    has_image = bool(illust.get('imageFileId'))
    return {
        "available": has_image,
        "imageUrl": f"/api/illustrations/{illustration_id}/image" if has_image else None,
        "message": "Immagine disponibile" if has_image else "Immagine non ancora disponibile"
    }

@api_router.get("/bundles", response_model=List[dict])
async def get_bundles():
    """Get public bundles - only active ones, sorted by sortOrder"""
    bundles = await db.bundles.find({"isActive": True}, {"_id": 0}).sort("sortOrder", 1).to_list(100)
    # Add background image URL if available
    for b in bundles:
        if b.get('backgroundImageFileId'):
            b['backgroundImageUrl'] = f"/api/bundles/{b['id']}/background-image"
        if b.get('pdfFileId'):
            b['pdfUrl'] = f"/api/bundles/{b['id']}/download"
    return bundles

@api_router.get("/reviews", response_model=List[dict])
async def get_reviews():
    """Get public reviews - only approved ones if show_reviews is enabled"""
    # Check site settings
    settings = await db.site_settings.find_one({"id": "global"})
    if settings and not settings.get("show_reviews", True):
        return []  # Reviews disabled globally
    
    # Only return approved reviews
    reviews = await db.reviews.find({"is_approved": True}).to_list(100)
    for r in reviews:
        r['_id'] = str(r.get('_id', ''))
    return reviews

@api_router.get("/site-settings")
async def get_public_site_settings():
    """Get public site settings (stripe status, hero image, social links, etc)"""
    settings = await db.site_settings.find_one({"id": "global"})
    stripe_enabled = bool(STRIPE_SECRET_KEY) if not settings else settings.get("stripe_enabled", False)
    has_hero = bool(settings and settings.get('heroImageFileId')) if settings else False
    show_bundles = settings.get("showBundlesSection", True) if settings else True
    has_brand_logo = bool(settings and settings.get('brandLogoFileId')) if settings else False
    
    return {
        "stripe_enabled": stripe_enabled,
        "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY if stripe_enabled else None,
        "hasHeroImage": has_hero,
        "heroImageUrl": "/api/site/hero-image" if has_hero else None,
        "showBundlesSection": show_bundles,
        "hasBrandLogo": has_brand_logo,
        "brandLogoUrl": "/api/site/brand-logo" if has_brand_logo else None,
        "instagramUrl": settings.get("instagramUrl", "") if settings else "",
        "tiktokUrl": settings.get("tiktokUrl", "") if settings else ""
    }

@api_router.get("/brand-kit")
async def get_brand_kit():
    return {
        "character": {
            "name": "Poppiconni",
            "personality": "Dolce, simpatico, leggermente impacciato",
            "features": [
                "Occhi grandi e espressivi con ciglia lunghe",
                "Corno arcobaleno con sfumature pastello",
                "Criniera morbida e fluente",
                "Zampette tozze e adorabili",
                "Codina con ciuffo colorato",
                "Guanciotte rosate"
            ],
            "proportions": {
                "head": "30% del corpo",
                "body": "Tozzo e morbido",
                "legs": "Corte e rotonde",
                "horn": "Piccolo e delicato"
            }
        },
        "colors": [
            {"name": "Rosa Poppiconni", "hex": "#FFB6C1", "usage": "Colore primario, guance, dettagli"},
            {"name": "Azzurro Cielo", "hex": "#B4D4FF", "usage": "Sfondi, elementi secondari"},
            {"name": "Verde Menta", "hex": "#98D8AA", "usage": "Accenti natura, prati"},
            {"name": "Giallo Sole", "hex": "#FFE5B4", "usage": "Elementi luminosi, stelle"},
            {"name": "Lavanda Sogno", "hex": "#E6E6FA", "usage": "Magia, elementi fantasy"},
            {"name": "Pesca Dolce", "hex": "#FFDAB9", "usage": "Calore, accoglienza"}
        ],
        "typography": {
            "primary": "Quicksand",
            "secondary": "Nunito",
            "style": "Arrotondato, amichevole, facile da leggere"
        },
        "styleGuidelines": [
            "Linee morbide e spesse per facilità di colorazione",
            "Nessun dettaglio eccessivo",
            "Espressioni sempre positive e tenere",
            "Stile bambinesco, non realistico",
            "Proporzioni cartoon con testa grande"
        ]
    }

# ============== HELPER FUNCTIONS ==============

async def recalculate_bundle_counts():
    """
    Ricalcola automaticamente i conteggi dei bundle basandosi sui dati reali.
    CONTA TUTTE le illustrazioni (non solo quelle con file).
    Chiamato ogni volta che un'illustrazione viene creata, modificata o eliminata.
    """
    try:
        # Conta TUTTE le illustrazioni
        total_count = await db.illustrations.count_documents({})
        
        # Gratuite
        free_count = await db.illustrations.count_documents({"isFree": True})
        
        # Mestieri
        mestieri_count = await db.illustrations.count_documents({"themeId": "mestieri"})
        
        # Stagioni
        stagioni_count = await db.illustrations.count_documents({"themeId": "stagioni"})
        
        # Aggiorna Starter Pack (max 10 gratuite)
        starter_count = min(free_count, 10)
        await db.bundles.update_one(
            {"name": "Starter Pack Poppiconni"},
            {"$set": {
                "illustrationCount": starter_count,
                "description": f"{starter_count} tavole gratuite per iniziare a colorare!"
            }}
        )
        
        # Aggiorna Album Mestieri
        await db.bundles.update_one(
            {"name": "Album Mestieri Completo"},
            {"$set": {
                "illustrationCount": mestieri_count,
                "description": f"Tutte le {mestieri_count} tavole dei mestieri in PDF"
            }}
        )
        
        # Aggiorna Mega Pack Stagioni
        await db.bundles.update_one(
            {"name": "Mega Pack Stagioni"},
            {"$set": {
                "illustrationCount": stagioni_count,
                "description": f"{stagioni_count} tavole per tutte le stagioni"
            }}
        )
        
        # Aggiorna Collezione Completa
        await db.bundles.update_one(
            {"name": "Collezione Completa"},
            {"$set": {
                "illustrationCount": total_count,
                "description": f"Tutti i {total_count} disegni + bonus esclusivi"
            }}
        )
        
        logger.info(f"Bundle counts updated: total={total_count}, free={free_count}, mestieri={mestieri_count}, stagioni={stagioni_count}")
    except Exception as e:
        logger.error(f"Error updating bundle counts: {e}")

async def recalculate_theme_count(theme_id: str):
    """
    Ricalcola il conteggio di TUTTE le illustrazioni per un singolo tema.
    """
    if not theme_id:
        return
    count = await db.illustrations.count_documents({"themeId": theme_id})
    await db.themes.update_one(
        {"id": theme_id},
        {"$set": {"illustrationCount": count}}
    )

# ============== ADMIN ENDPOINTS ==============

@admin_router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    if request.email == ADMIN_EMAIL and request.password == ADMIN_PASSWORD:
        token = create_token(request.email)
        return LoginResponse(token=token, email=request.email)
    raise HTTPException(status_code=401, detail="Credenziali non valide")

@admin_router.get("/dashboard")
async def admin_dashboard(email: str = Depends(verify_token)):
    total_illustrations = await db.illustrations.count_documents({})
    total_themes = await db.themes.count_documents({})
    free_count = await db.illustrations.count_documents({"isFree": True})
    
    # Calculate total downloads ONLY from real download_events (source of truth)
    total_downloads = await db.download_events.count_documents({})
    
    # Get popular illustrations by REAL download events count
    pipeline = [
        {"$group": {"_id": "$illustrationId", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    popular_ids = await db.download_events.aggregate(pipeline).to_list(5)
    
    # Fetch illustration details for popular ones
    popular = []
    for item in popular_ids:
        illust = await db.illustrations.find_one({"id": item["_id"]})
        if illust:
            illust['_id'] = str(illust.get('_id', ''))
            illust['downloadCount'] = item['count']  # Real count from events
            popular.append(illust)
    
    # If no downloads yet, return top 5 illustrations with 0 downloads
    if not popular:
        popular = await db.illustrations.find().limit(5).to_list(5)
        for p in popular:
            p['_id'] = str(p.get('_id', ''))
            p['downloadCount'] = 0
    
    # Get download stats for last 7 days
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_downloads = await db.download_events.count_documents({
        "downloadedAt": {"$gte": seven_days_ago}
    })
    
    # Get site settings
    settings = await db.site_settings.find_one({"id": "global"})
    
    return {
        "totalIllustrations": total_illustrations,
        "totalThemes": total_themes,
        "totalDownloads": total_downloads,
        "freeCount": free_count,
        "popularIllustrations": popular,
        "recentDownloads": recent_downloads,
        "stripeEnabled": bool(STRIPE_SECRET_KEY),
        "showReviews": settings.get("show_reviews", True) if settings else True
    }

@admin_router.post("/themes")
async def create_theme(theme: ThemeCreate, email: str = Depends(verify_token)):
    theme_dict = theme.dict()
    theme_dict['id'] = str(uuid.uuid4())
    theme_dict['illustrationCount'] = 0
    theme_dict['createdAt'] = datetime.now(timezone.utc)
    theme_dict['updatedAt'] = datetime.now(timezone.utc)
    await db.themes.insert_one(theme_dict)
    # Remove MongoDB _id field to avoid serialization issues
    theme_dict.pop('_id', None)
    return theme_dict

@admin_router.put("/themes/{theme_id}")
async def update_theme(theme_id: str, theme: ThemeCreate, email: str = Depends(verify_token)):
    theme_dict = theme.dict()
    theme_dict['updatedAt'] = datetime.now(timezone.utc)
    result = await db.themes.update_one({"id": theme_id}, {"$set": theme_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    return {"success": True}

@admin_router.post("/illustrations")
async def create_illustration(illustration: IllustrationCreate, email: str = Depends(verify_token)):
    illust_dict = illustration.dict()
    illust_dict['id'] = str(uuid.uuid4())
    illust_dict['downloadCount'] = 0
    illust_dict['pdfFileId'] = None
    illust_dict['imageFileId'] = None
    illust_dict['createdAt'] = datetime.now(timezone.utc)
    illust_dict['updatedAt'] = datetime.now(timezone.utc)
    await db.illustrations.insert_one(illust_dict)
    
    # Ricalcola conteggi (solo se l'illustrazione è scaricabile)
    # Nota: alla creazione non ha ancora file, quindi non incrementa i conteggi
    # I conteggi si aggiorneranno quando verrà caricato un file
    await recalculate_theme_count(illustration.themeId)
    await recalculate_bundle_counts()
    
    # Remove MongoDB _id field to avoid serialization issues
    illust_dict.pop('_id', None)
    return illust_dict

@admin_router.put("/illustrations/{illustration_id}")
async def update_illustration(illustration_id: str, illustration: IllustrationCreate, email: str = Depends(verify_token)):
    # Get current illustration to check if theme changed
    current = await db.illustrations.find_one({"id": illustration_id})
    if not current:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    old_theme_id = current.get('themeId')
    new_theme_id = illustration.themeId
    
    illust_dict = illustration.dict()
    illust_dict['updatedAt'] = datetime.now(timezone.utc)
    result = await db.illustrations.update_one({"id": illustration_id}, {"$set": illust_dict})
    
    # Ricalcola conteggi per entrambi i temi (vecchio e nuovo)
    if old_theme_id:
        await recalculate_theme_count(old_theme_id)
    if new_theme_id and new_theme_id != old_theme_id:
        await recalculate_theme_count(new_theme_id)
    
    # Ricalcola bundle counts
    await recalculate_bundle_counts()
    
    return {"success": True}

@admin_router.delete("/illustrations/{illustration_id}")
async def delete_illustration(illustration_id: str, email: str = Depends(verify_token)):
    # Get illustration to find theme
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    # Delete illustration
    await db.illustrations.delete_one({"id": illustration_id})
    
    # Ricalcola conteggi (solo scaricabili)
    await recalculate_theme_count(illust.get('themeId'))
    await recalculate_bundle_counts()
    
    return {"success": True}

@admin_router.get("/bundles")
async def admin_get_bundles(email: str = Depends(verify_token)):
    """Get all bundles for admin (including inactive), sorted by sortOrder"""
    bundles = await db.bundles.find({}, {"_id": 0}).sort("sortOrder", 1).to_list(100)
    for b in bundles:
        if b.get('backgroundImageFileId'):
            b['backgroundImageUrl'] = f"/api/bundles/{b['id']}/background-image"
        if b.get('pdfFileId'):
            b['pdfUrl'] = f"/api/bundles/{b['id']}/download"
    return bundles

@admin_router.post("/bundles")
async def create_bundle(bundle: BundleCreate, email: str = Depends(verify_token)):
    bundle_dict = bundle.dict()
    bundle_dict['id'] = str(uuid.uuid4())
    bundle_dict['illustrationCount'] = len(bundle.illustrationIds)
    bundle_dict['pdfFileId'] = None
    bundle_dict['pdfUrl'] = None
    bundle_dict['backgroundImageFileId'] = None
    bundle_dict['backgroundImageUrl'] = None
    bundle_dict['createdAt'] = datetime.now(timezone.utc)
    bundle_dict['updatedAt'] = datetime.now(timezone.utc)
    await db.bundles.insert_one(bundle_dict)
    bundle_dict.pop('_id', None)
    return bundle_dict

@admin_router.put("/bundles/{bundle_id}")
async def update_bundle(bundle_id: str, bundle: BundleUpdate, email: str = Depends(verify_token)):
    existing = await db.bundles.find_one({"id": bundle_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    
    update_data = {"updatedAt": datetime.now(timezone.utc)}
    bundle_data = bundle.dict(exclude_unset=True)
    
    for key, value in bundle_data.items():
        if value is not None:
            update_data[key] = value
    
    # Recalculate illustrationCount if illustrationIds changed
    if 'illustrationIds' in update_data:
        update_data['illustrationCount'] = len(update_data['illustrationIds'])
    
    await db.bundles.update_one({"id": bundle_id}, {"$set": update_data})
    
    updated = await db.bundles.find_one({"id": bundle_id}, {"_id": 0})
    if updated.get('backgroundImageFileId'):
        updated['backgroundImageUrl'] = f"/api/bundles/{bundle_id}/background-image"
    if updated.get('pdfFileId'):
        updated['pdfUrl'] = f"/api/bundles/{bundle_id}/download"
    return updated

@admin_router.delete("/bundles/{bundle_id}")
async def delete_bundle(bundle_id: str, email: str = Depends(verify_token)):
    from bson import ObjectId
    
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    
    # Delete associated files from GridFS
    if bundle.get('pdfFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(bundle['pdfFileId']))
        except Exception:
            pass
    if bundle.get('backgroundImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(bundle['backgroundImageFileId']))
        except Exception:
            pass
    
    await db.bundles.delete_one({"id": bundle_id})
    return {"success": True}

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
async def get_bundle_background_image(bundle_id: str):
    """Serve bundle background image"""
    from bson import ObjectId
    
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle or not bundle.get('backgroundImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(bundle['backgroundImageFileId']))
        content = await grid_out.read()
        metadata = grid_out.metadata or {}
        content_type = metadata.get('content_type', 'image/png')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error serving bundle background: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore nel caricamento immagine")

@api_router.get("/bundles/{bundle_id}/download")
async def download_bundle_pdf(bundle_id: str):
    """Download bundle PDF"""
    from bson import ObjectId
    
    bundle = await db.bundles.find_one({"id": bundle_id})
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    
    if not bundle.get('pdfFileId'):
        raise HTTPException(status_code=404, detail="PDF non disponibile per questo bundle")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(bundle['pdfFileId']))
        content = await grid_out.read()
        
        safe_title = bundle.get('title', 'bundle').replace(' ', '_')
        filename = f"Poppiconni_{safe_title}.pdf"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Error downloading bundle PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore nel download")

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

@admin_router.get("/reviews")
async def admin_get_reviews(email: str = Depends(verify_token)):
    """Get all reviews for admin (including non-approved)"""
    reviews = await db.reviews.find().to_list(100)
    for r in reviews:
        r['_id'] = str(r.get('_id', ''))
    return reviews

@admin_router.put("/reviews/{review_id}")
async def admin_update_review(review_id: str, update: ReviewUpdate, email: str = Depends(verify_token)):
    """Approve or disapprove a review"""
    result = await db.reviews.update_one(
        {"id": review_id},
        {"$set": {"is_approved": update.is_approved}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    return {"success": True}

@admin_router.delete("/reviews/{review_id}")
async def admin_delete_review(review_id: str, email: str = Depends(verify_token)):
    """Delete a review"""
    result = await db.reviews.delete_one({"id": review_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    return {"success": True}

@admin_router.post("/maintenance/fix-brand-name")
async def admin_fix_brand_name(email: str = Depends(verify_token)):
    """
    One-off maintenance endpoint to fix brand name from 'Poppiconni' to 'Poppiconni'
    in all collections (illustrations, themes, reviews, bundles, books).
    Does NOT change technical fields (endpoints, variables, credentials).
    """
    results = {
        "illustrations_fixed": 0,
        "themes_fixed": 0,
        "reviews_fixed": 0,
        "bundles_fixed": 0,
        "books_fixed": 0,
        "book_scenes_fixed": 0
    }
    
    old_brand = "Pompiconni"
    new_brand = "Poppiconni"
    
    # Fix illustrations (title, description)
    illustrations = await db.illustrations.find({}).to_list(1000)
    for illust in illustrations:
        updates = {}
        if old_brand in illust.get('title', ''):
            updates['title'] = illust['title'].replace(old_brand, new_brand)
        if old_brand in illust.get('description', ''):
            updates['description'] = illust['description'].replace(old_brand, new_brand)
        if updates:
            await db.illustrations.update_one({"id": illust['id']}, {"$set": updates})
            results["illustrations_fixed"] += 1
    
    # Fix themes (name, description)
    themes = await db.themes.find({}).to_list(100)
    for theme in themes:
        updates = {}
        if old_brand in theme.get('name', ''):
            updates['name'] = theme['name'].replace(old_brand, new_brand)
        if old_brand in theme.get('description', ''):
            updates['description'] = theme['description'].replace(old_brand, new_brand)
        if updates:
            await db.themes.update_one({"id": theme['id']}, {"$set": updates})
            results["themes_fixed"] += 1
    
    # Fix reviews (text)
    reviews = await db.reviews.find({}).to_list(100)
    for review in reviews:
        if old_brand in review.get('text', ''):
            await db.reviews.update_one(
                {"id": review['id']}, 
                {"$set": {"text": review['text'].replace(old_brand, new_brand)}}
            )
            results["reviews_fixed"] += 1
    
    # Fix bundles (name, description)
    bundles = await db.bundles.find({}).to_list(100)
    for bundle in bundles:
        updates = {}
        if old_brand in bundle.get('name', ''):
            updates['name'] = bundle['name'].replace(old_brand, new_brand)
        if old_brand in bundle.get('description', ''):
            updates['description'] = bundle['description'].replace(old_brand, new_brand)
        if updates:
            await db.bundles.update_one({"id": bundle['id']}, {"$set": updates})
            results["bundles_fixed"] += 1
    
    # Fix books (title, description)
    books = await db.books.find({}).to_list(100)
    for book in books:
        updates = {}
        if old_brand in book.get('title', ''):
            updates['title'] = book['title'].replace(old_brand, new_brand)
        if old_brand in book.get('description', ''):
            updates['description'] = book['description'].replace(old_brand, new_brand)
        if updates:
            await db.books.update_one({"id": book['id']}, {"$set": updates})
            results["books_fixed"] += 1
    
    # Fix book scenes (text.html)
    scenes = await db.book_scenes.find({}).to_list(1000)
    for scene in scenes:
        html = scene.get('text', {}).get('html', '')
        if old_brand in html:
            await db.book_scenes.update_one(
                {"id": scene['id']}, 
                {"$set": {"text.html": html.replace(old_brand, new_brand)}}
            )
            results["book_scenes_fixed"] += 1
    
    return {
        "success": True,
        "message": f"Brand name fixed from '{old_brand}' to '{new_brand}'",
        "results": results
    }
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    return {"success": True}

@admin_router.get("/settings")
async def admin_get_settings(email: str = Depends(verify_token)):
    """Get site settings"""
    settings = await db.site_settings.find_one({"id": "global"})
    if not settings:
        settings = {
            "id": "global",
            "show_reviews": True,
            "stripe_enabled": bool(STRIPE_SECRET_KEY)
        }
    settings['_id'] = str(settings.get('_id', ''))
    settings['stripe_configured'] = bool(STRIPE_SECRET_KEY)
    return settings

@admin_router.put("/settings")
async def admin_update_settings(settings: SiteSettings, email: str = Depends(verify_token)):
    """Update site settings"""
    await db.site_settings.update_one(
        {"id": "global"},
        {
            "$set": {
                "show_reviews": settings.show_reviews,
                "updatedAt": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    return {"success": True}

@admin_router.get("/download-stats")
async def admin_get_download_stats(email: str = Depends(verify_token)):
    """Get detailed download statistics"""
    # Total downloads
    total = await db.download_events.count_documents({})
    
    # Downloads by day (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    pipeline = [
        {"$match": {"downloadedAt": {"$gte": thirty_days_ago}}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$downloadedAt"}
                },
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    daily_stats = await db.download_events.aggregate(pipeline).to_list(30)
    
    # Downloads by illustration
    illustration_pipeline = [
        {
            "$group": {
                "_id": "$illustrationId",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_illustrations = await db.download_events.aggregate(illustration_pipeline).to_list(10)
    
    return {
        "total": total,
        "dailyStats": daily_stats,
        "topIllustrations": top_illustrations
    }

@admin_router.post("/reset-fake-counters")
async def admin_reset_fake_counters(email: str = Depends(verify_token)):
    """Reset all download counters to 0 (removes fake demo data)"""
    result = await db.illustrations.update_many(
        {},
        {"$set": {"downloadCount": 0}}
    )
    return {
        "success": True,
        "message": f"Reset contatori per {result.modified_count} illustrazioni",
        "modified_count": result.modified_count
    }

# ============== HERO IMAGE & SITE SETTINGS ==============

@api_router.get("/site/hero-image")
async def get_hero_image():
    """Serve hero image from GridFS"""
    from bson import ObjectId
    
    settings = await db.site_settings.find_one({"id": "global"})
    if not settings or not settings.get('heroImageFileId'):
        raise HTTPException(status_code=404, detail="Hero image non configurata")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(settings['heroImageFileId']))
        content = await grid_out.read()
        content_type = settings.get('heroImageContentType', 'image/png')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error serving hero image: {str(e)}")
        raise HTTPException(status_code=404, detail="Hero image non trovata")

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
async def get_brand_logo():
    """Serve brand logo image"""
    from bson import ObjectId
    
    settings = await db.site_settings.find_one({"id": "global"})
    if not settings or not settings.get('brandLogoFileId'):
        raise HTTPException(status_code=404, detail="Brand logo non configurato")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(settings['brandLogoFileId']))
        content = await grid_out.read()
        content_type = settings.get('brandLogoContentType', 'image/png')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error serving brand logo: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore nel caricamento logo")

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
    await db.site_settings.update_one(
        {"id": "global"},
        {"$set": {"instagramUrl": instagramUrl, "tiktokUrl": tiktokUrl}},
        upsert=True
    )
    return {"success": True, "instagramUrl": instagramUrl, "tiktokUrl": tiktokUrl}

@api_router.get("/theme-colors")
async def get_theme_color_palette():
    """Get available theme colors"""
    return THEME_COLOR_PALETTE

# ============== ENHANCED THEME CRUD ==============

@admin_router.get("/themes/check-delete/{theme_id}")
async def check_theme_delete(theme_id: str, email: str = Depends(verify_token)):
    """Check if theme can be deleted and how many illustrations it has"""
    theme = await db.themes.find_one({"id": theme_id})
    if not theme:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    
    illustration_count = await db.illustrations.count_documents({"themeId": theme_id})
    
    return {
        "canDelete": illustration_count == 0,
        "illustrationCount": illustration_count,
        "message": f"Questo tema ha {illustration_count} illustrazioni associate" if illustration_count > 0 else "Tema eliminabile"
    }

@admin_router.delete("/themes/{theme_id}")
async def delete_theme(theme_id: str, force: bool = False, email: str = Depends(verify_token)):
    """Delete theme. If force=true, unassign illustrations first."""
    theme = await db.themes.find_one({"id": theme_id})
    if not theme:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    
    illustration_count = await db.illustrations.count_documents({"themeId": theme_id})
    
    if illustration_count > 0 and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Tema ha {illustration_count} illustrazioni. Usa force=true per rimuovere comunque."
        )
    
    # Unassign illustrations if force delete
    if force and illustration_count > 0:
        await db.illustrations.update_many(
            {"themeId": theme_id},
            {"$set": {"themeId": None, "updatedAt": datetime.now(timezone.utc)}}
        )
    
    await db.themes.delete_one({"id": theme_id})
    
    return {
        "success": True,
        "message": f"Tema eliminato. {illustration_count} illustrazioni riassegnate." if illustration_count > 0 else "Tema eliminato."
    }

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

@api_router.get("/books", response_model=List[dict])
async def get_books():
    """Get all visible books for public display"""
    books = await db.books.find({"isVisible": True}).to_list(100)
    for b in books:
        b['_id'] = str(b.get('_id', ''))
    return books

@api_router.get("/books/{book_id}")
async def get_book(book_id: str):
    """Get a single book with its scenes"""
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    if not book.get('isVisible', True):
        raise HTTPException(status_code=404, detail="Libro non disponibile")
    
    book['_id'] = str(book.get('_id', ''))
    
    # Get scenes ordered by sceneNumber
    scenes = await db.book_scenes.find({"bookId": book_id}).sort("sceneNumber", 1).to_list(MAX_SCENES_PER_BOOK)
    for s in scenes:
        s['_id'] = str(s.get('_id', ''))
    
    # Increment view count
    await db.books.update_one({"id": book_id}, {"$inc": {"viewCount": 1}})
    
    return {"book": book, "scenes": scenes}

@api_router.get("/books/{book_id}/scene/{scene_number}/colored-image")
async def get_scene_colored_image(book_id: str, scene_number: int):
    """Serve colored image for a scene"""
    from bson import ObjectId
    
    scene = await db.book_scenes.find_one({"bookId": book_id, "sceneNumber": scene_number})
    if not scene or not scene.get('coloredImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(scene['coloredImageFileId']))
        content = await grid_out.read()
        content_type = grid_out.metadata.get('content_type', 'image/png') if grid_out.metadata else 'image/png'
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=31536000"}
        )
    except Exception as e:
        logger.error(f"Error serving colored image: {str(e)}")
        raise HTTPException(status_code=404, detail="Immagine non trovata")

@api_router.get("/books/{book_id}/scene/{scene_number}/lineart-image")
async def get_scene_lineart_image(book_id: str, scene_number: int):
    """Serve line art image for a scene"""
    from bson import ObjectId
    
    scene = await db.book_scenes.find_one({"bookId": book_id, "sceneNumber": scene_number})
    if not scene or not scene.get('lineArtImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non disponibile")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(scene['lineArtImageFileId']))
        content = await grid_out.read()
        content_type = grid_out.metadata.get('content_type', 'image/png') if grid_out.metadata else 'image/png'
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=31536000"}
        )
    except Exception as e:
        logger.error(f"Error serving lineart image: {str(e)}")
        raise HTTPException(status_code=404, detail="Immagine non trovata")

@api_router.get("/books/{book_id}/cover")
async def get_book_cover(book_id: str):
    """Serve book cover image"""
    from bson import ObjectId
    
    book = await db.books.find_one({"id": book_id})
    if not book or not book.get('coverImageFileId'):
        raise HTTPException(status_code=404, detail="Copertina non disponibile")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(book['coverImageFileId']))
        content = await grid_out.read()
        content_type = grid_out.metadata.get('content_type', 'image/png') if grid_out.metadata else 'image/png'
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error serving book cover: {str(e)}")
        raise HTTPException(status_code=404, detail="Copertina non trovata")

# Reading Progress
@api_router.get("/books/{book_id}/progress/{visitor_id}")
async def get_reading_progress(book_id: str, visitor_id: str):
    """Get reading progress for a visitor"""
    progress = await db.reading_progress.find_one({"bookId": book_id, "visitorId": visitor_id})
    if not progress:
        return {"currentScene": 1, "hasProgress": False}
    return {"currentScene": progress.get('currentScene', 1), "hasProgress": True}

@api_router.post("/books/{book_id}/progress/{visitor_id}")
async def save_reading_progress(book_id: str, visitor_id: str, scene: int):
    """Save reading progress for a visitor"""
    await db.reading_progress.update_one(
        {"bookId": book_id, "visitorId": visitor_id},
        {
            "$set": {
                "currentScene": scene,
                "updatedAt": datetime.now(timezone.utc)
            },
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "bookId": book_id,
                "visitorId": visitor_id
            }
        },
        upsert=True
    )
    return {"success": True}

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

@admin_router.get("/books")
async def admin_get_books(email: str = Depends(verify_token)):
    """Get all books for admin"""
    books = await db.books.find().sort("createdAt", -1).to_list(100)
    for b in books:
        b['_id'] = str(b.get('_id', ''))
    return books

@admin_router.post("/books")
async def admin_create_book(book: BookCreate, email: str = Depends(verify_token)):
    """Create a new book"""
    book_dict = book.dict()
    book_dict['id'] = str(uuid.uuid4())
    book_dict['sceneCount'] = 0
    book_dict['viewCount'] = 0
    book_dict['downloadCount'] = 0
    book_dict['coverImageFileId'] = None
    book_dict['coverImageUrl'] = None
    book_dict['createdAt'] = datetime.now(timezone.utc)
    book_dict['updatedAt'] = datetime.now(timezone.utc)
    
    await db.books.insert_one(book_dict)
    book_dict.pop('_id', None)
    return book_dict

@admin_router.put("/books/{book_id}")
async def admin_update_book(book_id: str, book: BookCreate, email: str = Depends(verify_token)):
    """Update book details"""
    existing = await db.books.find_one({"id": book_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    
    update_data = book.dict()
    update_data['updatedAt'] = datetime.now(timezone.utc)
    
    await db.books.update_one({"id": book_id}, {"$set": update_data})
    return {"success": True}

@admin_router.delete("/books/{book_id}")
async def admin_delete_book(book_id: str, email: str = Depends(verify_token)):
    """Delete a book and all its scenes"""
    from bson import ObjectId
    
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    
    # Delete cover image from GridFS
    if book.get('coverImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(book['coverImageFileId']))
        except Exception:
            pass
    
    # Delete all scene images from GridFS
    scenes = await db.book_scenes.find({"bookId": book_id}).to_list(MAX_SCENES_PER_BOOK)
    for scene in scenes:
        if scene.get('coloredImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(scene['coloredImageFileId']))
            except Exception:
                pass
        if scene.get('lineArtImageFileId'):
            try:
                await gridfs_bucket.delete(ObjectId(scene['lineArtImageFileId']))
            except Exception:
                pass
    
    # Delete scenes
    await db.book_scenes.delete_many({"bookId": book_id})
    
    # Delete reading progress
    await db.reading_progress.delete_many({"bookId": book_id})
    
    # Delete book
    await db.books.delete_one({"id": book_id})
    
    return {"success": True, "message": "Libro eliminato con tutte le scene"}

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
        
        return {"success": True, "coverUrl": f"/api/books/{book_id}/cover"}
    except Exception as e:
        logger.error(f"Error uploading book cover: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

# ============== BOOK SCENES ADMIN ==============

@admin_router.get("/books/{book_id}/scenes")
async def admin_get_book_scenes(book_id: str, email: str = Depends(verify_token)):
    """Get all scenes for a book"""
    scenes = await db.book_scenes.find({"bookId": book_id}).sort("sceneNumber", 1).to_list(MAX_SCENES_PER_BOOK)
    for s in scenes:
        s['_id'] = str(s.get('_id', ''))
    return scenes

@admin_router.post("/books/{book_id}/scenes")
async def admin_create_scene(book_id: str, scene: BookSceneCreate, email: str = Depends(verify_token)):
    """Create a new scene for a book"""
    book = await db.books.find_one({"id": book_id})
    if not book:
        raise HTTPException(status_code=404, detail="Libro non trovato")
    
    # Check scene limit
    current_count = await db.book_scenes.count_documents({"bookId": book_id})
    if current_count >= MAX_SCENES_PER_BOOK:
        raise HTTPException(status_code=400, detail=f"Limite massimo di {MAX_SCENES_PER_BOOK} scene raggiunto")
    
    # Check scene number not already used
    existing = await db.book_scenes.find_one({"bookId": book_id, "sceneNumber": scene.sceneNumber})
    if existing:
        raise HTTPException(status_code=400, detail=f"Scena {scene.sceneNumber} già esistente")
    
    if scene.sceneNumber < 1 or scene.sceneNumber > MAX_SCENES_PER_BOOK:
        raise HTTPException(status_code=400, detail=f"Numero scena deve essere tra 1 e {MAX_SCENES_PER_BOOK}")
    
    # Sanitize HTML before saving
    sanitized_html = sanitize_scene_html(scene.text.html)
    
    scene_dict = {
        "id": str(uuid.uuid4()),
        "bookId": book_id,
        "sceneNumber": scene.sceneNumber,
        "text": {"html": sanitized_html},
        "coloredImageFileId": None,
        "coloredImageUrl": None,
        "lineArtImageFileId": None,
        "lineArtImageUrl": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.book_scenes.insert_one(scene_dict)
    
    # Update book scene count
    await db.books.update_one({"id": book_id}, {"$inc": {"sceneCount": 1}})
    
    scene_dict.pop('_id', None)
    return scene_dict

@admin_router.put("/books/{book_id}/scenes/{scene_id}")
async def admin_update_scene(
    book_id: str, 
    scene_id: str, 
    text: BookSceneText,
    email: str = Depends(verify_token)
):
    """Update scene text with HTML sanitization"""
    scene = await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")
    
    # Sanitize HTML before saving
    sanitized_text = {"html": sanitize_scene_html(text.html)}
    
    await db.book_scenes.update_one(
        {"id": scene_id},
        {"$set": {"text": sanitized_text, "updatedAt": datetime.now(timezone.utc)}}
    )
    return {"success": True}

@admin_router.delete("/books/{book_id}/scenes/{scene_id}")
async def admin_delete_scene(book_id: str, scene_id: str, email: str = Depends(verify_token)):
    """Delete a scene"""
    from bson import ObjectId
    
    scene = await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")
    
    # Delete images from GridFS
    if scene.get('coloredImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(scene['coloredImageFileId']))
        except Exception:
            pass
    if scene.get('lineArtImageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(scene['lineArtImageFileId']))
        except Exception:
            pass
    
    await db.book_scenes.delete_one({"id": scene_id})
    await db.books.update_one({"id": book_id}, {"$inc": {"sceneCount": -1}})
    
    return {"success": True}

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
async def get_style_reference_image(style_id: str, email: str = Depends(verify_token)):
    """Serve reference image for a style"""
    from bson import ObjectId
    
    style = await db.generation_styles.find_one({"id": style_id, "userId": email})
    if not style or not style.get('referenceImageFileId'):
        raise HTTPException(status_code=404, detail="Immagine di riferimento non trovata")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(style['referenceImageFileId']))
        content = await grid_out.read()
        metadata = grid_out.metadata or {}
        content_type = metadata.get('content_type', 'image/png')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error serving style reference: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore nel caricamento immagine")

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

# ============== POSTER ENDPOINTS ==============

# --- PUBLIC POSTER ENDPOINTS ---

@api_router.get("/posters")
async def get_public_posters():
    """Get all published posters for public display"""
    posters = await db.posters.find(
        {"status": "published"},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    return posters

@api_router.get("/posters/{poster_id}")
async def get_public_poster(poster_id: str):
    """Get a single published poster by ID"""
    poster = await db.posters.find_one(
        {"id": poster_id, "status": "published"},
        {"_id": 0}
    )
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    return poster

@api_router.get("/posters/{poster_id}/image")
async def get_poster_image(poster_id: str):
    """Serve poster preview image from GridFS"""
    from bson import ObjectId
    
    poster = await db.posters.find_one({"id": poster_id})
    if not poster or not poster.get('imageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(poster['imageFileId']))
        content = await grid_out.read()
        metadata = grid_out.metadata or {}
        content_type = metadata.get('content_type', 'image/png')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error serving poster image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore nel caricamento immagine")

@api_router.get("/posters/{poster_id}/download")
async def download_poster_pdf(poster_id: str):
    """Download poster PDF (only if free or purchased)"""
    from bson import ObjectId
    
    poster = await db.posters.find_one({"id": poster_id, "status": "published"})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    
    if not poster.get('pdfFileId'):
        raise HTTPException(status_code=404, detail="PDF non disponibile")
    
    # Check if poster is free
    if poster.get('price', 0) > 0:
        # TODO: Check if user has purchased this poster
        # For now, return error for paid posters
        raise HTTPException(status_code=403, detail="Poster a pagamento - acquista per scaricare")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(poster['pdfFileId']))
        content = await grid_out.read()
        
        # Increment download count
        await db.posters.update_one(
            {"id": poster_id},
            {"$inc": {"downloadCount": 1}}
        )
        
        safe_title = re.sub(r'[^\w\s-]', '', poster.get('title', 'poster')).strip().replace(' ', '_')
        filename = f"Poppiconni_Poster_{safe_title}.pdf"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"Error downloading poster PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore nel download")

# --- ADMIN POSTER ENDPOINTS ---

@admin_router.get("/posters")
async def admin_get_posters(email: str = Depends(verify_token)):
    """Get all posters for admin panel"""
    posters = await db.posters.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return posters

@admin_router.post("/posters")
async def admin_create_poster(poster: PosterCreate, email: str = Depends(verify_token)):
    """Create a new poster"""
    poster_dict = {
        "id": str(uuid.uuid4()),
        "title": poster.title,
        "description": poster.description,
        "price": poster.price,
        "status": poster.status,
        "imageFileId": None,
        "imageUrl": None,
        "pdfFileId": None,
        "pdfUrl": None,
        "downloadCount": 0,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    await db.posters.insert_one(poster_dict)
    poster_dict.pop('_id', None)
    
    return poster_dict

@admin_router.get("/posters/{poster_id}")
async def admin_get_poster(poster_id: str, email: str = Depends(verify_token)):
    """Get a single poster for editing"""
    poster = await db.posters.find_one({"id": poster_id}, {"_id": 0})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    return poster

@admin_router.put("/posters/{poster_id}")
async def admin_update_poster(poster_id: str, poster: PosterUpdate, email: str = Depends(verify_token)):
    """Update a poster"""
    update_data = {k: v for k, v in poster.dict().items() if v is not None}
    update_data['updatedAt'] = datetime.now(timezone.utc)
    
    result = await db.posters.update_one({"id": poster_id}, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    
    return {"success": True}

@admin_router.delete("/posters/{poster_id}")
async def admin_delete_poster(poster_id: str, email: str = Depends(verify_token)):
    """Delete a poster and its files"""
    from bson import ObjectId
    
    poster = await db.posters.find_one({"id": poster_id})
    if not poster:
        raise HTTPException(status_code=404, detail="Poster non trovato")
    
    # Delete image from GridFS
    if poster.get('imageFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(poster['imageFileId']))
        except Exception:
            pass
    
    # Delete PDF from GridFS
    if poster.get('pdfFileId'):
        try:
            await gridfs_bucket.delete(ObjectId(poster['pdfFileId']))
        except Exception:
            pass
    
    await db.posters.delete_one({"id": poster_id})
    return {"success": True}

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

@admin_router.get("/posters/stats/summary")
async def admin_poster_stats(email: str = Depends(verify_token)):
    """Get poster statistics"""
    total = await db.posters.count_documents({})
    published = await db.posters.count_documents({"status": "published"})
    drafts = await db.posters.count_documents({"status": "draft"})
    free = await db.posters.count_documents({"status": "published", "price": 0})
    
    # Sum all downloads
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$downloadCount"}}}]
    result = await db.posters.aggregate(pipeline).to_list(1)
    total_downloads = result[0]['total'] if result else 0
    
    return {
        "total": total,
        "published": published,
        "drafts": drafts,
        "free": free,
        "paid": published - free,
        "totalDownloads": total_downloads
    }

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
        
        return {
            "success": True,
            "trait": trait,
            "imageUrl": f"/api/character-images/{trait}/image"
        }
    except Exception as e:
        logger.error(f"Error uploading character image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore durante il caricamento")

@api_router.get("/character-images/{trait}/image")
async def get_character_image(trait: str):
    """Serve character trait image"""
    from bson import ObjectId
    
    if trait not in CHARACTER_TRAITS:
        raise HTTPException(status_code=400, detail="Invalid trait")
    
    record = await db.character_images.find_one({"trait": trait})
    if not record or not record.get('imageFileId'):
        raise HTTPException(status_code=404, detail="Immagine non trovata")
    
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(record['imageFileId']))
        content = await grid_out.read()
        metadata = grid_out.metadata or {}
        content_type = metadata.get('content_type', 'image/png')
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error serving character image: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore nel caricamento immagine")

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

class CharacterTextUpdate(BaseModel):
    """Model for updating character trait texts"""
    title: Optional[str] = None
    shortDescription: Optional[str] = None
    longDescription: Optional[str] = None

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

# Include routers
app.include_router(api_router)
app.include_router(admin_router)

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
    client.close()
