"""Character image text update model — moved verbatim from ``server.py``.

The original class was declared *inline* among the route handlers
(line 4973 of the legacy ``server.py``). It is gathered here for
consistency with the other domain models.
"""
from typing import Optional

from pydantic import BaseModel


class CharacterTextUpdate(BaseModel):
    """Model for updating character trait texts"""
    title: Optional[str] = None
    shortDescription: Optional[str] = None
    longDescription: Optional[str] = None
