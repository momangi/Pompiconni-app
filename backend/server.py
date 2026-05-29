"""Application entry point (Fase 5/M4).

After the M4 bootstrap cleanup, this file is intentionally minimal:
it only wires the FastAPI app, top-level routers, lifecycle hooks,
static mount, CORS and Kubernetes health probes. All domain routing,
seed data, indexes and migrations live in dedicated packages
(``api/registry.py``, ``lifecycle/``).
"""
import logging

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from api.registry import register_routers
from core.config import settings
from core.database import close_client, ping_db
from lifecycle.seeder import init_database
from lifecycle.startup import ensure_indexes_and_migrations


# ============== LOGGING ==============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


# ============== APP + ROUTERS ==============
app = FastAPI()
api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin")


# ============== PUBLIC ROOT ==============
@api_router.get("/")
async def root():
    return {"message": "Poppiconni API v1.0", "status": "online"}


# ============== STATIC FILES ==============
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")


# ============== DOMAIN ROUTERS ==============
register_routers(api_router, admin_router)
app.include_router(api_router)
app.include_router(admin_router)


# ============== HEALTH PROBES ==============
# ``/`` and ``/health`` : K8s LIVENESS probes. They must NOT touch the DB
#   so the pod is reported alive even when Atlas is momentarily slow.
# ``/api/health``       : READINESS probe. Pings MongoDB with a short
#   timeout and returns HTTP 503 if the database is unreachable, so load
#   balancers can take this instance out of rotation until Atlas is back.
@app.get("/")
async def _root_health():
    return {"status": "ok", "service": "poppiconni"}


@app.get("/health")
async def _liveness():
    return {"status": "ok"}


@app.get("/api/health")
async def _readiness():
    db_ok = await ping_db(timeout_seconds=2.0)
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unreachable"},
        )
    return {"status": "ok", "db": "ok"}


# ============== CORS ==============
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== LIFECYCLE HOOKS ==============
@app.on_event("startup")
async def startup_event():
    """
    Best-effort startup: seed data + index creation are wrapped in
    try/except so the pod never enters CrashLoopBackOff if Atlas is
    momentarily slow or a single migration fails. Health endpoints
    work regardless.
    """
    try:
        await init_database()
    except Exception as e:
        logger.error(f"init_database failed (non-fatal): {str(e)[:200]}")
    await ensure_indexes_and_migrations()


@app.on_event("shutdown")
async def shutdown_db_client():
    await close_client()
