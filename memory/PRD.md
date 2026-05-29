# PRD — Poppiconni

## Original Problem Statement
Portale del brand "Poppiconni" (editoria per bambini): illustrazioni scaricabili, poster, libri, bundle, giochi interattivi ("Bolle Magiche"), pannello admin CMS completo. L'utente ha richiesto la trasformazione da MVP a prodotto web professionale, stabile, veloce e scalabile, pronto per il dominio ufficiale `poppiconni.it`.

## Stack tecnologico
- **Backend:** FastAPI + Motor (MongoDB async) + GridFS per immagini/PDF
- **Frontend:** React 18 + Tailwind + shadcn/ui
- **Database:** MongoDB Atlas (cluster `poppiconni-dev` e `poppiconni-prod`, separati)
- **LLM:** Emergent LLM Key (GPT-4o per generation AI)
- **Storage:** GridFS (no object storage esterno)
- **Deploy:** Emergent platform
- **Stripe:** configurato come `stripe_enabled: false` — **NON attivare**

## Architettura corrente (post-Fase 1)
```
/app
├── backend/
│   ├── .env                    # MONGO_URL, DB_NAME, JWT, ADMIN_*, EMERGENT_LLM_KEY
│   ├── server.py               # ⚠️ monolitico 4886 righe, 57 endpoint (TARGET: split in Fase 4)
│   ├── streaming.py            # ⭐ NEW Fase 1: true chunked GridFS streaming + ETag/304
│   ├── create_indexes.py       # ⭐ NEW Fase 1: script idempotente indici Atlas
│   ├── image_pipeline.py
│   ├── pdf_generator.py
│   ├── requirements.txt
│   └── tests/
│       └── test_refactor_phase1.py   # ⭐ NEW: regression suite Fase 1
└── frontend/src/
    ├── App.js
    ├── services/api.js         # Axios CRUD client (TARGET: split in Fase 5)
    ├── pages/                  # 30 pagine (TARGET: → features/ in Fase 5)
    └── components/ui/ (shadcn)
```

## Piano Refactoring (approvato dall'utente)
Strategia: "1 fase alla volta, piccoli batch, testing_agent_v3_fork dopo ogni fase, nessuna mega-riscrittura".

### ✅ Fase 1 — Performance Foundation (COMPLETATA 24/04/2026)
- 20 indici MongoDB su `poppiconni_dev` e `poppiconni_prod`
- True chunked streaming GridFS su 17 endpoint (TTFB 994ms → 440ms = –56%)
- ETag strong + `304 Not Modified`
- Regression suite 29/30 passati

### ✅ Fase 2 — Media Pipeline professionale (COMPLETATA 24/04/2026)
- **`media_pipeline.py`** — `ensure_variants()` / `find_variant()` / `normalize_size_param()` / `normalize_format_param()`. PIL + EXIF orientation rispettata, no upscale, fallback png/jpg in base ad alpha channel. Idempotente.
- **`streaming.py` esteso** — `stream_gridfs_response_with_variants()` con fallback sicuro all'originale. ETag per-variante.
- **Endpoint `?w=400|800|1600` + `?format=webp|jpg|png`** su: illustrations, posters, books cover, games thumbnail/card/page, themes bg, hero, brand-logo. Fallback: mai 500, sempre serve originale quando variante assente.
- **Auto-generazione post-upload** via `fire_variants()` (asyncio.create_task fire-and-forget) su 11 endpoint admin upload.
- **`migrate_variants.py`** — script idempotente batch. Eseguito su DEV e PROD: 3 originali → **18 varianti** generate in ciascun ambiente (3 × 3 size × 2 format).
- **Risultati misurati:**
  - Illustrazione 1.1 MB PNG → variante 400 webp = **15.5 KB** (–98.5%)
  - Gallery stimata 24 card a 400 webp ≈ **380 KB** (vs 26 MB originali)
  - Originali **intatti** (MD5, size, magic bytes verificati)
- Regression suite 28/28 + 29/30 Fase 1 ancora OK

### ✅ Fase 3 — Frontend Media Professionale (COMPLETATA 26/04/2026)
- **`SmartImage.jsx`** — `<picture>` + 2 `<source srcset>` (WebP + JPEG) × 3 widths (400/800/1600), `loading=lazy` di default, `decoding=async`, `fetchPriority` per LCP, fallback ladder a 3 livelli (placeholder neutro / fallbackSrc / gradient broken state). Mai produce broken-image icon.
- **`services/imageUrl.js`** — single source of truth per URL backend image: 11 builder functions + `buildImageSrcSet()` + `SUPPORTED_WIDTHS`. Tutti gli URL passano da REACT_APP_BACKEND_URL.
- **`services/queryClient.js`** — React Query setup (staleTime 5min, gcTime 30min, retry 1, refetchOnWindowFocus false).
- **`hooks/usePublicData.js`** — hooks centralizzati: `useThemes`, `useIllustrations`, `usePosters`, `useBooks`, `useBundles`, `useGames`, `useReviews`, `useSiteSettings`, `useBrandKit`.
- **`App.js`** — wrappato in `<QueryClientProvider>`.
- **Pagine refactored a SmartImage:** GalleryPage, ThemePage (24 card + dialog preview), PostersPage, PosterDetailPage (priority hero), LandingPage (hero + theme cards), SearchPage, BooksPage, GamesListPage, GameDetailPage, Navbar (brand logo).
- **Pagine convertite a React Query:** GalleryPage (useThemes), LandingPage (useThemes/useBundles/useReviews/useIllustrations/useSiteSettings + useQuery characterImages).
- **Endpoint image card:** ora puntano a `?w=400` (mobile) / `?w=800` (desktop card) / `?w=1600` (lightbox). Hero/LCP usa priority.
- **Bug found and fixed by testing agent:** `fetchpriority` lowercase JSX prop → `fetchPriority` camelCase (React DOM allow-list).

#### Esito `testing_agent_v3_fork` (iteration_3)
- ~95% pass rate, 0 critical, 0 console errors post-fix
- Mobile viewport 390×844: card carica `?w=400` come progettato
- Admin login senza più hint credenziali demo
- Regressione Fase 1+2 OK

### ⏳ Fase 4 — Refactor backend modulare
Split di `server.py` (4886 righe, 57 endpoint) in:
```
backend/
├── core/ (config, security, database, logging)
├── models/ (Pydantic schemas per dominio)
├── repositories/ (data access layer + GridFS)
├── services/ (business logic)
├── api/
│   ├── public/
│   └── admin/
├── utils/
└── tests/
```

### ⏳ Fase 5 — Refactor frontend modulare
```
frontend/src/
├── features/ (illustrations, posters, books, bundles, games, admin)
├── components/ (ui, media/SmartImage, cards, layout)
├── services/ (http, queryClient)
└── hooks/
```

### ⏳ Fase 6 — UX, produzione, rifinitura
- Fix responsività `BolleMagicheGame.jsx` (P1 residuo)
- Lighthouse test + test mobile
- Deploy produzione con PROD env vars
- Collegamento dominio `poppiconni.it`

## Pending / Backlog

### P1
- **Responsività gioco Bolle Magiche** (`/app/frontend/src/pages/BolleMagicheGame.jsx`): transform: scale() o unità relative

### P2 (backlog)
- Espansione "Bolle Magiche" con bolle speciali (arcobaleno, luce, festa)
- E-commerce per libri fisici
- Attivazione Stripe per bundle

### Minor non-regression rilevati da testing agent Fase 1
- **Cache-Control override su preview ingress:** Cloudflare override `no-store` nel preview `.preview.emergentagent.com`. Su produzione dovrebbe funzionare. Da verificare post-deploy.
- **`PUT /api/admin/illustrations/{id}`** usa schema `IllustrationCreate` che non espone `downloadEnabled`. Il toggle funziona solo via `/download-enabled` endpoint. Pre-esistente. Da considerare nella Fase 4.

## Integrazioni
- **MongoDB Atlas** (DEV + PROD configurati, utenti separati)
- **Emergent LLM Key** (universal key per OpenAI GPT-4o, usata per AI image generation)
- **Stripe** (INERT — `stripe_enabled: false`)

## Regole operative (NON violare)
1. Nessun MongoDB locale in DEV/PROD deployed
2. Nessuna credenziale nei log o nel repository
3. DEV (`poppiconni_dev`) e PROD (`poppiconni_prod`) SEMPRE separati
4. Mai toccare cluster PM Siteflow o Fitness Extreme
5. Una fase alla volta, report dopo ogni fase, approvazione utente prima della successiva
6. Mai stampare connection string Atlas complete
7. `.env` protetti da Emergent, non rinominare `MONGO_URL`/`DB_NAME`

## Changelog
- **2026-04-24** — Migrazione MongoDB locale → Atlas DEV (`poppiconni_dev`). 86 documenti, GridFS 3.57 MB.
- **2026-04-24** — Migrazione Atlas DEV → Atlas PROD (`poppiconni_prod`). Binary integrity verified (MD5).
- **2026-04-24** — Fase 1 Performance Foundation completata: 20 indici + true streaming + ETag/304. TTFB –56%.
- **2026-04-24** — Sanitizzazione credenziali: rimossi password/MongoDB URI/admin hint da README, AdminLogin, test files, reports. Tutte le credenziali solo in env vars.
- **2026-04-24** — Fase 2 Media Pipeline completata: 18 varianti responsive su DEV+PROD, endpoint `?w=` e `?format=`, fallback sicuro, auto-generazione post-upload. Gallery –98.5% (26 MB → 380 KB stimati).
- **2026-04-26** — Fase 3 Frontend Media Professionale completata: SmartImage component + React Query + 11 builder functions + 10 pagine refactored. Mobile usa w=400, desktop w=800, hero priority. Fix `fetchpriority` → `fetchPriority`.
- **2026-05-10** — Deploy produzione `poppiconni.it` ok. Fase 4A (`core/`, `models/`) + SEC-GIT-0 + Fase 4B Batch 1 (`reviews`, `site_settings`, `themes`) + Batch 2 (`posters`, `games`, `level_backgrounds`).
- **2026-05-11** — **Fase 4B Batch 3 completata**: estratti `repositories/bundle_repo.py`, `repositories/illustration_repo.py`, `services/bundle_service.py`, `services/illustration_service.py`. Cablati 12 endpoint admin/pubblici di `bundles` + `illustrations` su service layer. `recalculate_bundle_counts` ora delega a service. **Fix R1 applicato:** `_id` rimosso da `GET /api/illustrations`, `GET /api/illustrations/{id}`, `GET /api/admin/illustrations`, `POST /api/admin/illustrations` e `popularIllustrations` in `/api/admin/dashboard`. `server.py`: 4320 → 4099 righe (−221, −5.1%). Riduzione totale rispetto baseline: −838 / −17.0%. Test perimetrali curl + py_compile + pytest pre-esistenti (26/29 pass; 3 fallimenti pre-esistenti per `TARGET_ILLUST_ID` stale, non causati dal refactor). GridFS/streaming/upload/attach/search **non toccati**.
- **2026-05-11** — **Fase 4B Batch 4 completata**: estratti `repositories/book_repo.py`, `repositories/book_scene_repo.py`, `repositories/reading_progress_repo.py`, `services/book_service.py`. Cablati 13 endpoint pubblici/admin di `books`/`book_scenes`/`reading_progress` su service layer. **Fix R1 applicato:** `_id` rimosso da `GET /api/books`, `GET /api/books/{id}` (book+scenes), `GET /api/admin/books`, `POST /api/admin/books`, `GET /api/admin/books/{id}/scenes`, `POST /api/admin/books/{id}/scenes`. Aggiornato test data stale (`TARGET_ILLUST_ID`/`EXPECTED_CONTENT_LENGTH`/`EXPECTED_MD5_PREFIX`) in `tests/test_refactor_phase1.py` per puntare a record valido. `server.py`: 4099 → 3988 righe (−111, −2.7%). Riduzione totale rispetto baseline: **−949 / −19.2%**. Test: tutti i curl lifecycle (CRUD books/scenes + sanitize HTML + 400/404 semantics + reading progress) ✅, regression themes/posters/games/illustrations/bundles ✅, `pytest tests/test_refactor_phase1.py` ora **29 passed / 1 skipped (0 fail)**. GridFS (cover, scene images, generated PDF, uploads) **non toccato**.
- **2026-05-11** — **Fase 4C Router Split completata**: creata struttura `backend/api/` con `dependencies.py` (`verify_admin` alias di `verify_token`), 9 router pubblici (`api/public/*`) e 9 router admin (`api/admin/*`). **57 endpoint** CRUD/metadati spostati da `server.py` ai router modulari (themes, reviews, site_settings, bundles, illustrations metadata, posters, games, level_backgrounds, books, book_scenes, reading_progress). GridFS/streaming/PDF/upload/variants/AI routes **lasciate in `server.py`** (~50 endpoint). `server.py`: 3988 → 3653 righe (−335, −8.4%). **Totale riduzione rispetto baseline: −1284 / −26.0%**. Aggiunti 7 test anti-`_id` (R1 regression) in `tests/test_refactor_phase1.py`. `pytest tests/test_refactor_phase1.py` ora **35 passed / 2 skipped / 0 fail**. Frontend split e media-heavy refactor NON iniziati.
- **2026-05-11** — **Mini-batch Auth & Maintenance completato**: creati `api/admin/auth.py` (POST /login) e `api/admin/maintenance.py` (GET /dashboard, GET /download-stats, POST /reset-fake-counters, POST /maintenance/fix-brand-name). 5 endpoint spostati. Rimosso un blocco di dead code in `server.py` rimasto dopo Fase 4C. `server.py`: 3653 → 3454 righe (−199, −5.4%). **Totale riduzione rispetto baseline: −1483 / −30.0%**. Tutti i 5 endpoint testati con auth 403 senza token, status code preservati (401 su login fallito), shape identica al legacy (R1 mantenuto su `popularIllustrations`). `pytest` invariato: 35 passed / 2 skipped. Tutti gli endpoint admin **non-media** sono ora fuori dal monolite. Bug parallelo risolto in questa sessione: crash `/giochi` (`ReferenceError: BACKEND_URL is not defined` in `GamesListPage.jsx`), sostituito con builder helper `buildGameThumbnailUrl`/`buildGameCardImageUrl`. **Frontend split e media-heavy refactor NON iniziati.**
