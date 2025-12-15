// Mock data for Poppiconni - Libri da Colorare per Bambini

export const themes = [
  {
    id: 'mestieri',
    name: 'I Mestieri',
    description: 'Poppiconni scopre i mestieri: pompiere, dottore, cuoco, pilota e tanti altri!',
    icon: 'Briefcase',
    color: '#FFB6C1',
    illustrationCount: 12,
    coverImage: 'https://images.unsplash.com/photo-1608052568356-57732d885c2a?w=400'
  },
  {
    id: 'fattoria',
    name: 'La Fattoria',
    description: 'Poppiconni in fattoria tra mucche, galline, maialini e trattori!',
    icon: 'Tractor',
    color: '#98D8AA',
    illustrationCount: 10,
    coverImage: 'https://images.unsplash.com/photo-1564115484-a4aaa88d5449?w=400'
  },
  {
    id: 'zoo',
    name: 'Lo Zoo',
    description: 'Poppiconni visita lo zoo e incontra leoni, elefanti, giraffe e scimmie!',
    icon: 'Cat',
    color: '#FFE5B4',
    illustrationCount: 14,
    coverImage: 'https://images.unsplash.com/photo-1516748413653-9829208eeb5b?w=400'
  },
  {
    id: 'sport',
    name: 'Lo Sport',
    description: 'Poppiconni si diverte con calcio, nuoto, tennis e tanti sport!',
    icon: 'Trophy',
    color: '#B4D4FF',
    illustrationCount: 8,
    coverImage: 'https://images.unsplash.com/photo-1599141702157-e8f4361e3382?w=400'
  },
  {
    id: 'stagioni',
    name: 'Le Stagioni',
    description: 'Poppiconni attraverso primavera, estate, autunno e inverno!',
    icon: 'Sun',
    color: '#FFDAB9',
    illustrationCount: 16,
    coverImage: 'https://images.unsplash.com/photo-1608052568356-57732d885c2a?w=400'
  },
  {
    id: 'quotidiano',
    name: 'Vita Quotidiana',
    description: 'Poppiconni a scuola, al parco, in cucina e nelle avventure di ogni giorno!',
    icon: 'Home',
    color: '#E6E6FA',
    illustrationCount: 11,
    coverImage: 'https://images.unsplash.com/photo-1564115484-a4aaa88d5449?w=400'
  }
];

export const illustrations = [
  // Mestieri
  { id: 1, themeId: 'mestieri', title: 'Poppiconni Pompiere', description: 'Il nostro unicorno salva la giornata!', downloadCount: 234, isFree: true },
  { id: 2, themeId: 'mestieri', title: 'Poppiconni Dottore', description: 'Con lo stetoscopio e tanto amore', downloadCount: 189, isFree: true },
  { id: 3, themeId: 'mestieri', title: 'Poppiconni Cuoco', description: 'Prepara dolcetti magici!', downloadCount: 156, isFree: false },
  { id: 4, themeId: 'mestieri', title: 'Poppiconni Pilota', description: 'Vola tra le nuvole arcobaleno', downloadCount: 201, isFree: false },
  { id: 5, themeId: 'mestieri', title: 'Poppiconni Astronauta', description: 'Alla scoperta delle stelle', downloadCount: 178, isFree: true },
  
  // Fattoria
  { id: 6, themeId: 'fattoria', title: 'Poppiconni e la Mucca', description: 'Nuovi amici in fattoria', downloadCount: 145, isFree: true },
  { id: 7, themeId: 'fattoria', title: 'Poppiconni sul Trattore', description: 'Guidando tra i campi', downloadCount: 167, isFree: false },
  { id: 8, themeId: 'fattoria', title: 'Poppiconni e le Galline', description: 'A caccia di uova colorate', downloadCount: 134, isFree: true },
  { id: 9, themeId: 'fattoria', title: 'Poppiconni e il Maialino', description: 'Amici nel fango!', downloadCount: 112, isFree: false },
  
  // Zoo
  { id: 10, themeId: 'zoo', title: 'Poppiconni e il Leone', description: 'Un incontro coraggioso', downloadCount: 198, isFree: true },
  { id: 11, themeId: 'zoo', title: 'Poppiconni e l\'Elefante', description: 'Grande amicizia!', downloadCount: 223, isFree: true },
  { id: 12, themeId: 'zoo', title: 'Poppiconni e la Giraffa', description: 'Guardando in alto', downloadCount: 187, isFree: false },
  { id: 13, themeId: 'zoo', title: 'Poppiconni e le Scimmie', description: 'Acrobazie divertenti', downloadCount: 156, isFree: true },
  
  // Sport
  { id: 14, themeId: 'sport', title: 'Poppiconni Calciatore', description: 'Gol magico!', downloadCount: 245, isFree: true },
  { id: 15, themeId: 'sport', title: 'Poppiconni Nuotatore', description: 'Splash tra le onde', downloadCount: 134, isFree: false },
  { id: 16, themeId: 'sport', title: 'Poppiconni Tennista', description: 'Ace arcobaleno!', downloadCount: 98, isFree: true },
  
  // Stagioni
  { id: 17, themeId: 'stagioni', title: 'Poppiconni in Primavera', description: 'Tra fiori e farfalle', downloadCount: 278, isFree: true },
  { id: 18, themeId: 'stagioni', title: 'Poppiconni d\'Estate', description: 'Al mare con il gelato', downloadCount: 312, isFree: true },
  { id: 19, themeId: 'stagioni', title: 'Poppiconni d\'Autunno', description: 'Tra le foglie colorate', downloadCount: 189, isFree: false },
  { id: 20, themeId: 'stagioni', title: 'Poppiconni d\'Inverno', description: 'Pupazzo di neve magico', downloadCount: 267, isFree: true },
  
  // Quotidiano
  { id: 21, themeId: 'quotidiano', title: 'Poppiconni a Scuola', description: 'Primo giorno di scuola', downloadCount: 145, isFree: true },
  { id: 22, themeId: 'quotidiano', title: 'Poppiconni al Parco', description: 'Giochi sull\'altalena', downloadCount: 167, isFree: false },
  { id: 23, themeId: 'quotidiano', title: 'Poppiconni in Cucina', description: 'Biscotti con la mamma', downloadCount: 198, isFree: true }
];

export const brandKit = {
  character: {
    name: 'Poppiconni',
    personality: 'Dolce, simpatico, leggermente impacciato',
    features: [
      'Occhi grandi e espressivi con ciglia lunghe',
      'Corno arcobaleno con sfumature pastello',
      'Criniera morbida e fluente',
      'Zampette tozze e adorabili',
      'Codina con ciuffo colorato',
      'Guanciotte rosate'
    ],
    proportions: {
      head: '30% del corpo',
      body: 'Tozzo e morbido',
      legs: 'Corte e rotonde',
      horn: 'Piccolo e delicato'
    }
  },
  colors: [
    { name: 'Rosa Poppiconni', hex: '#FFB6C1', usage: 'Colore primario, guance, dettagli' },
    { name: 'Azzurro Cielo', hex: '#B4D4FF', usage: 'Sfondi, elementi secondari' },
    { name: 'Verde Menta', hex: '#98D8AA', usage: 'Accenti natura, prati' },
    { name: 'Giallo Sole', hex: '#FFE5B4', usage: 'Elementi luminosi, stelle' },
    { name: 'Lavanda Sogno', hex: '#E6E6FA', usage: 'Magia, elementi fantasy' },
    { name: 'Pesca Dolce', hex: '#FFDAB9', usage: 'Calore, accoglienza' }
  ],
  typography: {
    primary: 'Quicksand',
    secondary: 'Nunito',
    style: 'Arrotondato, amichevole, facile da leggere'
  },
  styleGuidelines: [
    'Linee morbide e spesse per facilità di colorazione',
    'Nessun dettaglio eccessivo',
    'Espressioni sempre positive e tenere',
    'Stile bambinesco, non realistico',
    'Proporzioni cartoon con testa grande'
  ]
};

export const bundles = [
  {
    id: 1,
    name: 'Starter Pack Poppiconni',
    description: '10 tavole gratuite per iniziare a colorare!',
    illustrationCount: 10,
    price: 0,
    isFree: true
  },
  {
    id: 2,
    name: 'Album Mestieri Completo',
    description: 'Tutte le 12 tavole dei mestieri in PDF',
    illustrationCount: 12,
    price: 4.99,
    isFree: false
  },
  {
    id: 3,
    name: 'Mega Pack Stagioni',
    description: '16 tavole per tutte le stagioni + bonus festività',
    illustrationCount: 16,
    price: 6.99,
    isFree: false
  },
  {
    id: 4,
    name: 'Collezione Completa',
    description: 'Tutti i temi + bonus esclusivi',
    illustrationCount: 71,
    price: 19.99,
    isFree: false
  }
];

export const testimonials = [
  {
    id: 1,
    name: 'Maria R.',
    role: 'Mamma di Sofia, 5 anni',
    text: 'Sofia adora Poppiconni! Le tavole sono perfette per le sue manine e il personaggio è dolcissimo.',
    rating: 5
  },
  {
    id: 2,
    name: 'Luca B.',
    role: 'Papà di Marco e Giulia',
    text: 'Finalmente disegni da colorare con linee spesse e chiare. I miei bimbi non escono mai dai bordi!',
    rating: 5
  },
  {
    id: 3,
    name: 'Anna T.',
    role: 'Maestra d\'asilo',
    text: 'Uso le tavole di Poppiconni in classe. I bambini adorano il personaggio e i temi sono educativi.',
    rating: 5
  }
];

export const adminUser = {
  id: 1,
  email: 'admin@pompiconni.it',
  name: 'Admin Poppiconni',
  role: 'admin'
};
