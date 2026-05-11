"""Cross-cutting models that do not belong to a single domain."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class DownloadEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    illustrationId: str
    bundleId: Optional[str] = None
    downloadedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ipHash: Optional[str] = None  # Privacy-friendly tracking
