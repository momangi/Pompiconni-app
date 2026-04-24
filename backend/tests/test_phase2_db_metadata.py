"""
Direct MongoDB checks for Phase 2 variant metadata.
Uses motor + MONGO_URL + DB_NAME from backend/.env.
"""
from __future__ import annotations

import os
import pytest

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except Exception:  # pragma: no cover
    AsyncIOMotorClient = None

MONGO_URL = os.environ.get("MONGO_URL") or os.environ.get("MONGODB_URI") or ""
DB_NAME = os.environ.get("DB_NAME") or os.environ.get("MONGODB_DB_NAME") or ""

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def _skip_if_no_db():
    if not (AsyncIOMotorClient and MONGO_URL and DB_NAME):
        pytest.skip("motor or MONGO_URL/DB_NAME not available")


async def test_variant_metadata_shape(_skip_if_no_db):
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        # All derived variants
        cursor = db["fs.files"].find({"metadata.variant": "derived"})
        derived = [d async for d in cursor]
        # Expect at least 18 (3 originals × 3 sizes × 2 formats per DEV)
        assert len(derived) >= 18, (
            f"expected >=18 derived variants, got {len(derived)}"
        )

        allowed_sizes = {400, 800, 1600}
        allowed_formats = {"webp", "jpg", "png"}

        for d in derived:
            md = d.get("metadata") or {}
            assert md.get("variant") == "derived"
            assert "sourceFileId" in md and md["sourceFileId"], "sourceFileId missing"
            assert isinstance(md["sourceFileId"], str), "sourceFileId must be stored as str"
            assert md.get("variantSize") in allowed_sizes, (
                f"variantSize {md.get('variantSize')} not in {allowed_sizes}"
            )
            assert md.get("variantFormat") in allowed_formats, (
                f"variantFormat {md.get('variantFormat')} not in {allowed_formats}"
            )
            assert md.get("content_type")

        # Originals must exist and NOT be tagged as derived
        originals = await db["fs.files"].count_documents(
            {"metadata.variant": {"$ne": "derived"}}
        )
        assert originals >= 3, f"expected >=3 originals, got {originals}"
    finally:
        client.close()


async def test_no_orphan_variants(_skip_if_no_db):
    """Every derived variant's sourceFileId must resolve to an existing fs.files doc."""
    from bson import ObjectId

    client = AsyncIOMotorClient(MONGO_URL)
    try:
        db = client[DB_NAME]
        orphans = []
        cursor = db["fs.files"].find({"metadata.variant": "derived"})
        async for d in cursor:
            src = (d.get("metadata") or {}).get("sourceFileId")
            if not src:
                orphans.append(str(d.get("_id")))
                continue
            try:
                oid = ObjectId(src)
            except Exception:
                orphans.append(str(d.get("_id")))
                continue
            exists = await db["fs.files"].find_one({"_id": oid}, {"_id": 1})
            if not exists:
                orphans.append(str(d.get("_id")))
        assert not orphans, f"orphan variants found (sourceFileId not resolvable): {orphans}"
    finally:
        client.close()
