"""Book & scene models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field


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
