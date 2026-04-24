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
- 20 indici MongoDB su `poppiconni_dev` e `poppiconni_prod` (ix_id_isPublished, ix_slug, ix_bookId_sceneNumber, …)
- True chunked streaming GridFS su 17 endpoint file (TTFB immagine 994ms → 440ms = –56%)
- ETag strong + `If-None-Match` → `304 Not Modified` (risparmia 1.1 MB trasferimento per immagine su cache hit)
- Cache-Control `public, max-age=31536000, immutable` su asset immutabili (illustrazioni, poster, book scenes)
- Regression test suite `test_refactor_phase1.py` (29/30 passati)
- **Files:** `backend/streaming.py`, `backend/create_indexes.py`, `backend/server.py` (edit chirurgico)

### ⏳ Fase 2 — Media Pipeline professionale
- Generazione thumbnail all'upload (400/800/1600 px × WebP+JPG)
- Endpoint immagine con size hint (`?w=400`)
- Migrazione batch file GridFS esistenti
- Riduzione payload Gallery: 26 MB → 1 MB (–97%)

### ⏳ Fase 3 — Frontend media professionale
- Componente `SmartImage` (`<picture>` + `srcset` + lazy + decoding async + blur placeholder)
- React Query per cache client-side
- Refactor 33 `<img>` → `<SmartImage>`

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
