"""Pydantic models for the Poppiconni backend.

Each submodule groups the data shapes (DTOs) for a single domain.
This package only contains data classes — no I/O, no MongoDB calls, no
FastAPI dependencies. The legacy import path ``from models import X``
keeps existing code in ``server.py`` working unchanged.
"""

from .auth import LoginRequest, LoginResponse
from .book import (
    MAX_SCENES_PER_BOOK,
    Book,
    BookBase,
    BookCreate,
    BookScene,
    BookSceneCreate,
    BookSceneText,
    ReadingProgress,
)
from .bundle import Bundle, BundleBase, BundleCreate, BundleUpdate
from .character import CharacterTextUpdate
from .common import DownloadEvent
from .game import Game
from .generation import (
    GenerationStyle,
    GenerationStyleBase,
    GenerationStyleCreate,
    PoppiconniGenerateRequest,
    PoppiconniGenerateResponse,
)
from .illustration import (
    GenerateRequest,
    Illustration,
    IllustrationBase,
    IllustrationCreate,
)
from .level_background import (
    GameLevelBackground,
    GameLevelBackgroundBase,
    GameLevelBackgroundCreate,
    GameLevelBackgroundUpdate,
)
from .poster import Poster, PosterBase, PosterCreate, PosterStatus, PosterUpdate
from .review import Review, ReviewUpdate
from .site_settings import HeroImageResponse, SiteSettings, SiteSettingsUpdate
from .theme import THEME_COLOR_PALETTE, Theme, ThemeBase, ThemeCreate, ThemeUpdate

__all__ = [
    # auth
    "LoginRequest", "LoginResponse",
    # theme
    "Theme", "ThemeBase", "ThemeCreate", "ThemeUpdate", "THEME_COLOR_PALETTE",
    # illustration
    "Illustration", "IllustrationBase", "IllustrationCreate", "GenerateRequest",
    # bundle
    "Bundle", "BundleBase", "BundleCreate", "BundleUpdate",
    # review
    "Review", "ReviewUpdate",
    # game
    "Game",
    # level background
    "GameLevelBackground", "GameLevelBackgroundBase",
    "GameLevelBackgroundCreate", "GameLevelBackgroundUpdate",
    # site settings
    "SiteSettings", "SiteSettingsUpdate", "HeroImageResponse",
    # book
    "Book", "BookBase", "BookCreate",
    "BookScene", "BookSceneCreate", "BookSceneText",
    "ReadingProgress", "MAX_SCENES_PER_BOOK",
    # generation
    "GenerationStyle", "GenerationStyleBase", "GenerationStyleCreate",
    "PoppiconniGenerateRequest", "PoppiconniGenerateResponse",
    # poster
    "Poster", "PosterBase", "PosterCreate", "PosterUpdate", "PosterStatus",
    # character
    "CharacterTextUpdate",
    # common
    "DownloadEvent",
]
