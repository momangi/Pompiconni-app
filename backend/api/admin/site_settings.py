"""Admin site-settings router (Fase 4C router split)."""
from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from models import SiteSettingsUpdate
from services import settings_service


router = APIRouter()


@router.get("/settings")
async def admin_get_settings(email: str = Depends(verify_admin)):
    """Get site settings"""
    return await settings_service.get_admin_payload()


@router.put("/settings")
async def admin_update_settings(settings: SiteSettingsUpdate, email: str = Depends(verify_admin)):
    """Update site settings"""
    await settings_service.update_admin_settings(settings)
    return {"success": True}
