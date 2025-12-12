# Pompiconni - Libri da Colorare per Bambini 🦄

Un'applicazione web completa per la gestione di libri da colorare per bambini con il personaggio Pompiconni, un unicorno dolce, simpatico e leggermente impacciato.

## 🌟 Caratteristiche

### Frontend Pubblico
- 🏠 **Landing Page** - Presentazione del personaggio e del progetto
- 🖼️ **Galleria Tematica** - 6 temi diversi (Mestieri, Fattoria, Zoo, Sport, Stagioni, Vita Quotidiana)
- 📥 **Download Center** - Tavole gratuite e bundle a pagamento
- 🎨 **Brand Kit** - Linee guida del personaggio, palette colori, tipografia
- ⭐ **Recensioni** - 15 recensioni con rotazione automatica ogni 15 secondi

### Area Admin (Protetta)
- 📊 **Dashboard** - Statistiche in tempo reale
- 🖼️ **Gestione Illustrazioni** - CRUD completo con upload immagini/PDF
- 🤖 **Generatore AI** - Creazione illustrazioni con OpenAI gpt-image-1
- 🔐 **Autenticazione** - Login sicuro con JWT

## 🛠️ Stack Tecnologico

- **Frontend**: React (CRA) + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: OpenAI gpt-image-1 (via Emergent LLM Key)

## 📦 Installazione

### Prerequisiti
- Node.js 18+
- Python 3.11+
- MongoDB

### Frontend
```bash
cd frontend
yarn install
yarn start
```

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001
```

## ⚙️ Configurazione

Copia `backend/.env.example` in `backend/.env` e configura le variabili:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=pompiconni_db
EMERGENT_LLM_KEY=your_emergent_llm_key
ADMIN_EMAIL=admin@pompiconni.it
ADMIN_PASSWORD=your_secure_password
JWT_SECRET=your_jwt_secret
```

## 🔑 Credenziali Demo

- **Email**: admin@pompiconni.it
- **Password**: admin123

## 📚 API Endpoints

### Pubblici
- `GET /api/themes` - Lista temi
- `GET /api/illustrations` - Lista illustrazioni
- `GET /api/bundles` - Lista bundle
- `GET /api/reviews` - Lista recensioni
- `GET /api/brand-kit` - Brand kit completo

### Admin (Protetti)
- `POST /api/admin/login` - Login
- `GET /api/admin/dashboard` - Statistiche
- `POST /api/admin/themes` - Crea tema
- `POST /api/admin/illustrations` - Crea illustrazione
- `POST /api/admin/upload` - Upload file
- `POST /api/admin/generate-illustration` - Genera con AI

## 🎨 Brand Kit

### Colori
- **Rosa Pompiconni**: #FFB6C1
- **Azzurro Cielo**: #B4D4FF
- **Verde Menta**: #98D8AA
- **Giallo Sole**: #FFE5B4
- **Lavanda Sogno**: #E6E6FA
- **Pesca Dolce**: #FFDAB9

### Font
- **Titoli**: Quicksand
- **Testi**: Nunito

## 📄 Licenza

© 2024 Pompiconni. Tutti i diritti riservati.
