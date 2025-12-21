import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import SEO from '../components/SEO';
import { getThemes } from '../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GalleryPage = () => {
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchThemes = async () => {
      try {
        const data = await getThemes();
        setThemes(data);
      } catch (error) {
        console.error('Error fetching themes:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchThemes();
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <SEO 
        title="Galleria disegni da colorare"
        description="Esplora la galleria di disegni da colorare di Poppiconni: temi come la fattoria, lo zoo, i mestieri e tante altre avventure per bambini."
        canonical="https://poppiconni.it/galleria"
      />
      <Navbar />
      
      <section className="bg-gradient-to-b from-pink-50 to-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            {/* H1 SEO invisibile */}
            <h1 className="sr-only">Galleria di disegni da colorare per bambini – Temi Poppiconni</h1>
            
            {/* Titolo visivo */}
            <p className="text-4xl sm:text-5xl font-bold text-gray-800 mb-4">
              <span className="gradient-text">Galleria</span> Tematica
            </p>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Esplora tutti i temi disponibili e scopri le avventure di Poppiconni con tanti disegni da colorare pensati per bambini.
            </p>
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {loading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
              {[...Array(6)].map((_, idx) => (
                <div key={idx} className="animate-pulse">
                  <div className="h-48 bg-gray-200 rounded-t-xl" />
                  <div className="p-6 bg-white rounded-b-xl shadow-xl">
                    <div className="h-6 bg-gray-200 rounded mb-3" />
                    <div className="h-4 bg-gray-200 rounded mb-4" />
                    <div className="h-4 bg-gray-200 rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
              {themes.map((theme) => {
                // Calcola blur e velo in base allo slider (0-80%)
                const themeOpacity = Math.min(Math.max(theme.backgroundOpacity ?? 0, 0), 80);
                const themeBlurPx = (themeOpacity / 80) * 8; // 0→0px, 80→8px
                const themeVeilOpacity = themeOpacity / 100; // 0→0, 80→0.8
                
                return (
                <Link key={theme.id} to={`/galleria/${theme.id}`}>
                  <Card className="border-0 shadow-xl hover-lift overflow-hidden group cursor-pointer h-full">
                    <div className="h-48 flex items-center justify-center relative overflow-hidden" style={{ backgroundColor: theme.color + '40' }}>
                      {/* Background Image Layer - sempre visibile con opacity 1 */}
                      {theme.backgroundImageUrl && (
                        <img 
                          src={`${BACKEND_URL}${theme.backgroundImageUrl}`}
                          alt=""
                          className="absolute inset-0 w-full h-full object-cover"
                          style={{ 
                            filter: `blur(${themeBlurPx}px)`,
                            transform: 'scale(1.1)',
                            opacity: 1
                          }}
                        />
                      )}
                      {/* Velo overlay - opacità controllata dallo slider, colore crema */}
                      {theme.backgroundImageUrl ? (
                        <div 
                          className="absolute inset-0 transition-opacity group-hover:opacity-90" 
                          style={{ 
                            backgroundColor: 'rgba(255, 250, 245, 1)', 
                            opacity: themeVeilOpacity 
                          }} 
                        />
                      ) : (
                        <div className="absolute inset-0 opacity-30 transition-opacity group-hover:opacity-40" style={{ backgroundColor: theme.color }} />
                      )}
                      <div className="relative z-10 text-center">
                        <BookOpen className="w-20 h-20 mx-auto text-gray-700 group-hover:scale-110 transition-transform duration-300" />
                        <span className="mt-2 inline-block px-3 py-1 bg-white/80 rounded-full text-sm font-medium text-gray-700">
                          {theme.illustrationCount} tavole
                        </span>
                      </div>
                    </div>
                    <CardContent className="p-6">
                      <h3 className="text-2xl font-bold text-gray-800 mb-3">{theme.name}</h3>
                      <p className="text-gray-600 mb-4">{theme.description}</p>
                      <div className="flex items-center text-pink-500 font-medium group-hover:text-pink-600">
                        <span>Scopri le tavole</span>
                        <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-2 transition-transform" />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default GalleryPage;
