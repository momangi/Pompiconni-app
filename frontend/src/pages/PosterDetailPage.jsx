import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, Download, ShoppingCart, Image as ImageIcon, 
  Printer, Frame, Star, Check
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { getPublicPoster } from '../services/api';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PosterDetailPage = () => {
  const { posterId } = useParams();
  const [poster, setPoster] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const fetchPoster = async () => {
      try {
        const data = await getPublicPoster(posterId);
        setPoster(data);
      } catch (error) {
        console.error('Error fetching poster:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPoster();
  }, [posterId]);

  const handleDownload = async () => {
    if (!poster) return;
    
    if (poster.price > 0) {
      toast.error('Questo poster è a pagamento. Acquistalo per scaricarlo!');
      return;
    }

    if (!poster.pdfFileId) {
      toast.error('PDF non ancora disponibile');
      return;
    }

    setDownloading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/posters/${posterId}/download`);
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Poppiconni_Poster_${poster.title.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('Download completato! 🎉');
    } catch (error) {
      toast.error('Errore nel download');
    } finally {
      setDownloading(false);
    }
  };

  const handlePurchase = () => {
    toast.info('Sistema di pagamento in arrivo!');
    // TODO: Integrate with existing payment system
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-pink-50 via-white to-blue-50">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500"></div>
        </div>
        <Footer />
      </div>
    );
  }

  if (!poster) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-pink-50 via-white to-blue-50">
        <Navbar />
        <div className="container mx-auto px-4 py-16 text-center">
          <ImageIcon className="w-24 h-24 mx-auto text-gray-300 mb-4" />
          <h1 className="text-2xl font-bold text-gray-700 mb-2">Poster non trovato</h1>
          <p className="text-gray-500 mb-6">Il poster richiesto non esiste o non è disponibile.</p>
          <Link to="/poster">
            <Button variant="outline">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Torna ai Poster
            </Button>
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  const isFree = poster.price === 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-pink-50 via-white to-blue-50">
      <Navbar />
      
      <main className="container mx-auto px-4 py-8">
        {/* Back Button */}
        <Link to="/poster" className="inline-flex items-center text-pink-500 hover:text-pink-600 mb-8">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Torna ai Poster
        </Link>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Image Section */}
          <div>
            <Card className="border-0 shadow-2xl overflow-hidden">
              <div className="aspect-[3/4] bg-gradient-to-br from-pink-100 to-purple-100 relative">
                {poster.imageUrl ? (
                  <img 
                    src={`${BACKEND_URL}${poster.imageUrl}`}
                    alt={poster.title}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-9xl">🖼️</span>
                  </div>
                )}
                
                {/* Price Badge */}
                <div className="absolute top-4 right-4">
                  {isFree ? (
                    <span className="bg-green-500 text-white text-lg px-4 py-2 rounded-full font-bold shadow-lg">
                      Gratis
                    </span>
                  ) : (
                    <span className="bg-gradient-to-r from-pink-500 to-purple-500 text-white text-lg px-4 py-2 rounded-full font-bold shadow-lg">
                      €{poster.price?.toFixed(2)}
                    </span>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Details Section */}
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-gray-800 mb-4">
              {poster.title}
            </h1>
            
            {poster.description && (
              <p className="text-lg text-gray-600 mb-6 leading-relaxed">
                {poster.description}
              </p>
            )}

            {/* Info Box */}
            <Card className="bg-gradient-to-r from-pink-50 to-purple-50 border-pink-200 mb-6">
              <CardContent className="p-6">
                <div className="flex items-center gap-3 mb-4">
                  <Frame className="w-6 h-6 text-pink-500" />
                  <span className="font-bold text-gray-800">PDF Stampabile – Ideale da Incorniciare</span>
                </div>
                <p className="text-gray-600 text-sm">
                  Questo poster è un'illustrazione a colori in alta risoluzione, 
                  perfetta per essere stampata e incorniciata. 
                  Decora la cameretta con Poppiconni!
                </p>
              </CardContent>
            </Card>

            {/* Features */}
            <div className="grid grid-cols-2 gap-4 mb-8">
              <div className="flex items-center gap-2 text-gray-600">
                <Check className="w-5 h-5 text-green-500" />
                <span>Alta risoluzione</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Check className="w-5 h-5 text-green-500" />
                <span>Formato PDF</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Check className="w-5 h-5 text-green-500" />
                <span>Stampa A4/A3</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <Check className="w-5 h-5 text-green-500" />
                <span>Colori vivaci</span>
              </div>
            </div>

            {/* CTA Buttons */}
            {isFree ? (
              <Button 
                size="lg"
                className="w-full bg-green-500 hover:bg-green-600 text-lg py-6"
                onClick={handleDownload}
                disabled={downloading || !poster.pdfFileId}
              >
                {downloading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Download in corso...
                  </>
                ) : (
                  <>
                    <Download className="w-5 h-5 mr-2" />
                    Scarica Gratis
                  </>
                )}
              </Button>
            ) : (
              <Button 
                size="lg"
                className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 text-lg py-6"
                onClick={handlePurchase}
              >
                <ShoppingCart className="w-5 h-5 mr-2" />
                Acquista a €{poster.price?.toFixed(2)}
              </Button>
            )}

            {!poster.pdfFileId && (
              <p className="text-center text-yellow-600 text-sm mt-3">
                ⚠️ PDF non ancora disponibile
              </p>
            )}

            {/* Print Tips */}
            <Card className="mt-8 bg-yellow-50 border-yellow-200">
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  <Printer className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div>
                    <h4 className="font-bold text-gray-800 mb-1">Consiglio per la stampa</h4>
                    <p className="text-sm text-gray-600">
                      Per risultati ottimali, stampa su carta fotografica lucida 
                      o carta di alta qualità (almeno 200g/m²).
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Related Section */}
        <div className="mt-16 text-center">
          <h3 className="text-2xl font-bold text-gray-800 mb-4">Ti potrebbero interessare</h3>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/poster">
              <Button variant="outline" className="border-pink-300 text-pink-600 hover:bg-pink-50">
                Altri Poster
              </Button>
            </Link>
            <Link to="/galleria">
              <Button variant="outline" className="border-purple-300 text-purple-600 hover:bg-purple-50">
                Tavole da Colorare
              </Button>
            </Link>
            <Link to="/libri">
              <Button variant="outline" className="border-blue-300 text-blue-600 hover:bg-blue-50">
                Libri Digitali
              </Button>
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default PosterDetailPage;
