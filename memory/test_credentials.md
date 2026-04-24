# Test Credentials — Poppiconni

## Admin Panel (DEV / Preview)
- **URL preview:** (from frontend `.env` REACT_APP_BACKEND_URL)
- **Admin email:** `admin@pompiconni.it`
- **Admin password:** `admin123`
- **Admin panel path:** `/admin`

## MongoDB — DEV (Atlas)
- **Cluster:** `poppiconni-dev`
- **Database:** `poppiconni_dev`
- **User:** `app_poppiconni_dev`
- **Role:** readWrite on `poppiconni_dev`
- **Network Access:** 0.0.0.0/0 (auth-based security)

## MongoDB — PROD (Atlas)
- **Cluster:** `poppiconni-prod`
- **Database:** `poppiconni_prod`
- **User:** `app_poppiconni_prod`
- **Role:** readWrite on `poppiconni_prod`
- **Network Access:** 0.0.0.0/0 (auth-based security)

> ⚠️ Le credenziali MongoDB sono nei `.env` (mai committati). Mai stampare connection string complete nei log.

## JWT Secret (backend/.env)
- `JWT_SECRET=pompiconni_secret_key_2024_very_secure`

## Emergent LLM Key
- `EMERGENT_LLM_KEY=sk-emergent-...` (managed)
