"""Startup indexes & migrations (Fase 5/M4).

Verbatim port of the legacy ``startup_event()`` body previously inlined
in ``server.py``: TTL index on ``download_limits``, the full set of
performance indexes (Fase 1), and post-deploy data migrations for
illustrations/posters. Side effects and log messages match the legacy
implementation.
"""
from datetime import datetime, timezone
import logging

from core.database import db


logger = logging.getLogger(__name__)


# Performance indexes: ``create_index`` is idempotent and a no-op when an
# equivalent index already exists. All indexes here support hot-path
# queries grepped from the codebase.
PERF_INDEXES = [
    # illustrations
    ("illustrations", [("id", 1), ("isPublished", 1)], {"name": "ix_id_isPublished"}),
    ("illustrations", [("isPublished", 1)],            {"name": "ix_isPublished"}),
    # posters
    ("posters",       [("id", 1), ("status", 1)],      {"name": "ix_id_status"}),
    ("posters",       [("status", 1)],                 {"name": "ix_status"}),
    # books
    ("books",         [("id", 1)],                     {"name": "ix_id"}),
    ("books",         [("slug", 1)],                   {"name": "ix_slug"}),
    # book_scenes
    ("book_scenes",   [("bookId", 1), ("sceneNumber", 1)], {"name": "ix_bookId_sceneNumber"}),
    ("book_scenes",   [("id", 1), ("bookId", 1)],      {"name": "ix_id_bookId"}),
    # bundles
    ("bundles",       [("id", 1)],                     {"name": "ix_id"}),
    # games
    ("games",         [("id", 1)],                     {"name": "ix_id"}),
    ("games",         [("slug", 1)],                   {"name": "ix_slug"}),
    # themes
    ("themes",        [("id", 1)],                     {"name": "ix_id"}),
    # game_level_backgrounds
    ("game_level_backgrounds", [("id", 1)],            {"name": "ix_id"}),
    # generation_styles
    ("generation_styles", [("id", 1), ("userId", 1)],  {"name": "ix_id_userId"}),
    # character_images
    ("character_images", [("trait", 1)],               {"name": "ix_trait"}),
    # reviews
    ("reviews",       [("is_approved", 1)],            {"name": "ix_is_approved"}),
    # reading_progress
    ("reading_progress", [("bookId", 1), ("visitorId", 1)], {"name": "ix_bookId_visitorId"}),
    # download_limits (extra: key lookup for rate limiting)
    ("download_limits", [("key", 1)],                  {"name": "ix_key"}),
    # admins
    ("admins",        [("email", 1)],                  {"name": "ix_email", "unique": True}),
    # site_settings (single doc, but cheap)
    ("site_settings", [("id", 1)],                     {"name": "ix_id"}),
]


async def ensure_indexes_and_migrations():
    """
    Best-effort: TTL index + performance indexes + post-deploy migrations.

    Mirrors the legacy ``startup_event`` body verbatim — every block is
    individually safe to fail (caught) so the pod never enters
    CrashLoopBackOff because of a transient Atlas slowdown or a
    pre-existing index conflict.
    """
    # Create TTL index for download_limits (auto-delete after 30 days)
    try:
        await db.download_limits.create_index("expiresAt", expireAfterSeconds=0)
        logger.info("TTL index created for download_limits")
    except Exception as e:
        # Index might already exist
        logger.debug(f"TTL index creation: {str(e)}")

    # ============== PERFORMANCE INDEXES (Fase 1) ==============
    created, skipped = 0, 0
    for coll_name, keys, opts in PERF_INDEXES:
        try:
            await db[coll_name].create_index(keys, **opts)
            created += 1
        except Exception as e:
            skipped += 1
            logger.debug(f"Index {coll_name}.{opts.get('name')} skipped: {str(e)[:80]}")
    logger.info(f"Performance indexes ensured: created_or_existing={created}, skipped={skipped}")

    # Migrate existing illustrations: set isPublished=True if field missing
    migration_result = await db.illustrations.update_many(
        {"isPublished": {"$exists": False}},
        {"$set": {"isPublished": True, "publishedAt": datetime.now(timezone.utc)}}
    )
    if migration_result.modified_count > 0:
        logger.info(f"Migrated {migration_result.modified_count} illustrations to published status")

    # Migrate existing illustrations: set downloadEnabled=True if field missing
    download_migration = await db.illustrations.update_many(
        {"downloadEnabled": {"$exists": False}},
        {"$set": {"downloadEnabled": True}}
    )
    if download_migration.modified_count > 0:
        logger.info(f"Migrated {download_migration.modified_count} illustrations with downloadEnabled=True")

    # Migrate existing posters: set downloadEnabled=True if field missing
    poster_migration = await db.posters.update_many(
        {"downloadEnabled": {"$exists": False}},
        {"$set": {"downloadEnabled": True}}
    )
    if poster_migration.modified_count > 0:
        logger.info(f"Migrated {poster_migration.modified_count} posters with downloadEnabled=True")

    logger.info("Database initialized")
