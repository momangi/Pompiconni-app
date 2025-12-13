from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import os
import logging
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
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

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

# ============== SEED DATA ==============

SEED_REVIEWS = [
    {"id": "1", "name": "Maria R.", "role": "Mamma di Sofia, 5 anni", "text": "Sofia adora Pompiconni! Le tavole sono perfette per le sue manine e il personaggio è dolcissimo.", "rating": 5},
    {"id": "2", "name": "Luca B.", "role": "Papà di Marco e Giulia", "text": "Finalmente disegni da colorare con linee spesse e chiare. I miei bimbi non escono mai dai bordi!", "rating": 5},
    {"id": "3", "name": "Anna T.", "role": "Maestra d'asilo", "text": "Uso le tavole di Pompiconni in classe. I bambini adorano il personaggio e i temi sono educativi.", "rating": 5},
    {"id": "4", "name": "Giuseppe M.", "role": "Nonno di 3 nipotini", "text": "Ho stampato tutte le tavole gratuite. I nipotini sono entusiasti di colorare questo unicorno buffo!", "rating": 5},
    {"id": "5", "name": "Francesca L.", "role": "Mamma di Emma, 4 anni", "text": "Emma chiede sempre 'il cavallino con il corno'! Pompiconni è diventato il suo personaggio preferito.", "rating": 5},
    {"id": "6", "name": "Roberto S.", "role": "Papà di Matteo, 6 anni", "text": "Qualità eccellente delle illustrazioni. Mio figlio si diverte tantissimo a colorare ogni dettaglio.", "rating": 5},
    {"id": "7", "name": "Claudia P.", "role": "Educatrice", "text": "I temi sono ben pensati e adatti a diverse età. Uso molto il tema dei mestieri per attività didattiche.", "rating": 5},
    {"id": "8", "name": "Marco V.", "role": "Papà di due gemelle", "text": "Le mie bambine adorano Pompiconni! Il personaggio è tenero e le linee sono perfette per colorare.", "rating": 5},
    {"id": "9", "name": "Silvia G.", "role": "Mamma di Leonardo, 7 anni", "text": "Anche mio figlio grande ama Pompiconni. I disegni sono abbastanza dettagliati da non annoiare.", "rating": 5},
    {"id": "10", "name": "Andrea C.", "role": "Papà di Aurora, 3 anni", "text": "Aurora sta imparando i colori grazie a Pompiconni. Un progetto davvero ben fatto!", "rating": 5},
    {"id": "11", "name": "Elena B.", "role": "Zia di 4 nipoti", "text": "Regalo sempre album di Pompiconni ai miei nipotini. Sono sempre un successo!", "rating": 5},
    {"id": "12", "name": "Davide R.", "role": "Papà di Chiara, 5 anni", "text": "Il tema dello zoo è fantastico! Chiara ha imparato tanti animali colorando con Pompiconni.", "rating": 5},
    {"id": "13", "name": "Paola M.", "role": "Mamma di Tommaso, 4 anni", "text": "Tommaso porta sempre i disegni di Pompiconni all'asilo per mostrarli agli amichetti!", "rating": 5},
    {"id": "14", "name": "Stefano L.", "role": "Papà di Sofia e Mattia", "text": "Ottimo per tenere i bambini impegnati in modo creativo. Consiglio il bundle completo!", "rating": 5},
    {"id": "15", "name": "Valentina F.", "role": "Mamma di Giulia, 6 anni", "text": "Giulia ama il tema delle stagioni. Abbiamo stampato tutto per ogni periodo dell'anno!", "rating": 5}
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
        now = datetime.utcnow()
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
        now = datetime.utcnow()
        illustrations_to_insert = []
        for illust in SEED_ILLUSTRATIONS:
            illust['createdAt'] = now
            illust['updatedAt'] = now
            illustrations_to_insert.append(illust)
        await db.illustrations.insert_many(illustrations_to_insert)
        logger.info("Seed illustrations inserted")
    
    # Check if bundles exist - use insert_many for batch performance
    bundles_count = await db.bundles.count_documents({})
    if bundles_count == 0:
        now = datetime.utcnow()
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
        logger.info("Seed reviews inserted")

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
    for i in illustrations:
        i['_id'] = str(i.get('_id', ''))
    return illustrations

@api_router.get("/illustrations/{illustration_id}")
async def get_illustration(illustration_id: str):
    illust = await db.illustrations.find_one({"id": illustration_id})
    if not illust:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    illust['_id'] = str(illust.get('_id', ''))
    return illust

@api_router.post("/illustrations/{illustration_id}/download")
async def increment_download(illustration_id: str):
    result = await db.illustrations.update_one(
        {"id": illustration_id},
        {"$inc": {"downloadCount": 1}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Illustrazione non trovata")
    return {"success": True}

@api_router.get("/bundles", response_model=List[dict])
async def get_bundles():
    bundles = await db.bundles.find().to_list(100)
    for b in bundles:
        b['_id'] = str(b.get('_id', ''))
    return bundles

@api_router.get("/reviews", response_model=List[dict])
async def get_reviews():
    reviews = await db.reviews.find().to_list(100)
    for r in reviews:
        r['_id'] = str(r.get('_id', ''))
    return reviews

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
    
    # Calculate total downloads
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$downloadCount"}}}]
    result = await db.illustrations.aggregate(pipeline).to_list(1)
    total_downloads = result[0]["total"] if result else 0
    
    # Get popular illustrations
    popular = await db.illustrations.find().sort("downloadCount", -1).limit(5).to_list(5)
    for p in popular:
        p['_id'] = str(p.get('_id', ''))
    
    return {
        "totalIllustrations": total_illustrations,
        "totalThemes": total_themes,
        "totalDownloads": total_downloads,
        "freeCount": free_count,
        "popularIllustrations": popular
    }

@admin_router.post("/themes")
async def create_theme(theme: ThemeCreate, email: str = Depends(verify_token)):
    theme_dict = theme.dict()
    theme_dict['id'] = str(uuid.uuid4())
    theme_dict['illustrationCount'] = 0
    theme_dict['createdAt'] = datetime.utcnow()
    theme_dict['updatedAt'] = datetime.utcnow()
    await db.themes.insert_one(theme_dict)
    # Remove MongoDB _id field to avoid serialization issues
    theme_dict.pop('_id', None)
    return theme_dict

@admin_router.put("/themes/{theme_id}")
async def update_theme(theme_id: str, theme: ThemeCreate, email: str = Depends(verify_token)):
    theme_dict = theme.dict()
    theme_dict['updatedAt'] = datetime.utcnow()
    result = await db.themes.update_one({"id": theme_id}, {"$set": theme_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    return {"success": True}

@admin_router.delete("/themes/{theme_id}")
async def delete_theme(theme_id: str, email: str = Depends(verify_token)):
    result = await db.themes.delete_one({"id": theme_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tema non trovato")
    return {"success": True}

@admin_router.post("/illustrations")
async def create_illustration(illustration: IllustrationCreate, email: str = Depends(verify_token)):
    illust_dict = illustration.dict()
    illust_dict['id'] = str(uuid.uuid4())
    illust_dict['downloadCount'] = 0
    illust_dict['createdAt'] = datetime.utcnow()
    illust_dict['updatedAt'] = datetime.utcnow()
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
    illust_dict['updatedAt'] = datetime.utcnow()
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
    bundle_dict['createdAt'] = datetime.utcnow()
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
    # Validate file type
    allowed_extensions = {
        "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "pdf": [".pdf"]
    }
    
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions.get(file_type, []):
        raise HTTPException(status_code=400, detail=f"Tipo file non permesso: {ext}")
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Return URL (relative path)
    file_url = f"/uploads/{unique_filename}"
    
    return {"url": file_url, "filename": unique_filename}

@admin_router.post("/generate-illustration")
async def generate_illustration(request: GenerateRequest, email: str = Depends(verify_token)):
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
        
        # Save the generated image
        unique_filename = f"generated_{uuid.uuid4()}.png"
        file_path = UPLOAD_DIR / unique_filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(images[0])
        
        image_url = f"/uploads/{unique_filename}"
        
        # Convert to base64 for preview
        image_base64 = base64.b64encode(images[0]).decode('utf-8')
        
        # Optionally create illustration record
        if request.themeId:
            illust_dict = {
                'id': str(uuid.uuid4()),
                'themeId': request.themeId,
                'title': f"Pompiconni - {request.prompt[:30]}",
                'description': request.prompt,
                'imageUrl': image_url,
                'pdfUrl': None,
                'isFree': True,
                'price': 0,
                'downloadCount': 0,
                'createdAt': datetime.utcnow(),
                'updatedAt': datetime.utcnow()
            }
            await db.illustrations.insert_one(illust_dict)
            await db.themes.update_one(
                {"id": request.themeId},
                {"$inc": {"illustrationCount": 1}}
            )
            
            return {
                "success": True,
                "imageUrl": image_url,
                "imageBase64": image_base64,
                "illustration": illust_dict
            }
        
        return {
            "success": True,
            "imageUrl": image_url,
            "imageBase64": image_base64
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Libreria AI non installata")
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Errore generazione: {str(e)}")

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
