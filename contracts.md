# Pompiconni - API Contracts

## Database Models

### Theme
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "icon": "string",
  "color": "string (hex)",
  "coverImage": "string (URL)",
  "illustrationCount": "number",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Illustration
```json
{
  "id": "string",
  "themeId": "string",
  "title": "string",
  "description": "string",
  "imageUrl": "string (URL)",
  "pdfUrl": "string (URL)",
  "isFree": "boolean",
  "price": "number",
  "downloadCount": "number",
  "createdAt": "datetime",
  "updatedAt": "datetime"
}
```

### Bundle
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "illustrationIds": ["string"],
  "illustrationCount": "number",
  "price": "number",
  "isFree": "boolean",
  "createdAt": "datetime"
}
```

### Review (Seed)
```json
{
  "id": "string",
  "name": "string",
  "role": "string",
  "text": "string",
  "rating": "number (1-5)"
}
```

## API Endpoints

### Public Endpoints
- `GET /api/themes` - Lista tutti i temi
- `GET /api/themes/{id}` - Dettaglio tema
- `GET /api/illustrations` - Lista illustrazioni (filtri: themeId, isFree)
- `GET /api/illustrations/{id}` - Dettaglio illustrazione
- `GET /api/bundles` - Lista bundle
- `GET /api/reviews` - Lista recensioni seed
- `POST /api/illustrations/{id}/download` - Incrementa download count

### Admin Endpoints (Protetti)
- `POST /api/admin/login` - Login admin
- `GET /api/admin/dashboard` - Statistiche
- `POST /api/admin/themes` - Crea tema
- `PUT /api/admin/themes/{id}` - Modifica tema
- `DELETE /api/admin/themes/{id}` - Elimina tema
- `POST /api/admin/illustrations` - Crea illustrazione
- `PUT /api/admin/illustrations/{id}` - Modifica illustrazione
- `DELETE /api/admin/illustrations/{id}` - Elimina illustrazione
- `POST /api/admin/bundles` - Crea bundle
- `PUT /api/admin/bundles/{id}` - Modifica bundle
- `DELETE /api/admin/bundles/{id}` - Elimina bundle
- `POST /api/admin/upload` - Upload file (immagine/PDF)
- `POST /api/admin/generate-illustration` - Genera con AI

## Mock Data da sostituire
- `/app/frontend/src/data/mock.js` → API calls reali
- Tutti i componenti useranno fetch/axios per dati dal backend

## Integrazione Frontend-Backend
1. Creare `api.js` con funzioni per ogni endpoint
2. Sostituire import mock.js con chiamate API
3. Aggiungere loading states e error handling
4. Mantenere UI identica, solo dati diversi
