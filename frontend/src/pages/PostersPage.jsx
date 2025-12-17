import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Image as ImageIcon, Download, ShoppingCart, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { getPublicPosters } from '../services/api';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const PostersPage = () => {
  const [posters, setPosters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPosters = async () => {
      try {
        const data = await getPublicPosters();
        setPosters(data);
      } catch (error) {
        console.error('Error fetching posters:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchPosters();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-b from-pink-50 via-white to-blue-50">
      <Navbar />
      
      <main className="container mx-auto px-4 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-gradient-to-r from-pink-100 to-purple-100 px-4 py-2 rounded-full mb-4">
            <Sparkles className="w-4 h-4 text-pink-500" />
            <span className="text-sm font-medium text-pink-600">Illustrazioni a colori</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            <span className="bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent">
              Poster Poppiconni
            </span>
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Bellissimi poster a colori pronti da stampare e incorniciare. 
            Perfetti per decorare la cameretta dei tuoi bambini!
          </p>
        </div>

        {/* Info Banner */}
        <div className="bg-gradient-to-r from-pink-500 to-purple-500 text-white rounded-2xl p-6 mb-12 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <ImageIcon className="w-6 h-6" />
            <span className="text-xl font-bold">PDF Stampabile – Ideale da Incorniciare</span>
          </div>
          <p className="text-pink-100">
            Ogni poster è in alta risoluzione, pronto per la stampa professionale
          </p>
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500"></div>
          </div>
        ) : posters.length === 0 ? (
          /* Empty State */
          <Card className="border-2 border-dashed border-pink-200 bg-pink-50/50">
            <CardContent className="py-16 text-center">
              <ImageIcon className="w-16 h-16 mx-auto text-pink-300 mb-4" />
              <h3 className="text-xl font-bold text-gray-700 mb-2">Poster in arrivo!</h3>
              <p className="text-gray-500">
                Stiamo preparando una collezione speciale di poster per te.
              </p>
            </CardContent>
          </Card>
        ) : (
          /* Posters Grid */
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {posters.map(poster => (
              <Link key={poster.id} to={`/poster/${poster.id}`}>
                <Card className="border-0 shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden group cursor-pointer h-full">
                  {/* Image */}
                  <div className="h-64 bg-gradient-to-br from-pink-100 to-purple-100 relative overflow-hidden">
                    {poster.imageUrl ? (
                      <img 
                        src={`${BACKEND_URL}${poster.imageUrl}`}
                        alt={poster.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <span className="text-8xl">🖼️</span>
                      </div>
                    )}
                    
                    {/* Price Badge */}
                    <div className="absolute top-3 right-3">
                      {poster.price === 0 ? (
                        <span className="bg-green-500 text-white text-sm px-3 py-1.5 rounded-full font-bold shadow-lg">
                          Gratis
                        </span>
                      ) : (
                        <span className="bg-purple-500 text-white text-sm px-3 py-1.5 rounded-full font-bold shadow-lg">
                          €{poster.price?.toFixed(2)}
                        </span>
                      )}
                    </div>

                    {/* Hover Overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-4">
                      <span className="text-white font-medium">Vedi dettagli →</span>
                    </div>
                  </div>

                  <CardContent className="p-5">
                    <h3 className="font-bold text-lg text-gray-800 mb-2 group-hover:text-pink-500 transition-colors">
                      {poster.title}
                    </h3>
                    {poster.description && (
                      <p className="text-sm text-gray-500 line-clamp-2 mb-4">
                        {poster.description}
                      </p>
                    )}
                    
                    {/* CTA Button */}
                    <Button 
                      className={`w-full ${
                        poster.price === 0 
                          ? 'bg-green-500 hover:bg-green-600' 
                          : 'bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600'
                      }`}
                    >
                      {poster.price === 0 ? (
                        <>
                          <Download className="w-4 h-4 mr-2" />
                          Scarica Gratis
                        </>
                      ) : (
                        <>
                          <ShoppingCart className="w-4 h-4 mr-2" />
                          Acquista
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {/* Bottom CTA */}
        {posters.length > 0 && (
          <div className="mt-16 text-center">
            <div className="bg-gradient-to-r from-yellow-100 to-orange-100 rounded-2xl p-8 max-w-2xl mx-auto">
              <h3 className="text-2xl font-bold text-gray-800 mb-2">
                🎨 Stampa e Incornicia!
              </h3>
              <p className="text-gray-600 mb-4">
                I nostri poster sono ottimizzati per la stampa in formato A4 e A3. 
                Scarica, stampa e regala un sorriso alla cameretta!
              </p>
              <Link to="/galleria">
                <Button variant="outline" className="border-orange-300 text-orange-600 hover:bg-orange-50">
                  Scopri anche le Tavole da Colorare →
                </Button>
              </Link>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
};

export default PostersPage;
