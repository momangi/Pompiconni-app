"""Illustration models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field


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
    isPublished: bool = False
    downloadEnabled: bool = True  # Flag per abilitare/disabilitare download (solo se pubblico)
    publishedAt: Optional[datetime] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GenerateRequest(BaseModel):
    prompt: str
    themeId: Optional[str] = None
    style: str = "lineart"
