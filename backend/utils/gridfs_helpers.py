"""Shared GridFS helpers (Fase 5/M2).

`get_gridfs_image` extracted verbatim from legacy ``server.py`` so it can
be reused by both public and admin books PDF routes without importing
from ``server.py`` (avoids circular imports).
"""
import logging

from bson import ObjectId

from core.database import gridfs_bucket


logger = logging.getLogger(__name__)


async def get_gridfs_image(file_id: str) -> bytes:
    """Helper function to get image bytes from GridFS."""
    try:
        grid_out = await gridfs_bucket.open_download_stream(ObjectId(file_id))
        return await grid_out.read()
    except Exception as e:
        logger.error(f"Error reading GridFS file {file_id}: {e}")
        raise


__all__ = ["get_gridfs_image"]
