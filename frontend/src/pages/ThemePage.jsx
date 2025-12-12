import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Download, Eye, Heart, Filter } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getTheme, getIllustrations, incrementDownload } from '../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const ThemePage = () => {
  const { themeId } = useParams();
  const [theme, setTheme] = useState(null);
  const [illustrations, setIllustrations] = useState([]);
  const [filter, setFilter] = useState('all');
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [themeData, illustrationsData] = await Promise.all([
          getTheme(themeId),
          getIllustrations(themeId)
        ]);
        setTheme(themeData);
        setIllustrations(illustrationsData);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    
    // Load favorites from localStorage
    const savedFavorites = JSON.parse(localStorage.getItem('pompiconni_favorites') || '[]');
    setFavorites(savedFavorites);
  }, [themeId]);

  const filteredIllustrations = illustrations.filter(i => {
    if (filter === 'free') return i.isFree;
    if (filter === 'premium') return !i.isFree;
    return true;
  });

  const toggleFavorite = (id) => {
    const newFavorites = favorites.includes(id) 
      ? favorites.filter(f => f !== id) 
      : [...favorites, id];
    setFavorites(newFavorites);
    localStorage.setItem('pompiconni_favorites', JSON.stringify(newFavorites));
    toast.success(favorites.includes(id) ? 'Rimosso dai preferiti' : 'Aggiunto ai preferiti');
  };

  const handleDownload = async (illustration) => {
    try {
      await incrementDownload(illustration.id);
      toast.success(`Download di "${illustration.title}" avviato!`);
      // In production, this would trigger actual file download
      if (illustration.pdfUrl) {
        window.open(`${BACKEND_URL}${illustration.pdfUrl}`, '_blank');
      }
    } catch (error) {
      toast.error('Errore durante il download');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin w-8 h-8 border-4 border-pink-500 border-t-transparent rounded-full" />
        </div>
        <Footer />
      </div>
    );
  }

  if (!theme) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Tema non trovato</h2>
            <Link to="/galleria"><Button>Torna alla Galleria</Button></Link>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="py-16 relative overflow-hidden" style={{ backgroundColor: theme.color + '30' }}>
        <div className="absolute inset-0 pattern-dots opacity-20" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link to="/galleria" className="inline-flex items-center text-gray-600 hover:text-pink-500 mb-6 transition-colors">
            <ArrowLeft className="w-5 h-5 mr-2" />Torna alla Galleria
          </Link>
          
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 mb-4">{theme.name}</h1>
              <p className="text-lg text-gray-600 max-w-xl">{theme.description}</p>
            </div>
            <div className="flex items-center gap-4">
              <Badge variant="secondary" className="px-4 py-2 text-base">{illustrations.length} tavole</Badge>
              <Badge variant="outline" className="px-4 py-2 text-base bg-green-50 text-green-600 border-green-200">
                {illustrations.filter(i => i.isFree).length} gratuite
              </Badge>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-gray-100 sticky top-16 bg-white z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <span className="text-gray-600 font-medium">Filtra:</span>
            </div>
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-48"><SelectValue placeholder="Tutti" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tutte le tavole</SelectItem>
                <SelectItem value="free">Solo gratuite</SelectItem>
                <SelectItem value="premium">Solo premium</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </section>

      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredIllustrations.map((illustration) => (
              <Card key={illustration.id} className="border-0 shadow-lg hover-lift overflow-hidden group">
                <div className="relative h-48 bg-gray-50 flex items-center justify-center">
                  {illustration.imageUrl ? (
                    <img 
                      src={`${BACKEND_URL}${illustration.imageUrl}`} 
                      alt={illustration.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-6xl opacity-30">🦄</div>
                  )}
                  <div className="absolute top-3 left-3 flex gap-2">
                    {illustration.isFree && <Badge className="bg-green-500 text-white">Gratis</Badge>}
                  </div>
                  <button onClick={() => toggleFavorite(illustration.id)} className="absolute top-3 right-3 w-8 h-8 bg-white rounded-full flex items-center justify-center shadow-md hover:scale-110 transition-transform">
                    <Heart className={`w-5 h-5 ${favorites.includes(illustration.id) ? 'text-pink-500 fill-pink-500' : 'text-gray-400'}`} />
                  </button>
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button size="sm" variant="secondary"><Eye className="w-4 h-4 mr-1" />Anteprima</Button>
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-lg">
                        <DialogHeader><DialogTitle>{illustration.title}</DialogTitle></DialogHeader>
                        <div className="mt-4">
                          <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center mb-4">
                            {illustration.imageUrl ? (
                              <img 
                                src={`${BACKEND_URL}${illustration.imageUrl}`} 
                                alt={illustration.title}
                                className="max-h-full max-w-full object-contain"
                              />
                            ) : (
                              <div className="text-8xl opacity-40">🦄</div>
                            )}
                          </div>
                          <p className="text-gray-600 mb-4">{illustration.description}</p>
                          <Button className="w-full bg-pink-500 hover:bg-pink-600" onClick={() => handleDownload(illustration)}>
                            <Download className="w-4 h-4 mr-2" />{illustration.isFree ? 'Scarica Gratis' : 'Acquista PDF'}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                    <Button size="sm" className="bg-pink-500 hover:bg-pink-600" onClick={() => handleDownload(illustration)}>
                      <Download className="w-4 h-4 mr-1" />{illustration.isFree ? 'Scarica' : 'Acquista'}
                    </Button>
                  </div>
                </div>
                <CardContent className="p-4">
                  <h3 className="font-bold text-gray-800 mb-1">{illustration.title}</h3>
                  <p className="text-sm text-gray-500 mb-3">{illustration.description}</p>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400"><Download className="w-4 h-4 inline mr-1" />{illustration.downloadCount}</span>
                    {!illustration.isFree && <span className="text-pink-500 font-semibold">€{illustration.price}</span>}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          {filteredIllustrations.length === 0 && (
            <div className="text-center py-16"><p className="text-gray-500 text-lg">Nessuna tavola trovata con questo filtro.</p></div>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default ThemePage;
