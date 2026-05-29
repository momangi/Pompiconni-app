"""Database seeding (Fase 5/M4).

Verbatim port of the legacy ``init_database()`` previously inlined in
``server.py``. Side effects (collections touched, migrations applied,
log messages) are preserved identical so startup behaviour does not
drift.
"""
from datetime import datetime, timezone
import logging
import uuid

from core.config import settings
from core.database import db

from .seed_data import (
    SEED_BUNDLES,
    SEED_ILLUSTRATIONS,
    SEED_REVIEWS,
    SEED_THEMES,
    build_default_games,
)


logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with seed data if empty"""
    # Check if themes exist - use insert_many for batch performance
    themes_count = await db.themes.count_documents({})
    if themes_count == 0:
        now = datetime.now(timezone.utc)
        themes_to_insert = []
        for theme in SEED_THEMES:
            theme['createdAt'] = now
            theme['updatedAt'] = now
            theme['backgroundImageFileId'] = None
            theme['backgroundImageUrl'] = None
            theme['backgroundOpacity'] = 30
            themes_to_insert.append(theme)
        await db.themes.insert_many(themes_to_insert)
        logger.info("Seed themes inserted")
    else:
        # Migrate existing themes to add background fields if missing
        await db.themes.update_many(
            {"backgroundOpacity": {"$exists": False}},
            {"$set": {
                "backgroundOpacity": 30,
                "backgroundImageFileId": None,
                "backgroundImageUrl": None
            }}
        )
        logger.info("Existing themes migrated with background fields")

    # Check if illustrations exist - use insert_many for batch performance
    illustrations_count = await db.illustrations.count_documents({})
    if illustrations_count == 0:
        now = datetime.now(timezone.utc)
        illustrations_to_insert = []
        for illust in SEED_ILLUSTRATIONS:
            # Reset download count to 0 - no fake numbers
            illust['downloadCount'] = 0
            illust['createdAt'] = now
            illust['updatedAt'] = now
            # Set pdfFileId and imageFileId to None initially (files not uploaded yet)
            illust['pdfFileId'] = None
            illust['imageFileId'] = None
            illustrations_to_insert.append(illust)
        await db.illustrations.insert_many(illustrations_to_insert)
        logger.info("Seed illustrations inserted with zero download counts")

    # Check if bundles exist - use insert_many for batch performance
    bundles_count = await db.bundles.count_documents({})
    if bundles_count == 0:
        now = datetime.now(timezone.utc)
        bundles_to_insert = []
        for bundle in SEED_BUNDLES:
            bundle['createdAt'] = now
            bundle['updatedAt'] = now
            bundles_to_insert.append(bundle)
        await db.bundles.insert_many(bundles_to_insert)
        logger.info("Seed bundles inserted")
    else:
        # Migrate existing bundles to add new fields if missing
        await db.bundles.update_many(
            {"isActive": {"$exists": False}},
            {"$set": {
                "isActive": True,
                "sortOrder": 0,
                "badgeText": "",
                "subtitle": "",
                "currency": "EUR",
                "backgroundImageFileId": None,
                "backgroundImageUrl": None,
                "pdfFileId": None,
                "pdfUrl": None,
                "backgroundOpacity": 30,
                "updatedAt": datetime.now(timezone.utc)
            }}
        )
        # Add backgroundOpacity to bundles that don't have it
        await db.bundles.update_many(
            {"backgroundOpacity": {"$exists": False}},
            {"$set": {"backgroundOpacity": 30}}
        )
        # Add generatedPdf fields for auto-generation cache
        await db.bundles.update_many(
            {"generatedPdfFileId": {"$exists": False}},
            {"$set": {"generatedPdfFileId": None, "generatedPdfHash": None}}
        )
        # Migrate name to title if needed
        await db.bundles.update_many(
            {"title": {"$exists": False}, "name": {"$exists": True}},
            [{"$set": {"title": "$name", "subtitle": "$description"}}]
        )
        # Set sortOrder based on existing order
        bundles = await db.bundles.find({}, {"id": 1}).to_list(100)
        for idx, b in enumerate(bundles, 1):
            await db.bundles.update_one({"id": b['id'], "sortOrder": 0}, {"$set": {"sortOrder": idx}})
        logger.info("Existing bundles migrated with new fields")

    # Check if reviews exist - use insert_many for batch performance
    reviews_count = await db.reviews.count_documents({})
    if reviews_count == 0:
        await db.reviews.insert_many(SEED_REVIEWS)
        logger.info("Seed reviews inserted with is_approved field")

    # Initialize site_settings if not exists
    site_settings = await db.site_settings.find_one({"id": "global"})
    if not site_settings:
        await db.site_settings.insert_one({
            "id": "global",
            "show_reviews": True,
            "stripe_enabled": bool(settings.stripe_secret_key),
            "createdAt": datetime.now(timezone.utc)
        })
        logger.info("Site settings initialized")

    # Initialize default games if not exist
    games_count = await db.games.count_documents({})
    if games_count == 0:
        now = datetime.now(timezone.utc)
        default_games = build_default_games(now, lambda: str(uuid.uuid4()))
        await db.games.insert_many(default_games)
        logger.info("Default games initialized")
