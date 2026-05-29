"""Shared route dependencies (Fase 4C router split).

`verify_admin` is the single canonical dependency for admin-only routes.
It is an alias of :func:`core.security.verify_token` and preserves the
exact legacy behaviour:

* extracts the bearer token via ``HTTPBearer``
* verifies JWT signature & expiration with the project secret
* returns the admin ``email`` (used to identify the caller in legacy code)
* raises ``HTTPException(401)`` on missing/invalid/expired token

No new roles, scopes, or permission changes are introduced here. The
alias exists to make admin routers explicit and to give us a single
point to evolve auth policy in the future.
"""
from core.security import verify_token

# Public alias used across `api/admin/*` routers.
verify_admin = verify_token

__all__ = ["verify_admin"]
