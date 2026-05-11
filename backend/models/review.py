"""Review models — moved verbatim from ``server.py`` (Fase 4A)."""
import uuid

from pydantic import BaseModel, Field


class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str
    text: str
    rating: int = 5


class ReviewUpdate(BaseModel):
    is_approved: bool
