"""Game level background models — moved verbatim from ``server.py`` (Fase 4A)."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class GameLevelBackgroundBase(BaseModel):
    """Background image for game levels (changes every 5 levels)"""
    levelRangeStart: int  # e.g., 1, 6, 11, 16...
    levelRangeEnd: int    # e.g., 5, 10, 15, 20...
    backgroundOpacity: int = 30  # 0-100% - controls overlay/blur

class GameLevelBackgroundCreate(GameLevelBackgroundBase):
    pass

class GameLevelBackgroundUpdate(BaseModel):
    levelRangeStart: Optional[int] = None
    levelRangeEnd: Optional[int] = None
    backgroundOpacity: Optional[int] = None

class GameLevelBackground(GameLevelBackgroundBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    gameSlug: str = "bolle-magiche"  # For future multi-game support
    backgroundImageFileId: Optional[str] = None
    backgroundImageUrl: Optional[str] = None
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
