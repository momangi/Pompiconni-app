"""AI generation models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


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
