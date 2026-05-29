"""Admin bundles router (Fase 4C router split).

CRUD metadata. The GridFS upload-background, upload-pdf, background-image
stream, download, download-pdf endpoints stay in ``server.py``.
"""
from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from core.database import gridfs_bucket
from models import BundleCreate, BundleUpdate
from services import bundle_service


router = APIRouter()


@router.get("/bundles")
async def admin_get_bundles(email: str = Depends(verify_admin)):
    """Get all bundles for admin (including inactive), sorted by sortOrder"""
    return await bundle_service.list_admin_bundles()


@router.post("/bundles")
async def create_bundle(bundle: BundleCreate, email: str = Depends(verify_admin)):
    return await bundle_service.create_bundle(bundle)


@router.put("/bundles/{bundle_id}")
async def update_bundle(bundle_id: str, bundle: BundleUpdate, email: str = Depends(verify_admin)):
    return await bundle_service.update_bundle(bundle_id, bundle)


@router.delete("/bundles/{bundle_id}")
async def delete_bundle(bundle_id: str, email: str = Depends(verify_admin)):
    from bson import ObjectId

    bundle = await bundle_service.prepare_admin_delete(bundle_id)

    # GridFS cleanup stays inline (heavy-media policy preserved).
    if bundle.get("pdfFileId"):
        try:
            await gridfs_bucket.delete(ObjectId(bundle["pdfFileId"]))
        except Exception:
            pass
    if bundle.get("backgroundImageFileId"):
        try:
            await gridfs_bucket.delete(ObjectId(bundle["backgroundImageFileId"]))
        except Exception:
            pass

    await bundle_service.finalize_admin_delete(bundle_id)
    return {"success": True}
