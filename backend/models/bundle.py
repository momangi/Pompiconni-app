"""Bundle models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


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
    pdfFileId: Optional[str] = None  # Legacy - manual PDF upload
    pdfUrl: Optional[str] = None
    backgroundImageFileId: Optional[str] = None
    backgroundImageUrl: Optional[str] = None
    # Auto-generated PDF cache
    generatedPdfFileId: Optional[str] = None
    generatedPdfHash: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
