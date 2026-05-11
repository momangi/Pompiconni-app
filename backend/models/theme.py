"""Theme models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field


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
