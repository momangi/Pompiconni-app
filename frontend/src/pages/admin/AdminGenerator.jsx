import React, { useState } from 'react';
import { Wand2, Download, RefreshCw, Sparkles, Image as ImageIcon, AlertCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { themes } from '../../data/mock';
import { toast } from 'sonner';

const AdminGenerator = () => {
  const [prompt, setPrompt] = useState('');
  const [selectedTheme, setSelectedTheme] = useState('');
  const [style, setStyle] = useState('lineart');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImages, setGeneratedImages] = useState([]);

  const styleOptions = [
    { value: 'lineart', label: 'Line Art (da colorare)' },
    { value: 'sketch', label: 'Bozza/Sketch' },
    { value: 'colored', label: 'Colorato (anteprima)' }
  ];

  const promptTemplates = [
    'Pompiconni come pompiere che salva un gattino',
    'Pompiconni in fattoria che accarezza una pecora',
    'Pompiconni allo zoo che guarda le giraffe',
    'Pompiconni che gioca a calcio nel parco',
    'Pompiconni d\'inverno che costruisce un pupazzo di neve',
    'Pompiconni a scuola che legge un libro'
  ];

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast.error('Inserisci una descrizione per l\'immagine');
      return;
    }

    setIsGenerating(true);
    toast.info('Generazione in corso...');

    // Mock generation - in futuro sarà collegato all'API
    setTimeout(() => {
      const mockImage = {
        id: Date.now(),
        prompt: prompt,
        theme: selectedTheme,
        style: style,
        timestamp: new Date().toISOString(),
        // Placeholder per immagine generata
        imageUrl: null
      };
      setGeneratedImages(prev => [mockImage, ...prev]);
      setIsGenerating(false);
      toast.success('Immagine generata! (mock)');
    }, 2000);
  };

  const handleDownload = (image) => {
    toast.success('Download avviato!');
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
          <Wand2 className="w-8 h-8 text-pink-500" />
          Generatore AI
        </h1>
        <p className="text-gray-600">Crea nuove bozze di Pompiconni usando l'intelligenza artificiale</p>
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
                Descrivi la scena che vuoi creare con Pompiconni
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert className="bg-blue-50 border-blue-200">
                <AlertCircle className="w-4 h-4 text-blue-500" />
                <AlertDescription className="text-sm text-blue-700">
                  La generazione AI sarà attivata dopo l'integrazione backend.
                  Per ora vengono create immagini placeholder.
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label>Descrizione Scena</Label>
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Descrivi la scena che vuoi generare con Pompiconni..."
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
                <Label>Tema (opzionale)</Label>
                <Select value={selectedTheme} onValueChange={setSelectedTheme}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona un tema" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nessun tema specifico</SelectItem>
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
                  <><RefreshCw className="w-4 h-4 mr-2 animate-spin" />Generazione...</>
                ) : (
                  <><Wand2 className="w-4 h-4 mr-2" />Genera Immagine</>
                )}
              </Button>
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
                <p className="text-sm text-gray-400">Usa il form a sinistra per creare nuove bozze di Pompiconni</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {generatedImages.map((image) => (
                <Card key={image.id} className="border-0 shadow-lg overflow-hidden">
                  <div className="h-48 bg-gradient-to-br from-pink-50 to-blue-50 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-6xl mb-2">🦄</div>
                      <p className="text-xs text-gray-400">Immagine Placeholder</p>
                    </div>
                  </div>
                  <CardContent className="p-4">
                    <p className="text-sm text-gray-700 mb-2 line-clamp-2">{image.prompt}</p>
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-3">
                      <span>{styleOptions.find(s => s.value === image.style)?.label}</span>
                      <span>{new Date(image.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" className="flex-1" onClick={() => handleDownload(image)}>
                        <Download className="w-4 h-4 mr-1" />Scarica
                      </Button>
                      <Button size="sm" className="flex-1 bg-pink-500 hover:bg-pink-600">
                        Salva in Galleria
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
