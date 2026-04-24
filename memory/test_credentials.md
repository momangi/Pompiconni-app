# Test Credentials — Poppiconni

> ⚠️ **Questo file NON contiene credenziali reali.**
> Tutte le credenziali operative vivono esclusivamente nelle variabili ambiente protette (`backend/.env`, Emergent platform secrets). Mai salvarle qui, nei log, nei report, né committarle.

## Admin Panel (DEV / Preview)
- **URL preview:** fornito da `REACT_APP_BACKEND_URL` (frontend `.env`)
- **Admin email:** `<ADMIN_EMAIL_FROM_ENV_OR_SEED>`
- **Admin password:** `<ADMIN_PASSWORD_FROM_PROTECTED_ENV>`
- **Admin panel path:** `/admin`
- **Env var names in `backend/.env`:** `ADMIN_EMAIL`, `ADMIN_PASSWORD`

## MongoDB — DEV (Atlas)
- **Cluster:** `poppiconni-dev`
- **Database:** `poppiconni_dev`
- **User:** `app_poppiconni_dev`
- **Role:** readWrite on `poppiconni_dev`
- **Network Access:** `0.0.0.0/0` (TLS + auth-based security)
- **Connection string:** `<DEV_MONGO_URL_FROM_ENV>` (env vars: `MONGO_URL`, `MONGODB_URI`)
- **DB name env var:** `DB_NAME` / `MONGODB_DB_NAME`

## MongoDB — PROD (Atlas)
- **Cluster:** `poppiconni-prod`
- **Database:** `poppiconni_prod`
- **User:** `app_poppiconni_prod`
- **Role:** readWrite on `poppiconni_prod`
- **Network Access:** `0.0.0.0/0` (TLS + auth-based security)
- **Connection string:** `<PROD_MONGO_URL_FROM_ENV>` (da impostare SOLO nell'ambiente deploy produttivo Emergent)
- **DB name:** `poppiconni_prod`

> 🚫 **Vietato salvare in qualsiasi file:**
> - Password MongoDB / admin / Stripe / LLM in chiaro
> - URI MongoDB complete con password inline
> - Token JWT firmati
> - Chiavi API di qualunque provider

## JWT
- **Secret env var:** `JWT_SECRET` (backend/.env — valore mai esposto)

## Emergent LLM Key
- **Env var:** `EMERGENT_LLM_KEY` (Universal Key, gestita da Emergent)

## Stripe
- **Stato:** `stripe_enabled: false` — NON attivare senza approvazione utente.

---

## Procedura per recuperare una credenziale per testing
1. Le credenziali attive vivono in `/app/backend/.env` (non committato al repo Git)
2. Per ottenere Atlas password: accedere a MongoDB Atlas console → Database Access → Edit utente → Reset password
3. Per admin password: variabile `ADMIN_PASSWORD` in `backend/.env`
4. **Mai** scrivere il valore reale in risposta, log, test report, PRD o changelog
