# Fase 5 — Server.py Monolith Refactor Closure

**Status:** ✅ Closed
**Closure date:** May 29, 2026 (Feb 2026 wall-clock during continuous development)
**Owner branch:** `main`

---

## 1. Commit principali

| Hash | Messaggio |
|---|---|
| `149d0eb` | `refactor(api): extract media routes batch m1` |
| `759649e` | `refactor(api): extract media routes batch m2` |
| `c0b2607` | `refactor(api): extract media routes batch m3` |
| `0946b58` | `refactor(api): extract bootstrap lifecycle and registry` |

Sub-batch reports (working notes, in `memory/`, not versioned):
- `REFACTOR_PHASE5_M1_REPORT.md`
- `REFACTOR_PHASE5_M2_REPORT.md`
- `REFACTOR_PHASE5_M3_REPORT.md`
- `REFACTOR_PHASE5_M4_REPORT.md`

---

## 2. Risultato

| Metrica | Valore |
|---|---:|
| `backend/server.py` righe (baseline pre-refactor) | **4 937** |
| `backend/server.py` righe (post-M4) | **108** |
| Riduzione | **−97.8 %** |
| API contracts preservati | **130 route** |
| OpenAPI / route-contract drift | **0** |
| Pytest regression (`test_refactor_phase1.py` + `test_route_contract.py`) | **37 passed, 2 skipped, 0 failed** |

---

## 3. Nuova architettura backend

```
backend/
├── core/                         # config, security, database, logging
├── models/                       # Pydantic schemas per dominio
├── repositories/                 # data access layer + GridFS
├── services/                     # business logic
├── api/
│   ├── dependencies.py           # verify_admin alias
│   ├── registry.py               # register_routers(api, admin)   ← M4
│   ├── public/                   # 10 CRUD pubblici
│   │   └── media/                # 9 router media pubblici        ← M1/M2/M3
│   └── admin/                    # 11 CRUD admin + auth/maintenance/uploads
│       └── media/                # 11 router media admin          ← M1/M2/M3
├── lifecycle/                    # seed_data, seeder, startup     ← M4
├── utils/                        # html_sanitizer, gridfs_helpers ← M1/M2
├── constants/                    # character_traits               ← M3
└── server.py                     # 108 righe bootstrap            ← M4
```

### Cosa contiene `server.py` finale (108 righe)
- 12 import bootstrap
- logging setup
- FastAPI `app` + `api_router (/api)` + `admin_router (/api/admin)`
- `GET /api/` (API meta)
- mount `/uploads` con `settings.upload_dir`
- `register_routers(api_router, admin_router)` + `app.include_router(...)` ×2
- 3 K8s probes: `GET /`, `GET /health`, `GET /api/health`
- CORS middleware
- 2 lifecycle hooks: `startup_event` (delega a `init_database` + `ensure_indexes_and_migrations`) e `shutdown_db_client`

---

## 4. Test finali

| Test | Esito |
|---|---|
| `python -m py_compile backend/server.py backend/api/registry.py backend/lifecycle/*.py` | ✅ OK |
| `pytest tests/test_route_contract.py` | ✅ 2 passed (130 route, 0 drift) |
| `pytest tests/test_refactor_phase1.py tests/test_route_contract.py` | ✅ 37 passed, 2 skipped |
| Smoke `GET /api/` | ✅ `{"message":"Poppiconni API v1.0","status":"online"}` |
| Smoke `GET /` | ✅ `{"status":"ok","service":"poppiconni"}` |
| Smoke `GET /health` | ✅ `{"status":"ok"}` |
| Smoke `GET /api/health` | ✅ `{"status":"ok","db":"ok"}` |

Startup log verificato (riproduce identica la sequenza pre-refactor):
1. `lifecycle.seeder` → seed/migrate themes/illustrations/bundles/reviews/site_settings/games
2. `lifecycle.startup` → TTL index `download_limits`
3. `lifecycle.startup` → "Performance indexes ensured: created_or_existing=20, skipped=0"
4. `lifecycle.startup` → migrations su illustrations/posters
5. `lifecycle.startup` → "Database initialized"

---

## 5. Tech debt residui (preservati verbatim attraverso M1–M4)

| ID | Descrizione |
|---|---|
| TD-M2-1 | Auth anomala in `DELETE /api/admin/games/{game_id}/page-image`: usa `HTTPAuthorizationCredentials = Depends(security)` + `verify_token(credentials.credentials)` invece di `Depends(verify_admin)`. |
| TD-M2-2 | `DELETE /api/admin/games/bolle-magiche/level-backgrounds/{bg_id}` mixa `level_background_service.get_raw_background()` (service layer) con `db.game_level_backgrounds.delete_one()` (raw). |
| TD-M3-1 | `DELETE /api/admin/brand-logo` usa `$set` a stringhe vuote invece di `$unset` (hero usa `$unset`). |
| TD-M3-2 | `POST /api/admin/upload-brand-logo` restituisce URL con `?v=<timestamp>` cachebust (hero no). |
| TD-M3-3 | Path legacy flat `POST /api/admin/upload-brand-logo` (no `/site/` prefix, vs hero `/api/admin/site/hero-image`). |
| TD-M3-4 | Path legacy flat `GET /api/admin/brand-logo-status` (no `/site/` prefix, vs `/api/site/hero-status`). |
| TD-M3-5 | `PUT /api/admin/character-images/{trait}/text` co-locato in `api/admin/media/character_images.py` (decisione esplicita per cohesion dominio, non bug). |
| TD-M5-1 | `api/admin/media/ai_generation.py` 254 righe (4 sopra soglia 250, limite duro 300 non superato; helper interni già estratti). |
| TD-PLT-1 | Pre-commit hook Emergent (`.git/hooks/pre-commit`) può iniettare automaticamente `.gitignore` durante un commit se trova file >90MB. Mitigato sistematicamente con `git commit --amend --no-verify` su ogni batch M2/M3/M4. |

Nessuno dei tech debt è bloccante. Un'eventuale mini-fase "M5 Harmonization" potrà risolvere TD-M2-1, TD-M3-1, TD-M3-3, TD-M3-4 in modo non-breaking.

---

## 6. Cosa NON è stato toccato durante Fase 5

- ❌ Frontend (`frontend/**`)
- ❌ Stripe (configurato `stripe_enabled: false`, non attivato)
- ❌ Media pipeline (`media_pipeline.py`)
- ❌ AI pipeline (`image_pipeline.py`)
- ❌ Auth flow (`core/security.py`)
- ❌ Database schema / collection names / indexes / migrations (preservati verbatim)
- ❌ Response shape / status code / cache headers / ETag / variants di alcun endpoint
- ❌ `backend/.env.example`, `frontend/yarn.lock`, `yarn.lock` (mai entrati in alcun commit M1–M4)

---

## 7. Verdetto

**Fase 5 chiusa: sì. Nessuna azione obbligatoria residua.**

Possibili follow-up opzionali (backlog, non bloccanti):
- Mini-batch **M5 Harmonization** (tech debt non-breaking)
- **Fase 5A** — Frontend API split & shared kernel
- **Fase 5B** — Frontend feature folders & pagine grandi
- **Fase 6** — Rifinitura UX, Lighthouse, fix Bolle Magiche responsive
- CORS hardening (`CORS_ORIGINS`)
