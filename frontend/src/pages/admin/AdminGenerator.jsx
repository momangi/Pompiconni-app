import React, { useState, useEffect } from 'react';
import { Wand2, Download, RefreshCw, Sparkles, Image as ImageIcon, Save } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { getThemes, generateIllustration } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminGenerator = () => {
  const [prompt, setPrompt] = useState('');
  const [selectedTheme, setSelectedTheme] = useState('');
  const [style, setStyle] = useState('lineart');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImages, setGeneratedImages] = useState([]);
  const [themes, setThemes] = useState([]);

  useEffect(() => {
    const fetchThemes = async () => {
      try {
        const data = await getThemes();
        setThemes(data);
      } catch (error) {
        console.error('Error fetching themes:', error);
      }
    };
    fetchThemes();
  }, []);

  const styleOptions = [
    { value: 'lineart', label: 'Line Art (da colorare)' },
    { value: 'sketch', label: 'Bozza/Sketch' },
    { value: 'colored', label: 'Colorato (anteprima)' }
  ];

  const promptTemplates = [
    'Poppiconni come pompiere che salva un gattino',
    'Poppiconni in fattoria che accarezza una pecora',
    'Poppiconni allo zoo che guarda le giraffe',
    'Poppiconni che gioca a calcio nel parco',
    'Poppiconni d\'inverno che costruisce un pupazzo di neve',
    'Poppiconni a scuola che legge un libro'
  ];

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Inserisci una descrizione per l\'immagine');
      return;
    }

    setIsGenerating(true);
    toast.info('Generazione in corso... può richiedere fino a 1 minuto');

    try {
      const result = await generateIllustration(
        prompt,
        selectedTheme !== 'none' ? selectedTheme : null,
        style
      );

      const newImage = {
        id: Date.now(),
        prompt: prompt,
        theme: selectedTheme,
        style: style,
        timestamp: new Date().toISOString(),
        imageUrl: result.imageUrl,
        imageBase64: result.imageBase64,
        illustration: result.illustration
      };

      setGeneratedImages(prev => [newImage, ...prev]);
      toast.success('Immagine generata con successo!');
      
      if (result.illustration) {
        toast.success('Illustrazione salvata in galleria!');
      }
    } catch (error) {
      console.error('Generation error:', error);
      toast.error('Errore nella generazione: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = (image) => {
    if (image.imageBase64) {
      const link = document.createElement('a');
      link.href = `data:image/png;base64,${image.imageBase64}`;
      link.download = `poppiconni_${Date.now()}.png`;
      link.click();
      toast.success('Download avviato!');
    } else if (image.imageUrl) {
      window.open(`${BACKEND_URL}${image.imageUrl}`, '_blank');
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
          <Wand2 className="w-8 h-8 text-pink-500" />
          Generatore AI
        </h1>
        <p className="text-gray-600">Crea nuove bozze di Poppiconni usando l'intelligenza artificiale</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Generator Form */}
        <div className="lg:col-span-1">
          <Card className="border-0 shadow-lg sticky top-8">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-pink-500" />
                Nuova Generazione
              </CardTitle>
              <CardDescription>
                Descrivi la scena che vuoi creare con Poppiconni
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Descrizione Scena</Label>
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Descrivi la scena che vuoi generare con Poppiconni..."
                  rows={4}
                />
              </div>

              <div className="space-y-2">
                <Label>Template Rapidi</Label>
                <div className="flex flex-wrap gap-2">
                  {promptTemplates.slice(0, 3).map((template, idx) => (
                    <button
                      key={idx}
                      onClick={() => setPrompt(template)}
                      className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-pink-100 text-gray-600 hover:text-pink-600 rounded-full transition-colors"
                    >
                      {template.slice(0, 30)}...
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label>Tema (opzionale - salva automaticamente)</Label>
                <Select value={selectedTheme} onValueChange={setSelectedTheme}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona un tema" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nessun tema (non salvare)</SelectItem>
                    {themes.map(theme => (
                      <SelectItem key={theme.id} value={theme.id}>{theme.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Stile Output</Label>
                <Select value={style} onValueChange={setStyle}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona stile" />
                  </SelectTrigger>
                  <SelectContent>
                    {styleOptions.map(option => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600"
                onClick={handleGenerate}
                disabled={isGenerating}
              >
                {isGenerating ? (
                  <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Generazione in corso...</>
                ) : (
                  <><Wand2 className="w-4 h-4 mr-2" />Genera Immagine</>
                )}
              </Button>
              
              {selectedTheme && selectedTheme !== 'none' && (
                <p className="text-xs text-green-600 text-center">
                  <Save className="w-3 h-3 inline mr-1" />
                  L'immagine verrà salvata automaticamente nel tema selezionato
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Generated Images */}
        <div className="lg:col-span-2">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Immagini Generate</h2>
          
          {generatedImages.length === 0 ? (
            <Card className="border-2 border-dashed border-gray-200">
              <CardContent className="py-16 text-center">
                <ImageIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-500 mb-2">Nessuna immagine generata</p>
                <p className="text-sm text-gray-400">Usa il form a sinistra per creare nuove bozze di Poppiconni</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {generatedImages.map((image) => (
                <Card key={image.id} className="border-0 shadow-lg overflow-hidden">
                  <div className="h-48 bg-gradient-to-br from-pink-50 to-blue-50 flex items-center justify-center">
                    {image.imageBase64 ? (
                      <img 
                        src={`data:image/png;base64,${image.imageBase64}`} 
                        alt="Generated" 
                        className="w-full h-full object-contain"
                      />
                    ) : image.imageUrl ? (
                      <img 
                        src={`${BACKEND_URL}${image.imageUrl}`} 
                        alt="Generated" 
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center">
                        <div className="text-6xl mb-2">🦄</div>
                        <p className="text-xs text-gray-400">Immagine Placeholder</p>
                      </div>
                    )}
                  </div>
                  <CardContent className="p-4">
                    <p className="text-sm text-gray-700 mb-2 line-clamp-2">{image.prompt}</p>
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-3">
                      <span>{styleOptions.find(s => s.value === image.style)?.label}</span>
                      <span>{new Date(image.timestamp).toLocaleTimeString()}</span>
                    </div>
                    {image.illustration && (
                      <p className="text-xs text-green-600 mb-3">
                        <Save className="w-3 h-3 inline mr-1" />
                        Salvato in: {themes.find(t => t.id === image.theme)?.name}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" className="flex-1" onClick={() => handleDownload(image)}>
                        <Download className="w-4 h-4 mr-1" />Scarica
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminGenerator;
