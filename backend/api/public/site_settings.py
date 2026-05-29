"""Public site-settings + static brand-kit router (Fase 4C router split)."""
from fastapi import APIRouter

from services import settings_service


router = APIRouter()


@router.get("/site-settings")
async def get_public_site_settings():
    """Get public site settings (stripe status, hero image, social links, legal info, etc)"""
    return await settings_service.get_public_payload()


@router.get("/brand-kit")
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
                "Guanciotte rosate",
            ],
            "proportions": {
                "head": "30% del corpo",
                "body": "Tozzo e morbido",
                "legs": "Corte e rotonde",
                "horn": "Piccolo e delicato",
            },
        },
        "colors": [
            {"name": "Rosa Poppiconni", "hex": "#FFB6C1", "usage": "Colore primario, guance, dettagli"},
            {"name": "Azzurro Cielo", "hex": "#B4D4FF", "usage": "Sfondi, elementi secondari"},
            {"name": "Verde Menta", "hex": "#98D8AA", "usage": "Accenti natura, prati"},
            {"name": "Giallo Sole", "hex": "#FFE5B4", "usage": "Elementi luminosi, stelle"},
            {"name": "Lavanda Sogno", "hex": "#E6E6FA", "usage": "Magia, elementi fantasy"},
            {"name": "Pesca Dolce", "hex": "#FFDAB9", "usage": "Calore, accoglienza"},
        ],
        "typography": {
            "primary": "Quicksand",
            "secondary": "Nunito",
            "style": "Arrotondato, amichevole, facile da leggere",
        },
        "styleGuidelines": [
            "Linee morbide e spesse per facilità di colorazione",
            "Nessun dettaglio eccessivo",
            "Espressioni sempre positive e tenere",
            "Stile bambinesco, non realistico",
            "Proporzioni cartoon con testa grande",
        ],
    }
