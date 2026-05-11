"""JWT-based authentication helpers.

Behaviour is intentionally identical to the previous implementation in
``server.py`` (HS256, 24h expiry, `sub=email`). Only the source of the
secret and algorithm changed: they now flow from ``core.config.settings``.
"""
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

# HTTPBearer dependency used by all admin endpoints.
security_bearer: HTTPBearer = HTTPBearer()


def create_token(email: str) -> str:
    """Issue a JWT for the given admin email."""
    payload = {
        "sub": email,
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> str:
    """Decode the JWT and return the embedded ``sub`` (admin email).

    Raises 401 on expired or invalid tokens — identical messages to the
    previous behavior so the frontend keeps working unchanged.
    """
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token scaduto")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token non valido")
