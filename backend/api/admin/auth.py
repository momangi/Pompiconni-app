"""Admin auth router (mini-batch Auth & Maintenance).

The single ``POST /api/admin/login`` endpoint. Credentials are read
directly from :mod:`core.config.settings` (the same source the legacy
``server.py`` was using). Status codes and response shape are preserved
verbatim: ``401 Credenziali non valide`` on mismatch, ``LoginResponse``
on success.
"""
from fastapi import APIRouter, HTTPException

from core.config import settings as app_settings
from core.security import create_token
from models import LoginRequest, LoginResponse


router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    if (
        request.email == app_settings.admin_email
        and request.password == app_settings.admin_password
    ):
        token = create_token(request.email)
        return LoginResponse(token=token, email=request.email)
    raise HTTPException(status_code=401, detail="Credenziali non valide")
