"""Seed data constants (Fase 5/M4).

Verbatim copy of the seed constants previously inlined in ``server.py``.
Values intentionally **not** modified.
"""

SEED_REVIEWS = [
    {"id": "1", "name": "Maria R.", "role": "Mamma di Sofia, 5 anni", "text": "Sofia adora Poppiconni! Le tavole sono perfette per le sue manine e il personaggio è dolcissimo.", "rating": 5, "is_approved": True},
    {"id": "2", "name": "Luca B.", "role": "Papà di Marco e Giulia", "text": "Finalmente disegni da colorare con linee spesse e chiare. I miei bimbi non escono mai dai bordi!", "rating": 5, "is_approved": True},
    {"id": "3", "name": "Anna T.", "role": "Maestra d'asilo", "text": "Uso le tavole di Poppiconni in classe. I bambini adorano il personaggio e i temi sono educativi.", "rating": 5, "is_approved": True},
    {"id": "4", "name": "Giuseppe M.", "role": "Nonno di 3 nipotini", "text": "Ho stampato tutte le tavole gratuite. I nipotini sono entusiasti di colorare questo unicorno buffo!", "rating": 5, "is_approved": True},
    {"id": "5", "name": "Francesca L.", "role": "Mamma di Emma, 4 anni", "text": "Emma chiede sempre 'il cavallino con il corno'! Poppiconni è diventato il suo personaggio preferito.", "rating": 5, "is_approved": True},
    {"id": "6", "name": "Roberto S.", "role": "Papà di Matteo, 6 anni", "text": "Qualità eccellente delle illustrazioni. Mio figlio si diverte tantissimo a colorare ogni dettaglio.", "rating": 5, "is_approved": True},
    {"id": "7", "name": "Claudia P.", "role": "Educatrice", "text": "I temi sono ben pensati e adatti a diverse età. Uso molto il tema dei mestieri per attività didattiche.", "rating": 5, "is_approved": True},
    {"id": "8", "name": "Marco V.", "role": "Papà di due gemelle", "text": "Le mie bambine adorano Poppiconni! Il personaggio è tenero e le linee sono perfette per colorare.", "rating": 5, "is_approved": True},
    {"id": "9", "name": "Silvia G.", "role": "Mamma di Leonardo, 7 anni", "text": "Anche mio figlio grande ama Poppiconni. I disegni sono abbastanza dettagliati da non annoiare.", "rating": 5, "is_approved": True},
    {"id": "10", "name": "Andrea C.", "role": "Papà di Aurora, 3 anni", "text": "Aurora sta imparando i colori grazie a Poppiconni. Un progetto davvero ben fatto!", "rating": 5, "is_approved": True},
    {"id": "11", "name": "Elena B.", "role": "Zia di 4 nipoti", "text": "Regalo sempre album di Poppiconni ai miei nipotini. Sono sempre un successo!", "rating": 5, "is_approved": True},
    {"id": "12", "name": "Davide R.", "role": "Papà di Chiara, 5 anni", "text": "Il tema dello zoo è fantastico! Chiara ha imparato tanti animali colorando con Poppiconni.", "rating": 5, "is_approved": True},
    {"id": "13", "name": "Paola M.", "role": "Mamma di Tommaso, 4 anni", "text": "Tommaso porta sempre i disegni di Poppiconni all'asilo per mostrarli agli amichetti!", "rating": 5, "is_approved": True},
    {"id": "14", "name": "Stefano L.", "role": "Papà di Sofia e Mattia", "text": "Ottimo per tenere i bambini impegnati in modo creativo. Consiglio il bundle completo!", "rating": 5, "is_approved": True},
    {"id": "15", "name": "Valentina F.", "role": "Mamma di Giulia, 6 anni", "text": "Giulia ama il tema delle stagioni. Abbiamo stampato tutto per ogni periodo dell'anno!", "rating": 5, "is_approved": True}
]

SEED_THEMES = [
    {"id": "mestieri", "name": "I Mestieri", "description": "Poppiconni scopre i mestieri: pompiere, dottore, cuoco, pilota e tanti altri!", "icon": "Briefcase", "color": "#FFB6C1", "illustrationCount": 12},
    {"id": "fattoria", "name": "La Fattoria", "description": "Poppiconni in fattoria tra mucche, galline, maialini e trattori!", "icon": "Tractor", "color": "#98D8AA", "illustrationCount": 10},
    {"id": "zoo", "name": "Lo Zoo", "description": "Poppiconni visita lo zoo e incontra leoni, elefanti, giraffe e scimmie!", "icon": "Cat", "color": "#FFE5B4", "illustrationCount": 14},
    {"id": "sport", "name": "Lo Sport", "description": "Poppiconni si diverte con calcio, nuoto, tennis e tanti sport!", "icon": "Trophy", "color": "#B4D4FF", "illustrationCount": 8},
    {"id": "stagioni", "name": "Le Stagioni", "description": "Poppiconni attraverso primavera, estate, autunno e inverno!", "icon": "Sun", "color": "#FFDAB9", "illustrationCount": 16},
    {"id": "quotidiano", "name": "Vita Quotidiana", "description": "Poppiconni a scuola, al parco, in cucina e nelle avventure di ogni giorno!", "icon": "Home", "color": "#E6E6FA", "illustrationCount": 11}
]

SEED_ILLUSTRATIONS = [
    {"id": "1", "themeId": "mestieri", "title": "Poppiconni Pompiere", "description": "Il nostro unicorno salva la giornata!", "downloadCount": 234, "isFree": True, "price": 0},
    {"id": "2", "themeId": "mestieri", "title": "Poppiconni Dottore", "description": "Con lo stetoscopio e tanto amore", "downloadCount": 189, "isFree": True, "price": 0},
    {"id": "3", "themeId": "mestieri", "title": "Poppiconni Cuoco", "description": "Prepara dolcetti magici!", "downloadCount": 156, "isFree": False, "price": 0.99},
    {"id": "4", "themeId": "mestieri", "title": "Poppiconni Pilota", "description": "Vola tra le nuvole arcobaleno", "downloadCount": 201, "isFree": False, "price": 0.99},
    {"id": "5", "themeId": "mestieri", "title": "Poppiconni Astronauta", "description": "Alla scoperta delle stelle", "downloadCount": 178, "isFree": True, "price": 0},
    {"id": "6", "themeId": "fattoria", "title": "Poppiconni e la Mucca", "description": "Nuovi amici in fattoria", "downloadCount": 145, "isFree": True, "price": 0},
    {"id": "7", "themeId": "fattoria", "title": "Poppiconni sul Trattore", "description": "Guidando tra i campi", "downloadCount": 167, "isFree": False, "price": 0.99},
    {"id": "8", "themeId": "fattoria", "title": "Poppiconni e le Galline", "description": "A caccia di uova colorate", "downloadCount": 134, "isFree": True, "price": 0},
    {"id": "9", "themeId": "fattoria", "title": "Poppiconni e il Maialino", "description": "Amici nel fango!", "downloadCount": 112, "isFree": False, "price": 0.99},
    {"id": "10", "themeId": "zoo", "title": "Poppiconni e il Leone", "description": "Un incontro coraggioso", "downloadCount": 198, "isFree": True, "price": 0},
    {"id": "11", "themeId": "zoo", "title": "Poppiconni e l'Elefante", "description": "Grande amicizia!", "downloadCount": 223, "isFree": True, "price": 0},
    {"id": "12", "themeId": "zoo", "title": "Poppiconni e la Giraffa", "description": "Guardando in alto", "downloadCount": 187, "isFree": False, "price": 0.99},
    {"id": "13", "themeId": "zoo", "title": "Poppiconni e le Scimmie", "description": "Acrobazie divertenti", "downloadCount": 156, "isFree": True, "price": 0},
    {"id": "14", "themeId": "sport", "title": "Poppiconni Calciatore", "description": "Gol magico!", "downloadCount": 245, "isFree": True, "price": 0},
    {"id": "15", "themeId": "sport", "title": "Poppiconni Nuotatore", "description": "Splash tra le onde", "downloadCount": 134, "isFree": False, "price": 0.99},
    {"id": "16", "themeId": "sport", "title": "Poppiconni Tennista", "description": "Ace arcobaleno!", "downloadCount": 98, "isFree": True, "price": 0},
    {"id": "17", "themeId": "stagioni", "title": "Poppiconni in Primavera", "description": "Tra fiori e farfalle", "downloadCount": 278, "isFree": True, "price": 0},
    {"id": "18", "themeId": "stagioni", "title": "Poppiconni d'Estate", "description": "Al mare con il gelato", "downloadCount": 312, "isFree": True, "price": 0},
    {"id": "19", "themeId": "stagioni", "title": "Poppiconni d'Autunno", "description": "Tra le foglie colorate", "downloadCount": 189, "isFree": False, "price": 0.99},
    {"id": "20", "themeId": "stagioni", "title": "Poppiconni d'Inverno", "description": "Pupazzo di neve magico", "downloadCount": 267, "isFree": True, "price": 0},
    {"id": "21", "themeId": "quotidiano", "title": "Poppiconni a Scuola", "description": "Primo giorno di scuola", "downloadCount": 145, "isFree": True, "price": 0},
    {"id": "22", "themeId": "quotidiano", "title": "Poppiconni al Parco", "description": "Giochi sull'altalena", "downloadCount": 167, "isFree": False, "price": 0.99},
    {"id": "23", "themeId": "quotidiano", "title": "Poppiconni in Cucina", "description": "Biscotti con la mamma", "downloadCount": 198, "isFree": True, "price": 0}
]

SEED_BUNDLES = [
    {"id": "1", "title": "Starter Pack Poppiconni", "subtitle": "10 tavole gratuite per iniziare a colorare!", "illustrationCount": 0, "price": 0, "currency": "EUR", "isFree": True, "badgeText": "GRATIS", "isActive": True, "sortOrder": 1, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None},
    {"id": "2", "title": "Album Mestieri Completo", "subtitle": "Tutte le 12 tavole dei mestieri in PDF", "illustrationCount": 0, "price": 4.99, "currency": "EUR", "isFree": False, "badgeText": "", "isActive": True, "sortOrder": 2, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None},
    {"id": "3", "title": "Mega Pack Stagioni", "subtitle": "16 tavole per tutte le stagioni + bonus festività", "illustrationCount": 0, "price": 6.99, "currency": "EUR", "isFree": False, "badgeText": "", "isActive": True, "sortOrder": 3, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None},
    {"id": "4", "title": "Collezione Completa", "subtitle": "Tutti i temi + bonus esclusivi", "illustrationCount": 0, "price": 19.99, "currency": "EUR", "isFree": False, "badgeText": "BEST VALUE", "isActive": True, "sortOrder": 4, "illustrationIds": [], "pdfFileId": None, "backgroundImageFileId": None}
]


def build_default_games(now, new_uuid):
    """Return the default ``games`` documents.

    ``now`` (``datetime``) and ``new_uuid`` (callable returning a str) are
    injected by the seeder so this module stays import-side-effect-free.
    """
    return [
        {
            "id": new_uuid(),
            "slug": "bolle-magiche",
            "title": "Bolle Magiche",
            "shortDescription": "Scoppia le bolle colorate con Poppiconni! Un gioco divertente per tutti.",
            "longDescription": "Aiuta Poppiconni a scoppiare tutte le bolle colorate che fluttuano nel cielo! Un gioco semplice e divertente, perfetto per i più piccoli. Tocca le bolle per farle scoppiare e accumula punti. Attenzione: le bolle diventano sempre più veloci!",
            "status": "available",
            "ageRecommended": "3+",
            "howToPlay": [
                "Tocca o clicca sulle bolle per farle scoppiare",
                "Accumula punti scoppiando più bolle possibili",
                "Non lasciare che le bolle raggiungano il fondo!"
            ],
            "thumbnailFileId": None,
            "sortOrder": 1,
            "createdAt": now,
            "updatedAt": now
        },
        {
            "id": new_uuid(),
            "slug": "puzzle-poppiconni",
            "title": "Puzzle Poppiconni",
            "shortDescription": "Ricomponi le immagini di Poppiconni in tanti puzzle colorati!",
            "longDescription": "Metti alla prova le tue abilità con i puzzle di Poppiconni! Ricomponi le immagini delle avventure del nostro amico elefantino.",
            "status": "coming_soon",
            "ageRecommended": "4+",
            "howToPlay": [
                "Trascina i pezzi nella posizione corretta",
                "Completa il puzzle per sbloccare nuove immagini",
                "Sfida te stesso con puzzle sempre più difficili!"
            ],
            "thumbnailFileId": None,
            "sortOrder": 2,
            "createdAt": now,
            "updatedAt": now
        },
        {
            "id": new_uuid(),
            "slug": "memory-poppiconni",
            "title": "Memory Poppiconni",
            "shortDescription": "Trova le coppie e allena la memoria con le carte di Poppiconni!",
            "longDescription": "Allena la tua memoria con il gioco di carte Memory! Trova tutte le coppie delle carte con le immagini di Poppiconni.",
            "status": "coming_soon",
            "ageRecommended": "3+",
            "howToPlay": [
                "Gira due carte alla volta",
                "Cerca di trovare le coppie uguali",
                "Completa il gioco con meno mosse possibili!"
            ],
            "thumbnailFileId": None,
            "sortOrder": 3,
            "createdAt": now,
            "updatedAt": now
        }
    ]
