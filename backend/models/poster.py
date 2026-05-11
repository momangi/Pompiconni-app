"""Poster models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class PosterStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class PosterBase(BaseModel):
    """Base model for Poster (decorative colored illustrations for framing)"""
    title: str
    description: str = ""
    price: float = 0.0  # 0 = free
    status: str = "draft"  # draft or published
    downloadEnabled: bool = True  # Flag per abilitare/disabilitare download (solo se pubblico)


class PosterCreate(PosterBase):
    pass


class PosterUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    downloadEnabled: Optional[bool] = None


class Poster(PosterBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    imageFileId: Optional[str] = None  # GridFS ID for preview image
    imageUrl: Optional[str] = None
    pdfFileId: Optional[str] = None  # GridFS ID for print-ready PDF
    pdfUrl: Optional[str] = None
    downloadCount: int = 0
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
