# 🚀 Variabili d'ambiente PRODUZIONE — Poppiconni

> ⚠️ **Questo file NON contiene segreti reali** — è un template di riferimento.
> I valori reali per la produzione sono salvati in un posto sicuro fuori dal repository.
> Quando deployerai l'app su Emergent, copia/incolla le variabili come indicato qui sotto.

## 📋 Cosa fare al primo deploy

1. Vai su **Emergent → app "Poppiconni" → Deploy → Manage Secrets** (o "Environment Variables")
2. Aggiungi/incolla **queste 4 variabili** (cliccando "Add Variable" per ciascuna):

```text
MONGODB_URI       = <PROD_ATLAS_CONNECTION_STRING>
MONGODB_DB_NAME   = poppiconni_prod
ENVIRONMENT       = production
JWT_SECRET        = <generare un secret PROD diverso da DEV (>=48 chars, random)>
```

Le altre variabili (`MONGO_URL`, `DB_NAME`, `EMERGENT_LLM_KEY`, `ADMIN_EMAIL`,
`ADMIN_PASSWORD`, `CORS_ORIGINS`) sono gestite dalla piattaforma Emergent oppure
sono già nel `backend/.env` versionato (perché lo richiede Emergent, ma il
backend a runtime usa `MONGODB_URI` e `MONGODB_DB_NAME` come primarie).

## 🔑 Dove recuperare i valori PROD reali

| Variabile | Dove si trova |
|---|---|
| `MONGODB_URI` | MongoDB Atlas → cluster `poppiconni-prod` → Connect → connection string utente `app_poppiconni_prod` |
| `JWT_SECRET` PROD | Genera con: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_PASSWORD` PROD | Scegli una password robusta diversa da DEV |

## 🛡️ Regole di sicurezza
- ❌ NON committare mai i valori PROD reali in git
- ❌ NON scriverli in test_credentials.md o nei log
- ✅ Solo nel pannello Emergent "Manage Secrets" del deploy
- ✅ La preview continua a usare DEV (Atlas `poppiconni-dev`) — isolato dalla produzione
