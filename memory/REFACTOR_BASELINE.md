# 📋 REFACTOR BASELINE — Poppiconni (Fase 0)

> **Data:** 2026-02 (sessione corrente)
> **Scope:** osservazione read-only pre-refactor. **Nessuna modifica al codice, al DB, alle dipendenze.**
> **Stato app:** Preview = Atlas DEV (`poppiconni_dev`). Production = live su `https://poppiconni.it` (NON toccato in questa fase).
> **Tutti i valori sensibili sono sanitizzati.** Nessun secret reale è presente in questo documento.

---

## 1. RUNTIME — Stato attuale

### 1.1 Comando di avvio (supervisor)
```
/root/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1 --reload
directory=/app/backend
autostart=true
```
**→ `server.py` deve continuare a esportare `app` (vincolo deploy Emergent).**

### 1.2 Smoke import backend
```
python -c "import server"  →  OK (app type=FastAPI)
```

### 1.3 py_compile su tutti i .py backend
```
server.py, streaming.py, media_pipeline.py, image_pipeline.py,
pdf_generator.py, create_indexes.py, migrate_variants.py
→ All OK (no syntax errors)
```

### 1.4 Frontend build
```
yarn build → Compiled successfully (26.5s)
  main JS:   352 KB gzip
  main CSS:   15 KB gzip
```

---

## 2. HEALTH ENDPOINTS — fotografia attuale

| Endpoint | Definito in server.py | Da preview URL (Cloudflare/ingress) | Da localhost:8001 | Note |
|---|---|---|---|---|
| `GET /` | ✅ riga 5024 | 200 | 200 `{"status":"ok","service":"poppiconni"}` | Health root |
| `GET /health` | ✅ riga 5028 | **200 ma serve l'HTML del frontend** (ingress route `/health` → React) | 200 `{"status":"ok"}` | **L'ingress non instrada `/health` al backend perché non ha prefisso `/api`.** Funziona solo internamente per la K8s readiness probe. |
| `GET /api/health` | ✅ riga 5029 | 200 `{"status":"ok"}` | 200 `{"status":"ok"}` | **Affidabile lato esterno.** Questo è il vero health check pubblico. |
| `GET /api/` | ✅ riga 861 (`api_router`) | 200 `{"message":"Poppiconni API v1.0","status":"online"}` | 200 | OK |

**Nota:** entrambi `/health` e `/api/health` sono mappati alla stessa funzione (riga 5029-5030: doppio decoratore).

**Target Fase 4A:** mantenere identico questo comportamento. Non aggiungere ancora controllo DB nel health (vedi §10 raccomandazione: in fase futura, `/api/health` può differenziare ready vs alive).

---

## 3. ENVIRONMENT — variabili lette dal backend

### 3.1 Variabili effettivamente referenziate (`grep os.environ` su /app/backend)

| Variabile | File | Default attuale | Criticità in PROD | Note |
|---|---|---|---|---|
| `MONGODB_URI` | server.py:37 | (fallback su MONGO_URL) | **P0 — obbligatoria** | Letta per prima. |
| `MONGO_URL` | server.py:38 + create_indexes.py + migrate_variants.py + tests | (fallback su localhost in alcuni script!) | P0 in PROD | Fallback `'mongodb://localhost:27017'` in server.py:39 → **rischio se MONGODB_URI assente in PROD** |
| `MONGODB_DB_NAME` | server.py:42 | (fallback su DB_NAME) | **P0 — obbligatoria** | |
| `DB_NAME` | server.py:43 + create_indexes.py + migrate_variants.py + tests | fallback `'pompiconni_db'` in server.py:44 | P0 in PROD | **Rischio fallback** |
| `JWT_SECRET` | server.py:58 | **`'pompiconni_secret_key_2024'`** (hardcoded!) | **P0 CRITICO** | **In PROD non deve mai partire con questo valore** |
| `ADMIN_EMAIL` | server.py:63 | `'admin@pompiconni.it'` | P1 | |
| `ADMIN_PASSWORD` | server.py:64 | `''` (vuoto) | P0 in PROD | Vuoto → login impossibile (safe by accident) |
| `ENVIRONMENT` | (NON LETTA OGGI in server.py!) | n/d | n/d | **OSSERVAZIONE: la var è impostata in `.env` ma il backend non la legge mai.** Verrà introdotta in Fase 4A per il fail-fast in PROD. |
| `EMERGENT_LLM_KEY` | server.py:2327 + image_pipeline.py:182,289,336 | (verifica in-line a uso) | P1 (solo per generazione AI) | |
| `MAX_REFERENCE_IMAGES_PER_USER` | image_pipeline.py:32 | `'20'` | P3 | |
| `MAX_SYNC_RETRIES` | image_pipeline.py:35 | `'5'` | P3 | |
| `MAX_ASYNC_RETRIES` | image_pipeline.py:36 | `'5'` | P3 | |
| `STRIPE_SECRET_KEY` | server.py:53 | `''` | P3 (Stripe disabilitato) | |
| `STRIPE_PUBLISHABLE_KEY` | server.py:54 | `''` | P3 | |
| `STRIPE_WEBHOOK_SECRET` | server.py:55 | `''` | P3 | |
| `CORS_ORIGINS` | (NON LETTA OGGI! impostata in `.env` ma server.py usa `allow_origins=["*"]` hardcoded) | n/d | P2 | OSSERVAZIONE: env var ignorata, c'è hardcoded `["*"]` nel middleware (server.py:5039) |
| `BACKEND_DIRECT_URL` | tests only | — | n/d | Per test |
| `TARGET_ILLUST_ID` | tests only | — | n/d | Per test |
| `REACT_APP_BACKEND_URL` | tests only (e frontend) | — | P0 frontend | |

### 3.2 Backend .env attuale (chiavi presenti, valori sanitizzati)
```
ADMIN_EMAIL=         (settato)
ADMIN_PASSWORD=      (settato)
CORS_ORIGINS=        (settato ma NON LETTO dal codice)
DB_NAME=             (settato)
EMERGENT_LLM_KEY=    (settato)
ENVIRONMENT=         development   ← settato ma NON LETTO dal codice
JWT_SECRET=          (settato)
MONGODB_DB_NAME=     poppiconni_dev
MONGODB_URI=         mongodb+srv://...@poppiconni-dev....mongodb.net/poppiconni_dev?...
MONGO_URL=           (settato, alias compat)
```

### 3.3 Frontend .env (chiavi)
```
ENABLE_HEALTH_CHECK
REACT_APP_BACKEND_URL
REACT_APP_ENABLE_VISUAL_EDITS
WDS_SOCKET_PORT
```

### 3.4 Hardcoded URL/credenziali nel codice
- ✅ **Frontend**: nessun `localhost`/`127.0.0.1`/`:8001` in `/app/frontend/src` (grep pulito)
- ⚠️ **Backend `server.py`**: fallback `'mongodb://localhost:27017'` (riga 39) e `'pompiconni_db'` (riga 44) e `'pompiconni_secret_key_2024'` (riga 58)
  - Questi fallback **NON sono pericolosi in DEV** (la preview usa Atlas regolarmente)
  - **Sono pericolosi in PROD** se le env critiche non sono settate
  - **Target Fase 4A**: `core/config.py` farà fail-fast in PROD per `MONGODB_URI`, `MONGODB_DB_NAME`, `JWT_SECRET`, `ADMIN_PASSWORD`

---

## 4. MONGODB ATLAS DEV — snapshot read-only

### 4.1 Connessione
- **Ping Atlas:** ✅ OK
- **Cluster:** `poppiconni-dev.b0fmklq.mongodb.net`
- **DB:** `poppiconni_dev`
- **ENVIRONMENT app:** `development` (var letta dal `.env` ma non ancora dal codice)

### 4.2 Conteggio documenti per collezione (baseline da preservare)

| Collezione | Documenti |
|---|---|
| `admins` | 1 |
| `book_scenes` | 1 |
| `books` | 3 |
| `bundles` | 4 |
| `character_images` | 3 |
| `download_events` | 6 |
| `download_limits` | 0 |
| `fs.chunks` | 132 |
| `fs.files` | 66 |
| `game_level_backgrounds` | 0 |
| `games` | 3 |
| `generation_styles` | 1 |
| `illustrations` | 23 |
| `posters` | 2 |
| `reading_progress` | 0 |
| `reviews` | 15 |
| `site_settings` | 1 |
| `themes` | 6 |
| **TOTAL** | **18 collezioni / 270+ documenti** |

> Questi numeri servono da **regression check**: dopo ogni fase del refactor, eseguire un ri-conteggio e verificare 0 perdite/aggiunte impreviste.

### 4.3 OSSERVAZIONE — Collezione `admins`
- È presente una collezione `admins` con 1 documento. Tuttavia il codice in `server.py:1320-1325` esegue login confrontando solo `ADMIN_EMAIL`/`ADMIN_PASSWORD` da env.
- **La collezione `admins` non viene letta dal flusso di login attuale.** Forse residuo o predisposizione futura. **Da chiarire prima di Fase 4B (dominio auth).**

---

## 5. INVENTARIO ENDPOINT — completo, statico

> Estratto via AST parsing di `server.py`. **Nessuna chiamata eseguita per costruirlo.**
> Auth detection è euristica: marcata `[AUTH]` se la signature contiene `Depends(verify_token)` nei primi 500 char della funzione. **Casi marcati `[PUB]` per route admin vanno verificati manualmente prima di refactor** (vedi §5.4).

### 5.1 Statistiche
- **Totale endpoint:** 130 (escluse 2 funzioni lifecycle `@app.on_event`)
- **`api_router` (prefix `/api`):** 57 endpoint
- **`admin_router` (prefix `/api/admin`):** 70 endpoint
- **`app` direct (no prefix):** 3 endpoint (`/`, `/health`, `/api/health`)

### 5.2 ANOMALIA STRUTTURALE — route admin registrate nel router sbagliato

L'inventario rivela che **5 route relative ai giochi sono dichiarate sotto `api_router` ma puntano a path che iniziano con `/admin/games/...`**:

| Riga | Path effettivo | Path corretto se nel router giusto |
|---|---|---|
| 3956 | `/api/admin/games` (via api_router + `/admin/games`) | uguale |
| 3975 | `/api/admin/games` (POST) | uguale |
| 4005 | `/api/admin/games/{game_id}` (PUT) | uguale |
| 4046 | `/api/admin/games/{game_id}` (DELETE) | uguale |
| 4080 | `/api/admin/games/{game_id}/thumbnail` | uguale |
| 4125 | `/api/admin/games/{game_id}/card-image` | uguale |
| 4190 | `/api/admin/games/{game_id}/card-image` (DELETE) | uguale |
| 4224 | `/api/admin/games/{game_id}/page-image` | uguale |
| 4289 | `/api/admin/games/{game_id}/page-image` (DELETE) | uguale |
| 4356 | `/api/admin/games/bolle-magiche/level-backgrounds` | uguale |
| 4371 | `/api/admin/games/bolle-magiche/level-backgrounds` (POST) | uguale |
| 4428 | `/api/admin/games/bolle-magiche/level-backgrounds/{bg_id}` (PUT) | uguale |
| 4459 | `/api/admin/games/bolle-magiche/level-backgrounds/{bg_id}/image` | uguale |
| 4497 | `/api/admin/games/bolle-magiche/level-backgrounds/{bg_id}` (DELETE) | uguale |

> **Effetto utente:** nessuno — i path finali sono identici (`/api/admin/games/...` = `/api` + `/admin/games` ≡ `/api/admin` + `/games`). Funziona "per caso".
>
> **Effetto Fase 4C:** lo split router dovrà **preservare i path esatti**, quindi raggrupperò semanticamente queste route nel router admin/games, ma i path nel decoratore resteranno invariati. Documentato come **decisione obbligatoria di Fase 4C**.

### 5.3 Endpoint pubblici (`api_router`, 57)

```
GET    /                                                             [PUB]
GET    /admin/games                                                  [AUTH] ← in api_router, vedi §5.2
POST   /admin/games                                                  [AUTH]
GET    /admin/games/bolle-magiche/level-backgrounds                  [AUTH] q=user_id
POST   /admin/games/bolle-magiche/level-backgrounds                  [AUTH]
DELETE /admin/games/bolle-magiche/level-backgrounds/{bg_id}          [AUTH]
PUT    /admin/games/bolle-magiche/level-backgrounds/{bg_id}          [AUTH]
POST   /admin/games/bolle-magiche/level-backgrounds/{bg_id}/image    [AUTH]
DELETE /admin/games/{game_id}                                        [AUTH]
PUT    /admin/games/{game_id}                                        [AUTH]
DELETE /admin/games/{game_id}/card-image                             [AUTH]
POST   /admin/games/{game_id}/card-image                             [AUTH]
DELETE /admin/games/{game_id}/page-image                             [PUB ?] ← da verificare manualmente
POST   /admin/games/{game_id}/page-image                             [AUTH]
POST   /admin/games/{game_id}/thumbnail                              [AUTH]
GET    /books                                                        [PUB]
GET    /books/{book_id}                                              [PUB]
GET    /books/{book_id}/cover                                        [PUB] q=w,format
GET    /books/{book_id}/pdf                                          [PUB]
GET    /books/{book_id}/progress/{visitor_id}                        [PUB]
POST   /books/{book_id}/progress/{visitor_id}                        [PUB]
GET    /books/{book_id}/scene/{scene_number}/colored-image           [PUB]
GET    /books/{book_id}/scene/{scene_number}/lineart-image           [PUB]
GET    /brand-kit                                                    [PUB]
GET    /bundles                                                      [PUB]
GET    /bundles/{bundle_id}/background-image                         [PUB]
GET    /bundles/{bundle_id}/download                                 [PUB]
GET    /bundles/{bundle_id}/download-pdf                             [PUB]
GET    /character-images                                             [PUB]
GET    /character-images/{trait}/image                               [PUB]
GET    /games                                                        [PUB]
GET    /games/bolle-magiche/level-backgrounds                        [PUB]
GET    /games/bolle-magiche/level-backgrounds/{bg_id}/image          [PUB]
GET    /games/{slug}                                                 [PUB]
GET    /games/{slug}/card-image                                      [PUB] q=w,format
GET    /games/{slug}/page-image                                      [PUB] q=w,format
GET    /games/{slug}/thumbnail                                       [PUB] q=w,format
GET    /illustrations                                                [PUB] q=themeId,isFree
GET    /illustrations/{illustration_id}                              [PUB]
POST   /illustrations/{illustration_id}/download                     [PUB]
GET    /illustrations/{illustration_id}/download-status              [PUB]
GET    /illustrations/{illustration_id}/image                        [PUB] q=w,format
GET    /illustrations/{illustration_id}/image-status                 [PUB]
GET    /posters                                                      [PUB]
GET    /posters/{poster_id}                                          [PUB]
GET    /posters/{poster_id}/download                                 [PUB]
GET    /posters/{poster_id}/image                                    [PUB] q=w,format
GET    /reviews                                                      [PUB]
GET    /search/illustrations                                         [PUB] q=q,limit
GET    /site-settings                                                [PUB]
GET    /site/brand-logo                                              [PUB] q=w,format
GET    /site/hero-image                                              [PUB] q=w,format
GET    /site/hero-status                                             [PUB]
GET    /theme-colors                                                 [PUB]
GET    /themes                                                       [PUB]
GET    /themes/{theme_id}                                            [PUB]
GET    /themes/{theme_id}/background-image                           [PUB] q=w,format
```

### 5.4 Endpoint admin (`admin_router`, 70)

```
POST   /login                                                        [PUB]   ← login pubblico, OK
GET    /dashboard                                                    [AUTH]
GET    /books, POST /books, PUT /books/{id}, DELETE /books/{id}      [AUTH]
POST   /books/{id}/cover                                             [AUTH] q=file
GET    /books/{id}/pdf                                               [AUTH]
GET    /books/{id}/scenes, POST /books/{id}/scenes                   [AUTH]
PUT/DELETE /books/{id}/scenes/{scene_id}                             [AUTH]
POST   /books/{id}/scenes/{scene_id}/colored-image                   [AUTH] q=file
POST   /books/{id}/scenes/{scene_id}/lineart-image                   [AUTH] q=file
GET    /brand-logo-status, POST /upload-brand-logo, DELETE /brand-logo  [AUTH]
GET    /bundles, POST /bundles, PUT/DELETE /bundles/{id}             [AUTH]
POST   /bundles/{id}/upload-background, /upload-pdf                  [AUTH]
GET    /character-images                                             [AUTH]
DELETE /character-images/{trait}                                     [AUTH]
PUT    /character-images/{trait}/text                                [AUTH]
POST   /character-images/{trait}/upload                              [AUTH]
GET    /download-stats                                               [AUTH]
POST   /generate-illustration, /generate-poppiconni                  [AUTH]
GET    /illustrations, POST /illustrations                           [AUTH] q=themeId,isPublished
PUT    /illustrations/{id}, DELETE /illustrations/{id}               [AUTH]
PUT    /illustrations/{id}/download-enabled                          [AUTH]
PUT    /illustrations/{id}/publish                                   [AUTH]
PUT    /illustrations/{id}/theme                                     [AUTH]
POST   /illustrations/{id}/attach-image, /attach-pdf                 [AUTH]
POST   /maintenance/fix-brand-name                                   [AUTH]
GET    /pipeline-status/{generation_id}                              [AUTH]
GET    /posters, POST /posters                                       [AUTH]
GET    /posters/stats/summary                                        [AUTH]
GET    /posters/{id}, PUT /posters/{id}, DELETE /posters/{id}        [AUTH]
PUT    /posters/{id}/download-enabled                                [AUTH]
POST   /posters/{id}/upload-image, /upload-pdf                       [AUTH]
POST   /reset-fake-counters                                          [AUTH]
GET    /reviews, PUT /reviews/{id}, DELETE /reviews/{id}             [AUTH]
GET    /settings, PUT /settings                                      [AUTH]
POST   /site/hero-image, DELETE /site/hero-image                     [AUTH]
PUT    /social-links                                                 [AUTH]
GET    /styles, POST /styles, DELETE /styles/{id}                    [AUTH]
GET    /styles/{id}/reference-image                                  [AUTH]
POST   /styles/{id}/upload-reference                                 [AUTH]
POST   /themes                                                       [AUTH]
GET    /themes/check-delete/{id}                                     [AUTH]
DELETE /themes/{id}                                                  [AUTH] q=force
PUT    /themes/{id}                                                  [AUTH]
POST   /themes/{id}/upload-background                                [AUTH]
POST   /upload                                                       [AUTH] q=file,file_type
```

### 5.5 Auth check (live curl, read-only)
- `POST /api/admin/login` con credenziali test → **200, token ricevuto (len 143)**
- Senza token: `GET /api/admin/dashboard` → **403** ✅ (auth enforced)
- Con token: `dashboard`, `illustrations`, `posters`, `settings`, `games`, `books`, `bundles` → **tutti 200** ✅

---

## 6. RESPONSE SHAPE — chiavi top-level osservate (subset read-only)

> Solo per endpoint pubblici testati. Shape derivata da `json.load + sorted(keys)`. Lo schema **non è dichiarato** in OpenAPI (response_model raramente usato), quindi shape è "de facto" non "de jure".

| Endpoint | Chiavi top-level di un item della response | Note |
|---|---|---|
| `GET /api/themes` | `backgroundImageFileId, backgroundImageUrl, backgroundOpacity, color, createdAt, description, icon, id, illustrationCount, name, updatedAt` | ✅ pulito, **no `_id`** |
| `GET /api/illustrations` | `_id, createdAt, description, downloadCount, downloadEnabled, id, isFree, isPublished, price, publishedAt, themeId, title, updatedAt` | **🔴 `_id` LEAK** (vedi §8.1) |
| `GET /api/books` | `_id, allowDownload, coverImageFileId, coverImageUrl, createdAt, description, downloadCount, id, isFree, isVisible, price, sceneCount, title, updatedAt, viewCount` | **🔴 `_id` LEAK** |
| `GET /api/posters` | `createdAt, description, downloadCount, downloadEnabled, id, imageFileId, imageUrl, pdfFileId, pdfUrl, price, status, title, updatedAt` | ✅ pulito |
| `GET /api/games` | `ageRecommended, cardImageFileId, cardImageOpacity, cardImageUrl, createdAt, howToPlay, id, longDescription, pageImageOpacity, shortDescription, slug, sortOrder, status, thumbnailFileId, title, updatedAt` | ✅ pulito |
| `GET /api/site-settings` | `brandLogoUrl, hasBrandLogo, hasHeroImage, heroImageUrl, instagramUrl, legalAddress, legalCompanyName, legalEmail, legalPecEmail, legalVatNumber, showBundlesSection, showLegalAddress, showLegalCompanyName, showLegalEmail, showLegalPecEmail, showLegalVatNumber, stripe_enabled, stripe_publishable_key, tiktokUrl` | ✅ pulito |
| `GET /api/brand-kit` | `character, colors, styleGuidelines, typography` | ✅ pulito |

> **Tutti gli altri endpoint:** shape **da confermare** prima di Fase 4B/4C — verrà fatto domino per domino con curl mirato.

---

## 7. MEDIA STREAMING — verifica live (read-only)

Test sull'illustrazione `id="1"` (unica con `imageUrl=True` controllabile via list pubblico):

### 7.1 Variante "original"
```
GET /api/illustrations/1/image
→ HTTP 200, 735,407 bytes, image/png
   content-type: image/png
   etag: "6a0179830b5edc09b11f6f87"    ✅ ETag presente
   cache-control: no-store, no-cache, must-revalidate  ⚠️ vedi §8.2
```

### 7.2 Variante WebP 400px
```
GET /api/illustrations/1/image?w=400&format=webp
→ HTTP 200, 22,960 bytes (97% riduzione!), image/webp
   etag: "6a0179870b5edc09b11f6f8b"    ✅ ETag presente (diverso = variante separata)
```

**Pipeline media ✅ funzionante.** Streaming + ETag + varianti server-side OK.

---

## 8. RISCHI IDENTIFICATI PRIMA DEL REFACTOR

### 🔴 R1 — `_id` MongoDB leak in 2 endpoint pubblici (P1)
- **Dove:** `GET /api/illustrations`, `GET /api/books`
- **Cosa leaka:** `_id` (ObjectId stringificato) accanto a `id` (UUID/identificatore di dominio)
- **Perché esiste:** in quelle route le projection non escludono `_id` (`db.collection.find({})` senza `{"_id": 0}`)
- **Impatto:** rivela dettagli interni dell'infrastruttura, viola best practice MongoDB adherence
- **Fase di fix raccomandata:** **Fase 4B (dominio illustrations + dominio books)** quando si scrive il repository — la projection viene applicata in un solo posto
- **NON va fixato in Fase 4A** (proibito: niente cambi di response shape osservabile)

### 🔴 R2 — `JWT_SECRET` default hardcoded in `server.py:58` (P0)
- **Valore:** `'pompiconni_secret_key_2024'`
- **Impatto:** se in PROD la env `JWT_SECRET` non fosse settata, l'app partirebbe con secret pubblico → token forgiabili
- **Mitigazione attuale:** in produzione l'utente HA settato `JWT_SECRET` correttamente (verificato via screenshot pannello Emergent). Quindi **non c'è exploit live ora**, ma il default è una bomba latente.
- **Fix in Fase 4A:** `core/config.py` farà raise in PROD se `JWT_SECRET` mancante o uguale al default.

### 🟠 R3 — Fallback Mongo verso `localhost` (P0)
- **Dove:** `server.py:39` (`'mongodb://localhost:27017'`), `server.py:44` (`'pompiconni_db'`)
- **Impatto:** se in PROD mancano `MONGODB_URI` e `MONGO_URL` insieme, l'app tenta `localhost:27017` su un container senza Mongo → silent failure / connessione che pende.
- **Fix in Fase 4A:** fail-fast in PROD.

### 🟠 R4 — Anomalia routing: 14 route admin registrate in `api_router` (P2)
- **Dove:** §5.2 — route `/admin/games/...` decorate con `@api_router` invece di `@admin_router`
- **Impatto utente:** nessuno (path finale identico per coincidenza dei prefissi)
- **Impatto refactor:** Fase 4C deve preservare i path esatti malgrado lo spostamento semantico nei nuovi router admin
- **Decisione:** preservare path invariati in 4C; consolidare correzione (se vorremo) come post-4C dedicato

### 🟠 R5 — Env var dichiarate ma mai lette dal codice (P2)
- `ENVIRONMENT` (in .env, NON letta) → da introdurre Fase 4A
- `CORS_ORIGINS` (in .env, NON letta — c'è `["*"]` hardcoded in server.py:5039) → da introdurre Fase 4A/post

### 🟡 R6 — Cache-Control "no-cache" sulle immagini (P2)
- **Dove:** header `Cache-Control: no-store, no-cache, must-revalidate` sulle response immagine
- **Impatto:** il browser non cache le immagini → ogni reload rifa la richiesta (ETag però evita ri-download del payload, risponde 304)
- **NON è una regression del refactor**. Da rivedere in fase di "performance polish" (post Fase 6).

### 🟡 R7 — Collezione `admins` non collegata al login (P3)
- 1 documento esiste in `admins`, ma il login usa solo env vars
- Da chiarire prima di Fase 4B (dominio auth)

### 🟡 R8 — Illustration ID inconsistenti (P3)
- Modello dichiara `id: str = uuid4()`, ma alcuni record hanno `id="1"`, `"12"`, `"21"` (legacy data)
- **Impatto:** lookup per UUID standardizzato non funzionerebbe per record legacy. Funziona oggi perché la query è `{"id": <stringa>}`.
- Documentato, non azione richiesta nel refactor (semmai migrazione dati post)

### 🟢 R9 — Pytest esistenti sono SKIPPED senza env (P2)
- `tests/test_phase2_db_metadata.py` → 2 test, entrambi SKIPPED senza `MONGO_URL`/`DB_NAME` esportati nel shell
- Funzionano se eseguiti con env corretto, ma **non danno copertura automatica out-of-the-box**
- Fase 4A includerà un piccolo `conftest.py` che li attiva — **da confermare**

---

## 9. SCRIPTS — verifica statica (NESSUNA ESECUZIONE)

### 9.1 `/app/backend/create_indexes.py` (94 righe)
- Parsa correttamente (`ast.parse` OK)
- Compila (`py_compile` OK)
- **Idempotenza dichiarata nei commenti:** "All create_index calls are idempotent: if an equivalent index exists the call is a no-op"
- Definisce indici su: `themes(id)`, `illustrations(themeId, id, isFree, isPublished)`, `admins(email unique)`, `games(slug, sortOrder)`, ecc.
- Legge `MONGO_URL` e `DB_NAME` da env
- **Comando da eseguire (dopo approvazione esplicita, NON ora):**
  ```bash
  cd /app/backend && python create_indexes.py
  ```

### 9.2 `/app/backend/migrate_variants.py` (125 righe)
- Parsa correttamente
- Compila
- **Idempotenza esplicita:** `skip_if_exists=True` → "if a variant for (source, size, format) already exists it is skipped"
- Supporta dry-run via flag (stampa "(dry-run — skipping)")
- Legge `MONGO_URL` e `DB_NAME` da env
- **Comando da eseguire (dopo approvazione esplicita, NON ora):**
  ```bash
  cd /app/backend && python migrate_variants.py [--dry-run]
  ```

### 9.3 Conformità con il piano refactor
Entrambi gli script saranno **lasciati invariati in posizione** in Fase 4A. Se in Fase 4C/5 li sposteremo in `/app/backend/scripts/`, verranno create **wrapper compatibili** in `/app/backend/create_indexes.py` e `/app/backend/migrate_variants.py` (single-line `from scripts.create_indexes import *`) per non rompere comandi esterni esistenti.

---

## 10. CHECKLIST TEST MINIMI — da rieseguire dopo OGNI fase

Salvare come check di regressione. Tempo stimato: 5–10 minuti.

### Backend statici
- [ ] `python -m py_compile` su tutti i file backend modificati → 0 errori
- [ ] `cd /app/backend && python -c "import server; assert hasattr(server, 'app')"` → OK
- [ ] `sudo supervisorctl restart backend` → STATUS `RUNNING`
- [ ] `tail -50 /var/log/supervisor/backend.*.log` → nessun traceback nelle ultime 50 righe

### Health
- [ ] `curl http://localhost:8001/` → 200 `{"status":"ok",...}`
- [ ] `curl http://localhost:8001/health` → 200 `{"status":"ok"}`
- [ ] `curl http://localhost:8001/api/health` → 200 `{"status":"ok"}`
- [ ] `curl $REACT_APP_BACKEND_URL/api/` → 200
- [ ] `curl $REACT_APP_BACKEND_URL/api/health` → 200

### Public API (smoke)
- [ ] `curl /api/themes` → 200, count = **6**
- [ ] `curl /api/illustrations` → 200, count = **23**
- [ ] `curl /api/bundles` → 200, count = **4**
- [ ] `curl /api/posters` → 200, count = **2**
- [ ] `curl /api/games` → 200, count = **3**
- [ ] `curl /api/books` → 200, count = **2**
- [ ] `curl /api/reviews` → 200, count = **15**
- [ ] `curl /api/site-settings` → 200, contiene chiavi `legalCompanyName`, `showLegalCompanyName`...
- [ ] `curl /api/brand-kit` → 200, contiene `character, colors, styleGuidelines, typography`
- [ ] `curl /api/illustrations/1/image` → 200, content-type `image/png`, ETag presente
- [ ] `curl /api/illustrations/1/image?w=400&format=webp` → 200, content-type `image/webp`

### Auth & Admin
- [ ] `POST /api/admin/login` con creds test → 200, token ricevuto
- [ ] `GET /api/admin/dashboard` senza token → 403
- [ ] `GET /api/admin/dashboard` con token → 200
- [ ] `GET /api/admin/illustrations` con token → 200
- [ ] `GET /api/admin/posters` con token → 200
- [ ] `GET /api/admin/settings` con token → 200

### Security regression (draft + downloadEnabled)
- [ ] Identificare una illustration in stato `isPublished=false` via admin list
- [ ] `GET /api/illustrations/{draft_id}` (no auth) → 404 (atteso)
- [ ] `GET /api/illustrations/{draft_id}/image` (no auth) → 404 (atteso)
- [ ] Identificare un poster `status=draft`
- [ ] `GET /api/posters/{draft_id}/image` (no auth) → 404
- [ ] `GET /api/illustrations/{published_no_download}/download` → 403 (se esiste record `downloadEnabled=false`)

### Database (read-only)
- [ ] Ping Atlas DEV → OK
- [ ] `count_documents` per le 18 collezioni → numeri = baseline §4.2 ± 0

### Frontend
- [ ] `cd /app/frontend && yarn build` → "Compiled successfully", 0 errori
- [ ] Smoke screenshot Landing
- [ ] Smoke screenshot Admin login
- [ ] Grep `localhost|127.0.0.1|:8001` in `src/` → vuoto

### Tests
- [ ] `cd /app/backend && python -m pytest tests/` → 0 fail (skip ok)

---

## 11. COSA È PROIBITO MODIFICARE IN FASE 4A

(riepilogo concordato)

- ❌ Path di qualunque endpoint
- ❌ Metodo HTTP
- ❌ Shape della response
- ❌ Status code (200/201/204/400/401/403/404)
- ❌ Nomi parametri (path, query, body)
- ❌ Logica di auth
- ❌ Logica upload/download
- ❌ Streaming GridFS / pipeline media
- ❌ PDF generation
- ❌ AI pipeline (image_pipeline.py)
- ❌ Script (create_indexes.py, migrate_variants.py)
- ❌ Frontend (ZERO modifiche)
- ❌ Dipendenze (requirements.txt invariato)
- ❌ `.env`
- ❌ Supervisor config

---

## 12. PUNTI APERTI DA CHIARIRE PRIMA DI FASE 4A

> **Non bloccanti per autorizzare Fase 4A**, ma vanno decisi prima di Fase 4B.

1. **R7 (collezione `admins`)**: tenere come legacy o rimuovere?
2. **R5 (`ENVIRONMENT` non letta)**: Fase 4A introduce la lettura solo per fail-fast in PROD — confermi?
3. **R5 (`CORS_ORIGINS` non letta)**: Fase 4A leggerà la var ma manterrà `["*"]` come default per backward compat? Oppure rimaniamo su `["*"]` hardcoded fino a una fase dedicata sicurezza?
4. **R1 (`_id` leak)**: fix in Fase 4B (consigliato) o in fase dedicata?

---

## 13. APPROVAZIONI RICHIESTE PER PROCEDERE

- [ ] **A. Approvazione Fase 4A** con scope §3 del piano: creazione `core/*` + `models/*`, modifica solo `server.py`, zero altri file toccati, zero nuove dep, zero commit automatici.
- [ ] **B. Risposta ai 4 punti aperti** in §12 (o accettazione defaults proposti).

Fermo qui. Nessuna azione fino a tuo OK esplicito.

---

*Documento generato in modalità read-only. Nessun file modificato, nessun DB scritto, nessuna dipendenza installata, nessun commit eseguito.*
