from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
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
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import base64
import aiofiles
import io

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
app = FastAPI(title="Pompiconni API", version="1.0.0")

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

class ThemeCreate(ThemeBase):
    pass

class Theme(ThemeBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    illustrationCount: int = 0
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Predefined color palette for themes (coherent with site design)
THEME_COLOR_PALETTE = [
    {"name": "Rosa Pompiconni", "value": "#FFB6C1", "hex": "#FFB6C1"},
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
    name: str
    description: str
    price: float = 0
    isFree: bool = True

class BundleCreate(BundleBase):
    illustrationIds: List[str] = []

class Bundle(BundleBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    illustrationIds: List[str] = []
    illustrationCount: int = 0
    createdAt: datetime = Field(default_factory=datetime.utcnow)

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
    {"id": "1", "name": "Maria R.", "role": "Mamma di Sofia, 5 anni", "text": "Sofia adora Pompiconni! Le tavole sono perfette per le sue manine e il personaggio è dolcissimo.", "rating": 5, "is_approved": True},
    {"id": "2", "name": "Luca B.", "role": "Papà di Marco e Giulia", "text": "Finalmente disegni da colorare con linee spesse e chiare. I miei bimbi non escono mai dai bordi!", "rating": 5, "is_approved": True},
    {"id": "3", "name": "Anna T.", "role": "Maestra d'asilo", "text": "Uso le tavole di Pompiconni in classe. I bambini adorano il personaggio e i temi sono educativi.", "rating": 5, "is_approved": True},
    {"id": "4", "name": "Giuseppe M.", "role": "Nonno di 3 nipotini", "text": "Ho stampato tutte le tavole gratuite. I nipotini sono entusiasti di colorare questo unicorno buffo!", "rating": 5, "is_approved": True},
    {"id": "5", "name": "Francesca L.", "role": "Mamma di Emma, 4 anni", "text": "Emma chiede sempre 'il cavallino con il corno'! Pompiconni è diventato il suo personaggio preferito.", "rating": 5, "is_approved": True},
    {"id": "6", "name": "Roberto S.", "role": "Papà di Matteo, 6 anni", "text": "Qualità eccellente delle illustrazioni. Mio figlio si diverte tantissimo a colorare ogni dettaglio.", "rating": 5, "is_approved": True},
    {"id": "7", "name": "Claudia P.", "role": "Educatrice", "text": "I temi sono ben pensati e adatti a diverse età. Uso molto il tema dei mestieri per attività didattiche.", "rating": 5, "is_approved": True},
    {"id": "8", "name": "Marco V.", "role": "Papà di due gemelle", "text": "Le mie bambine adorano Pompiconni! Il personaggio è tenero e le linee sono perfette per colorare.", "rating": 5, "is_approved": True},
    {"id": "9", "name": "Silvia G.", "role": "Mamma di Leonardo, 7 anni", "text": "Anche mio figlio grande ama Pompiconni. I disegni sono abbastanza dettagliati da non annoiare.", "rating": 5, "is_approved": True},
    {"id": "10", "name": "Andrea C.", "role": "Papà di Aurora, 3 anni", "text": "Aurora sta imparando i colori grazie a Pompiconni. Un progetto davvero ben fatto!", "rating": 5, "is_approved": True},
    {"id": "11", "name": "Elena B.", "role": "Zia di 4 nipoti", "text": "Regalo sempre album di Pompiconni ai miei nipotini. Sono sempre un successo!", "rating": 5, "is_approved": True},
    {"id": "12", "name": "Davide R.", "role": "Papà di Chiara, 5 anni", "text": "Il tema dello zoo è fantastico! Chiara ha imparato tanti animali colorando con Pompiconni.", "rating": 5, "is_approved": True},
    {"id": "13", "name": "Paola M.", "role": "Mamma di Tommaso, 4 anni", "text": "Tommaso porta sempre i disegni di Pompiconni all'asilo per mostrarli agli amichetti!", "rating": 5, "is_approved": True},
    {"id": "14", "name": "Stefano L.", "role": "Papà di Sofia e Mattia", "text": "Ottimo per tenere i bambini impegnati in modo creativo. Consiglio il bundle completo!", "rating": 5, "is_approved": True},
    {"id": "15", "name": "Valentina F.", "role": "Mamma di Giulia, 6 anni", "text": "Giulia ama il tema delle stagioni. Abbiamo stampato tutto per ogni periodo dell'anno!", "rating": 5, "is_approved": True}
]

SEED_THEMES = [
    {"id": "mestieri", "name": "I Mestieri", "description": "Pompiconni scopre i mestieri: pompiere, dottore, cuoco, pilota e tanti altri!", "icon": "Briefcase", "color": "#FFB6C1", "illustrationCount": 12},
    {"id": "fattoria", "name": "La Fattoria", "description": "Pompiconni in fattoria tra mucche, galline, maialini e trattori!", "icon": "Tractor", "color": "#98D8AA", "illustrationCount": 10},
    {"id": "zoo", "name": "Lo Zoo", "description": "Pompiconni visita lo zoo e incontra leoni, elefanti, giraffe e scimmie!", "icon": "Cat", "color": "#FFE5B4", "illustrationCount": 14},
    {"id": "sport", "name": "Lo Sport", "description": "Pompiconni si diverte con calcio, nuoto, tennis e tanti sport!", "icon": "Trophy", "color": "#B4D4FF", "illustrationCount": 8},
    {"id": "stagioni", "name": "Le Stagioni", "description": "Pompiconni attraverso primavera, estate, autunno e inverno!", "icon": "Sun", "color": "#FFDAB9", "illustrationCount": 16},
    {"id": "quotidiano", "name": "Vita Quotidiana", "description": "Pompiconni a scuola, al parco, in cucina e nelle avventure di ogni giorno!", "icon": "Home", "color": "#E6E6FA", "illustrationCount": 11}
]

SEED_ILLUSTRATIONS = [
    {"id": "1", "themeId": "mestieri", "title": "Pompiconni Pompiere", "description": "Il nostro unicorno salva la giornata!", "downloadCount": 234, "isFree": True, "price": 0},
    {"id": "2", "themeId": "mestieri", "title": "Pompiconni Dottore", "description": "Con lo stetoscopio e tanto amore", "downloadCount": 189, "isFree": True, "price": 0},
    {"id": "3", "themeId": "mestieri", "title": "Pompiconni Cuoco", "description": "Prepara dolcetti magici!", "downloadCount": 156, "isFree": False, "price": 0.99},
    {"id": "4", "themeId": "mestieri", "title": "Pompiconni Pilota", "description": "Vola tra le nuvole arcobaleno", "downloadCount": 201, "isFree": False, "price": 0.99},
    {"id": "5", "themeId": "mestieri", "title": "Pompiconni Astronauta", "description": "Alla scoperta delle stelle", "downloadCount": 178, "isFree": True, "price": 0},
    {"id": "6", "themeId": "fattoria", "title": "Pompiconni e la Mucca", "description": "Nuovi amici in fattoria", "downloadCount": 145, "isFree": True, "price": 0},
    {"id": "7", "themeId": "fattoria", "title": "Pompiconni sul Trattore", "description": "Guidando tra i campi", "downloadCount": 167, "isFree": False, "price": 0.99},
    {"id": "8", "themeId": "fattoria", "title": "Pompiconni e le Galline", "description": "A caccia di uova colorate", "downloadCount": 134, "isFree": True, "price": 0},
    {"id": "9", "themeId": "fattoria", "title": "Pompiconni e il Maialino", "description": "Amici nel fango!", "downloadCount": 112, "isFree": False, "price": 0.99},
    {"id": "10", "themeId": "zoo", "title": "Pompiconni e il Leone", "description": "Un incontro coraggioso", "downloadCount": 198, "isFree": True, "price": 0},
    {"id": "11", "themeId": "zoo", "title": "Pompiconni e l'Elefante", "description": "Grande amicizia!", "downloadCount": 223, "isFree": True, "price": 0},
    {"id": "12", "themeId": "zoo", "title": "Pompiconni e la Giraffa", "description": "Guardando in alto", "downloadCount": 187, "isFree": False, "price": 0.99},
    {"id": "13", "themeId": "zoo", "title": "Pompiconni e le Scimmie", "description": "Acrobazie divertenti", "downloadCount": 156, "isFree": True, "price": 0},
    {"id": "14", "themeId": "sport", "title": "Pompiconni Calciatore", "description": "Gol magico!", "downloadCount": 245, "isFree": True, "price": 0},
    {"id": "15", "themeId": "sport", "title": "Pompiconni Nuotatore", "description": "Splash tra le onde", "downloadCount": 134, "isFree": False, "price": 0.99},
    {"id": "16", "themeId": "sport", "title": "Pompiconni Tennista", "description": "Ace arcobaleno!", "downloadCount": 98, "isFree": True, "price": 0},
    {"id": "17", "themeId": "stagioni", "title": "Pompiconni in Primavera", "description": "Tra fiori e farfalle", "downloadCount": 278, "isFree": True, "price": 0},
    {"id": "18", "themeId": "stagioni", "title": "Pompiconni d'Estate", "description": "Al mare con il gelato", "downloadCount": 312, "isFree": True, "price": 0},
    {"id": "19", "themeId": "stagioni", "title": "Pompiconni d'Autunno", "description": "Tra le foglie colorate", "downloadCount": 189, "isFree": False, "price": 0.99},
    {"id": "20", "themeId": "stagioni", "title": "Pompiconni d'Inverno", "description": "Pupazzo di neve magico", "downloadCount": 267, "isFree": True, "price": 0},
    {"id": "21", "themeId": "quotidiano", "title": "Pompiconni a Scuola", "description": "Primo giorno di scuola", "downloadCount": 145, "isFree": True, "price": 0},
    {"id": "22", "themeId": "quotidiano", "title": "Pompiconni al Parco", "description": "Giochi sull'altalena", "downloadCount": 167, "isFree": False, "price": 0.99},
    {"id": "23", "themeId": "quotidiano", "title": "Pompiconni in Cucina", "description": "Biscotti con la mamma", "downloadCount": 198, "isFree": True, "price": 0}
]

SEED_BUNDLES = [
    {"id": "1", "name": "Starter Pack Pompiconni", "description": "10 tavole gratuite per iniziare a colorare!", "illustrationCount": 10, "price": 0, "isFree": True, "illustrationIds": []},
    {"id": "2", "name": "Album Mestieri Completo", "description": "Tutte le 12 tavole dei mestieri in PDF", "illustrationCount": 12, "price": 4.99, "isFree": False, "illustrationIds": []},
    {"id": "3", "name": "Mega Pack Stagioni", "description": "16 tavole per tutte le stagioni + bonus festività", "illustrationCount": 16, "price": 6.99, "isFree": False, "illustrationIds": []},
    {"id": "4", "name": "Collezione Completa", "description": "Tutti i temi + bonus esclusivi", "illustrationCount": 71, "price": 19.99, "isFree": False, "illustrationIds": []}
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
            bundles_to_insert.append(bundle)
        await db.bundles.insert_many(bundles_to_insert)
        logger.info("Seed bundles inserted")
    
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
    return {"message": "Pompiconni API v1.0", "status": "online"}

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
    bundles = await db.bundles.find().to_list(100)
    for b in bundles:
        b['_id'] = str(b.get('_id', ''))
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
    """Get public site settings (stripe status, hero image, etc)"""
    settings = await db.site_settings.find_one({"id": "global"})
    stripe_enabled = bool(STRIPE_SECRET_KEY) if not settings else settings.get("stripe_enabled", False)
    has_hero = bool(settings and settings.get('heroImageFileId')) if settings else False
    
    return {
        "stripe_enabled": stripe_enabled,
        "stripe_publishable_key": STRIPE_PUBLISHABLE_KEY if stripe_enabled else None,
        "hasHeroImage": has_hero,
        "heroImageUrl": "/api/site/hero-image" if has_hero else None
    }

@api_router.get("/brand-kit")
async def get_brand_kit():
    return {
        "character": {
            "name": "Pompiconni",
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
            {"name": "Rosa Pompiconni", "hex": "#FFB6C1", "usage": "Colore primario, guance, dettagli"},
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
    
    # Update theme illustration count
    await db.themes.update_one(
        {"id": illustration.themeId},
        {"$inc": {"illustrationCount": 1}}
    )
    
    # Remove MongoDB _id field to avoid serialization issues
    illust_dict.pop('_id', None)
    return illust_dict

@admin_router.put("/illustrations/{illustration_id}")
async def update_illustration(illustration_id: str, illustration: IllustrationCreate, email: str = Depends(verify_token)):
    illust_dict = illustration.dict()
    illust_dict['updatedAt'] = datetime.now(timezone.utc)
    result = await db.illustrations.update_one({"id": illustration_id}, {"$set": illust_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    return {"success": True}

@admin_router.delete("/illustrations/{illustration_id}")
async def delete_illustration(illustration_id: str, email: str = Depends(verify_token)):
    # Get illustration to find theme
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    
    # Delete illustration
    await db.illustrations.delete_one({"id": illustration_id})
    
    # Update theme count
    await db.themes.update_one(
        {"id": illust['themeId']},
        {"$inc": {"illustrationCount": -1}}
    )
    
    return {"success": True}

@admin_router.post("/bundles")
async def create_bundle(bundle: BundleCreate, email: str = Depends(verify_token)):
    bundle_dict = bundle.dict()
    bundle_dict['id'] = str(uuid.uuid4())
    bundle_dict['illustrationCount'] = len(bundle.illustrationIds)
    bundle_dict['createdAt'] = datetime.now(timezone.utc)
    await db.bundles.insert_one(bundle_dict)
    # Remove MongoDB _id field to avoid serialization issues
    bundle_dict.pop('_id', None)
    return bundle_dict

@admin_router.put("/bundles/{bundle_id}")
async def update_bundle(bundle_id: str, bundle: BundleCreate, email: str = Depends(verify_token)):
    bundle_dict = bundle.dict()
    bundle_dict['illustrationCount'] = len(bundle.illustrationIds)
    result = await db.bundles.update_one({"id": bundle_id}, {"$set": bundle_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    return {"success": True}

@admin_router.delete("/bundles/{bundle_id}")
async def delete_bundle(bundle_id: str, email: str = Depends(verify_token)):
    result = await db.bundles.delete_one({"id": bundle_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bundle non trovato")
    return {"success": True}

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
        
        full_prompt = f"Pompiconni the cute clumsy unicorn with big eyes, rosy cheeks, rainbow horn, fluffy mane: {request.prompt}. Style: {style_prompts.get(request.style, style_prompts['lineart'])}"
        
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
            'title': f"Pompiconni - {request.prompt[:30]}",
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
    
    scene_dict = {
        "id": str(uuid.uuid4()),
        "bookId": book_id,
        "sceneNumber": scene.sceneNumber,
        "text": scene.text.dict(),
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
    """Update scene text"""
    scene = await db.book_scenes.find_one({"id": scene_id, "bookId": book_id})
    if not scene:
        raise HTTPException(status_code=404, detail="Scena non trovata")
    
    await db.book_scenes.update_one(
        {"id": scene_id},
        {"$set": {"text": text.dict(), "updatedAt": datetime.now(timezone.utc)}}
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
