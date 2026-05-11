"""Centralized application settings.

Reads environment variables once at import time. Behaviour:
  * In `development` / preview, legacy fallback values are kept so the
    existing preview environment continues to work unchanged.
  * In `production` (ENVIRONMENT=production), the constructor refuses to
    start if any critical variable is missing or matches an insecure
    legacy default. The RuntimeError is raised during uvicorn boot, so
    misconfigurations surface immediately and visibly.

This module must NOT have side-effects beyond reading env and validating
values. Database connections and other I/O live in `core/database.py`.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve repo paths -----------------------------------------------------------
# core/config.py -> core/ -> backend/
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# Load .env if present. dotenv is idempotent: re-import is safe.
load_dotenv(ROOT_DIR / ".env")


# Known-insecure JWT defaults that must NOT survive into production. ----------
_INSECURE_JWT_DEFAULTS = {
    "",
    "pompiconni_secret_key_2024",
    "poppiconni_secret_key_2024",
    "change-me",
    "secret",
}

# DB names that must NOT be used in production by accident. -------------------
_DEV_DB_NAMES_FORBIDDEN_IN_PROD = {
    "pompiconni_db",
    "poppiconni_dev",
}


class Settings:
    """Application settings, loaded once.

    Attribute names use snake_case. Legacy constants in ``server.py`` are
    re-exported from there as ``JWT_SECRET = settings.jwt_secret`` etc., so
    existing call sites continue to work without renaming.
    """

    def __init__(self) -> None:
        # ------------------------------------------------------------------
        # Environment
        # ------------------------------------------------------------------
        self.environment: str = os.environ.get("ENVIRONMENT", "development").strip().lower()
        self.is_production: bool = self.environment == "production"

        # ------------------------------------------------------------------
        # MongoDB — prefer MONGODB_URI / MONGODB_DB_NAME over the legacy
        # MONGO_URL / DB_NAME pair so that the deploy platform cannot
        # override our Atlas connection with its own managed Mongo.
        # ------------------------------------------------------------------
        self.mongo_uri: str = (
            os.environ.get("MONGODB_URI")
            or os.environ.get("MONGO_URL")
            or ""
        )
        self.mongo_db_name: str = (
            os.environ.get("MONGODB_DB_NAME")
            or os.environ.get("DB_NAME")
            or ""
        )

        # ------------------------------------------------------------------
        # JWT
        # ------------------------------------------------------------------
        self.jwt_secret: str = os.environ.get("JWT_SECRET", "")
        self.jwt_algorithm: str = "HS256"
        self.jwt_expiration_hours: int = 24

        # ------------------------------------------------------------------
        # Admin credentials (env-driven login, not from DB)
        # ------------------------------------------------------------------
        self.admin_email: str = os.environ.get("ADMIN_EMAIL", "")
        self.admin_password: str = os.environ.get("ADMIN_PASSWORD", "")

        # ------------------------------------------------------------------
        # CORS — read the env value but preserve the historical wildcard
        # default. A dedicated security-hardening phase will restrict this.
        # ------------------------------------------------------------------
        cors_raw = os.environ.get("CORS_ORIGINS", "*").strip()
        if cors_raw in ("", "*"):
            self.cors_origins: list[str] = ["*"]
        else:
            self.cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

        # ------------------------------------------------------------------
        # Third-party API keys (optional / Stripe currently disabled)
        # ------------------------------------------------------------------
        self.emergent_llm_key: str = os.environ.get("EMERGENT_LLM_KEY", "")
        self.stripe_secret_key: str = os.environ.get("STRIPE_SECRET_KEY", "")
        self.stripe_publishable_key: str = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
        self.stripe_webhook_secret: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

        # ------------------------------------------------------------------
        # File system paths
        # ------------------------------------------------------------------
        self.root_dir: Path = ROOT_DIR
        self.upload_dir: Path = ROOT_DIR / "uploads"
        self.upload_dir.mkdir(exist_ok=True)

        # ------------------------------------------------------------------
        # Apply DEV/preview fallbacks BEFORE production validation, so that
        # DEV behaves exactly like before the refactor.
        # ------------------------------------------------------------------
        self._apply_dev_fallbacks()

        if self.is_production:
            self._enforce_production_safety()

    # ----------------------------------------------------------------------
    # Internals
    # ----------------------------------------------------------------------
    def _apply_dev_fallbacks(self) -> None:
        """Reinstate the legacy fallbacks from `server.py` in non-prod envs."""
        if self.is_production:
            return
        if not self.mongo_uri:
            self.mongo_uri = "mongodb://localhost:27017"
        if not self.mongo_db_name:
            self.mongo_db_name = "pompiconni_db"
        if not self.jwt_secret:
            self.jwt_secret = "pompiconni_secret_key_2024"
        if not self.admin_email:
            self.admin_email = "admin@pompiconni.it"
        # admin_password is intentionally left empty if unset (legacy behavior).

    def _enforce_production_safety(self) -> None:
        """Refuse to start in production with missing/insecure settings.

        The error message lists every missing/insecure variable so that the
        operator can fix all of them in one go.
        """
        problems: list[str] = []

        if not self.mongo_uri:
            problems.append("MONGODB_URI is required in production")
        elif "localhost" in self.mongo_uri or "127.0.0.1" in self.mongo_uri:
            problems.append("MONGODB_URI must not point to localhost in production")

        if not self.mongo_db_name:
            problems.append("MONGODB_DB_NAME is required in production")
        elif self.mongo_db_name in _DEV_DB_NAMES_FORBIDDEN_IN_PROD:
            problems.append(
                f"MONGODB_DB_NAME='{self.mongo_db_name}' is a dev database "
                "and must not be used in production"
            )

        if not self.jwt_secret or self.jwt_secret in _INSECURE_JWT_DEFAULTS:
            problems.append(
                "JWT_SECRET is missing or set to an insecure legacy default"
            )

        if not self.admin_password:
            problems.append("ADMIN_PASSWORD is required in production")

        if problems:
            raise RuntimeError(
                "Refusing to start in ENVIRONMENT=production due to insecure "
                "or missing configuration:\n  - "
                + "\n  - ".join(problems)
            )


# Singleton: build at import so failures surface during uvicorn startup,
# not on the first request.
settings: Settings = Settings()
