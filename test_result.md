# Poppiconni CMS - Test Results

## Implementazioni Completate

### 1. Upload Contenuti GridFS (PDF + Immagini)
- ✅ Campi DB separati: `imageFileId`, `pdfFileId`, `contentType`, `originalFileName`
- ✅ `POST /api/admin/illustrations/{id}/attach-image` (JPG, JPEG, PNG)
- ✅ `POST /api/admin/illustrations/{id}/attach-pdf`
- ✅ Sostituzione automatica file esistenti
- ✅ `GET /api/illustrations/{id}/image` - stream immagine da GridFS
- ✅ `GET /api/illustrations/{id}/download` - stream PDF con Content-Disposition
- ✅ Contatori download incrementati solo su download PDF riuscito

### 2. Generazione AI Persistente (OLD)
- ✅ Generazione solo backend con EMERGENT_LLM_KEY
- ✅ Output salvato in GridFS come PNG
- ✅ Creazione documento Illustration con `imageFileId`
- ✅ Salvataggio prompt, style, tema associato

### 3. 🆕 PIPELINE MULTI-AI POPPICONNI (NEW!)
Pipeline automatica a 4 fasi per generare illustrazioni on-brand:

**Endpoint principale:** `POST /api/admin/generate-poppiconni`

**Fasi della Pipeline:**
1. **Fase 1 - LLM (GPT-4o):** Interpreta richiesta utente + applica regole brand → genera prompt ottimizzato
2. **Fase 2 - Image Gen (gpt-image-1):** Genera immagine candidata
3. **Fase 3 - Vision/OCR (GPT-4o):** Quality Check automatico (barattolo popcorn, scritta "POPPICONNI", stile line-art)
4. **Fase 4 - Post-Produzione (Pillow):** Pulizia, normalizzazione, export (PNG 300DPI, PDF, thumbnail)

**Logica Retry:**
- Max 5 tentativi sincroni con patch automatica del prompt
- Se fallisce: salva come `LOW_CONFIDENCE`
- Ciclo asincrono aggiuntivo (altri 5 tentativi)

**Nuova collezione DB: `generation_styles`**
- Libreria stili persistente per utente
- Limite configurabile (default: 20 reference per utente)
- Upload immagini di riferimento

**Nuovi Endpoint Styles:**
- ✅ `GET /api/admin/styles` - Lista stili utente
- ✅ `POST /api/admin/styles` - Crea nuovo stile
- ✅ `DELETE /api/admin/styles/{id}` - Elimina stile
- ✅ `POST /api/admin/styles/{id}/upload-reference` - Carica reference image
- ✅ `GET /api/admin/styles/{id}/reference-image` - Serve reference image

**Nuovi Endpoint Pipeline:**
- ✅ `POST /api/admin/generate-poppiconni` - Avvia pipeline completa
- ✅ `GET /api/admin/pipeline-status/{generation_id}` - Check stato async

**Frontend:**
- ✅ `AdminGenerator.jsx` rinnovato con:
  - Form descrizione scena in linguaggio naturale
  - Template rapidi
  - Selettore tema per organizzazione galleria
  - Selettore stile di riferimento
  - Toggle Style Lock
  - Toggle Salva in Galleria
  - Visualizzazione risultati pipeline con:
    - Status badge (pending, phase1, phase2, phase3, phase4, completed, low_confidence, failed)
    - QC Report dettagliato
    - Thumbnail preview
    - Download PNG/PDF

### 4. Gestione Temi Admin (CRUD)
- ✅ Pagina Admin "Temi" con lista completa
- ✅ Creare tema: name, description, color
- ✅ Edit tema
- ✅ Delete tema con verifica illustrazioni
- ✅ Palette 12 colori predefiniti

### 5. Hero Image Homepage
- ✅ Upload hero image (JPG, JPEG, PNG)
- ✅ Storage GridFS
- ✅ Stream immagine

### 6. Libri Digitali
- ✅ CRUD libri
- ✅ Editor scene con TipTap
- ✅ Galleria libri pubblica
- ✅ Lettore libri con tracking progresso
- ✅ Download PDF con ReportLab

## Schema DB Aggiornato

### generation_styles (NEW)
```json
{
  "id": "string",
  "userId": "string",
  "styleName": "string",
  "description": "string|null",
  "isActive": true,
  "referenceImageFileId": "GridFS ObjectId|null",
  "referenceImageUrl": "string|null",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### illustrations (UPDATED)
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "themeId": "string|null",
  "imageUrl": "/api/illustrations/{id}/image",
  "imageFileId": "GridFS ObjectId",
  "pdfUrl": "/api/illustrations/{id}/download",
  "pdfFileId": "GridFS ObjectId",
  "isFree": true,
  "price": 0.99,
  "downloadCount": 0,
  "generatedByAI": true,
  "aiPrompt": "string",
  "aiStyle": "multi_ai_pipeline",
  "pipelineGenerationId": "uuid",
  "pipelineStatus": "completed|low_confidence|failed",
  "qcPassed": true,
  "qcConfidenceScore": 0.9
}
```

## File Modificati/Creati per Pipeline Multi-AI
- `/app/backend/image_pipeline.py` - Modulo orchestrazione pipeline (NEW)
- `/app/backend/server.py` - Nuovi endpoint styles e pipeline
- `/app/frontend/src/services/api.js` - Nuove funzioni API
- `/app/frontend/src/pages/admin/AdminGenerator.jsx` - UI rinnovata

## Test Cases per Pipeline Multi-AI

### Backend Tests
1. **Test creazione stile:** `POST /api/admin/styles` con nome/descrizione
2. **Test limite stili:** Verificare che oltre 20 stili dia errore
3. **Test upload reference:** `POST /api/admin/styles/{id}/upload-reference`
4. **Test pipeline completa:** `POST /api/admin/generate-poppiconni`
5. **Test QC report:** Verificare presenza di tutti i campi nel report

### Frontend Tests
1. **Test form generazione:** Inserimento prompt, selezione tema/stile
2. **Test visualizzazione risultati:** Status badge, QC report, thumbnail
3. **Test libreria stili:** Creazione, eliminazione, upload reference
4. **Test toggle options:** Style Lock, Salva in Galleria

## Credenziali Test
- Admin: admin@pompiconni.it / admin123

## Note Importanti
- La pipeline può impiegare 1-2 minuti per completare tutti i 5 tentativi
- Il QC verifica la leggibilità della scritta "POPPICONNI" tramite GPT-4o Vision
- Se QC fallisce dopo 5 tentativi, l'immagine viene salvata come `LOW_CONFIDENCE`
- I file finali sono: PNG 300 DPI, PDF pronto stampa, thumbnail per UI

## Testing Protocol
- ✅ Read /app/image_testing.md before testing image integrations
- Use base64-encoded images for all tests
- Accepted formats: JPEG, PNG, WEBP only

## Test da Eseguire (Fork Session - 22 Dicembre 2025)

### A) Contatti Legali con Flag di Visibilità
**Backend:**
- ✅ PUT /api/admin/settings - Salvataggio campi legali con flag show_*
- ✅ GET /api/site-settings - Restituisce campi legali e flag visibilità

**Frontend:**
- ✅ Admin Settings - Sezione "Informazioni Legali" con input + checkbox "Mostra"
- ✅ Pagina /contatti-legali - Mostra dinamicamente solo campi con show=true E valore non vuoto

### B) Illustrazioni con Stato Bozza/Pubblicata
**Backend:**
- ✅ Modello Illustration con isPublished, publishedAt
- ✅ GET /api/illustrations - Filtra server-side solo isPublished=true
- ✅ GET /api/admin/illustrations - Mostra tutte (incluse bozze)
- ✅ PUT /api/admin/illustrations/{id}/publish - Toggle stato
- ✅ Migrazione automatica: illustrazioni esistenti → isPublished=true

**Frontend:**
- ✅ Admin Illustrazioni - Filtro per stato (Tutti/Pubblicate/Bozze)
- ✅ Admin Illustrazioni - Toggle publish con icona Eye/EyeOff
- ✅ Admin Illustrazioni - Badge "Bozza" e bordo arancione per bozze
- ✅ Galleria pubblica - Non mostra illustrazioni in bozza (filtro server-side)

### Credenziali Test
- **Email**: admin@pompiconni.it
- **Password**: admin123

### Endpoint per Test Backend
```bash
# Test legal settings
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
TOKEN=$(curl -s -X POST "$API_URL/api/admin/login" -H "Content-Type: application/json" -d '{"email":"admin@pompiconni.it","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Update legal settings
curl -X PUT "$API_URL/api/admin/settings" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"legal_company_name":"Test","show_legal_company_name":true}'

# Get public settings
curl "$API_URL/api/site-settings"

# Get admin illustrations (all)
curl "$API_URL/api/admin/illustrations" -H "Authorization: Bearer $TOKEN"

# Toggle publish
curl -X PUT "$API_URL/api/admin/illustrations/{id}/publish" -H "Authorization: Bearer $TOKEN"

# Get public illustrations (only published)
curl "$API_URL/api/illustrations"
```

### Pagine Frontend da Testare
- /admin/settings - Sezione Informazioni Legali
- /admin/illustrations - Toggle publish e filtro stati
- /contatti-legali - Visualizzazione dinamica campi
- /galleria - Verifica che bozze non siano visibili
