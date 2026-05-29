"""Admin themes router (Fase 4C router split).

CRUD metadata + check-delete. The ``/themes/{id}/upload-background``
endpoint (GridFS upload) stays in ``server.py``.
"""
from fastapi import APIRouter, Depends

from api.dependencies import verify_admin
from models import ThemeCreate, ThemeUpdate
from services import theme_service


router = APIRouter()


@router.post("/themes")
async def create_theme(theme: ThemeCreate, email: str = Depends(verify_admin)):
    return await theme_service.create_theme(theme)


@router.put("/themes/{theme_id}")
async def update_theme(theme_id: str, theme: ThemeUpdate, email: str = Depends(verify_admin)):
    return await theme_service.update_theme(theme_id, theme)


@router.get("/themes/check-delete/{theme_id}")
async def check_theme_delete(theme_id: str, email: str = Depends(verify_admin)):
    """Check if theme can be deleted and how many illustrations it has"""
    return await theme_service.check_delete(theme_id)


@router.delete("/themes/{theme_id}")
async def delete_theme(theme_id: str, force: bool = False, email: str = Depends(verify_admin)):
    """Delete theme. If force=true, unassign illustrations first."""
    return await theme_service.delete_theme(theme_id, force=force)
