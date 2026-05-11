"""MongoDB client and GridFS bucket singletons.

The Motor `AsyncIOMotorClient` opens connections lazily on first await, so
instantiation here is cheap and safe at import time.

Public surface kept stable for `server.py`:
    * ``client``         - the Motor client
    * ``db``             - the default database
    * ``gridfs_bucket``  - the GridFS bucket on that database

Plus helper functions for the new health probe and graceful shutdown.
"""
import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket

from .config import settings

logger = logging.getLogger(__name__)

# Motor client + DB + GridFS — eager construction, lazy connection. ------------
client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_db_name]
gridfs_bucket: AsyncIOMotorGridFSBucket = AsyncIOMotorGridFSBucket(db)


def get_db():
    """Return the default Motor database handle.

    Provided as a function so future FastAPI ``Depends(get_db)`` patterns
    plug in without a second refactor.
    """
    return db


def get_gridfs_bucket() -> AsyncIOMotorGridFSBucket:
    """Return the shared GridFS bucket."""
    return gridfs_bucket


async def ping_db(timeout_seconds: float = 2.0) -> bool:
    """Return True if the database responds to a ping within the timeout.

    Used by the readiness probe at ``/api/health``. Kept conservative
    (2 s default) so the probe stays responsive even when Atlas is slow.
    Never raises — any failure is logged and reported as ``False``.
    """
    try:
        await asyncio.wait_for(client.admin.command("ping"), timeout=timeout_seconds)
        return True
    except Exception as e:  # noqa: BLE001 - intentional: must not raise
        logger.warning(f"DB ping failed: {str(e)[:200]}")
        return False


async def close_client() -> None:
    """Close the Mongo client. Wired to FastAPI ``shutdown`` event."""
    client.close()
