"""Game models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


class Game(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slug: str
    title: str
    shortDescription: Optional[str] = None
    longDescription: Optional[str] = None
    status: str = "coming_soon"  # available, coming_soon
    ageRecommended: str = "3+"
    howToPlay: List[str] = []
    thumbnailFileId: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    # Card image (for /giochi list page)
    cardImageFileId: Optional[str] = None
    cardImageUrl: Optional[str] = None
    cardImageOpacity: int = 35  # 0-100%
    # Page image (for /giochi/:slug detail page)
    pageImageFileId: Optional[str] = None
    pageImageUrl: Optional[str] = None
    pageImageOpacity: int = 25  # 0-100%
    sortOrder: int = 0
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
