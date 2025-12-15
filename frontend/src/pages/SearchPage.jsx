import React, { useState, useEffect } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import { Search, Download, Lock, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { searchIllustrations } from '../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Suggested search terms for empty results
const SUGGESTIONS = ['fattoria', 'pompiere', 'mare', 'spazio', 'dinosauro', 'principessa'];

const SearchPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';
  
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    const performSearch = async () => {
      if (!query.trim()) {
        setResults([]);
        setSearched(false);
        return;
      }

      setLoading(true);
      setSearched(true);
      
      try {
        const data = await searchIllustrations(query);
        setResults(data.results || []);
      } catch (error) {
        console.error('Search error:', error);
        toast.error('Errore nella ricerca');
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    performSearch();
  }, [query]);

  const handleSuggestionClick = (suggestion) => {
    navigate(`/cerca?q=${encodeURIComponent(suggestion)}`);
  };

  const handleDownload = async (illustration) => {
    if (!illustration.isFree) {
      toast.error('Pagamenti non ancora attivi');
      return;
    }
    
    // Navigate to theme page with this illustration
    if (illustration.themeId) {
      navigate(`/galleria/${illustration.themeId}`);
    } else {
      navigate('/galleria');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-pink-50 to-white">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Back Button */}
        <Link to="/galleria" className="inline-flex items-center text-pink-600 hover:text-pink-700 mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Torna alla Galleria
        </Link>

        {/* Search Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-100 rounded-full mb-4">
            <Search className="w-4 h-4 text-pink-600" />
            <span className="text-sm font-medium text-pink-700">Ricerca Illustrazioni</span>
          </div>
          
          {query ? (
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-2">
              Risultati per: <span className="text-pink-600">&ldquo;{query}&rdquo;</span>
            </h1>
          ) : (
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-2">
              Cerca le illustrazioni di Poppiconni
            </h1>
          )}
          
          {searched && !loading && (
            <p className="text-gray-600">
              {results.length > 0 
                ? `${results.length} illustrazion${results.length === 1 ? 'e' : 'i'} trovat${results.length === 1 ? 'a' : 'e'}`
                : 'Nessun risultato trovato'
              }
            </p>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-10 h-10 border-4 border-pink-500 border-t-transparent rounded-full" />
          </div>
        )}

        {/* Results Grid */}
        {!loading && results.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-12">
            {results.map((illustration) => (
              <Card 
                key={illustration.id} 
                className="group overflow-hidden hover:shadow-lg transition-all duration-300 border-2 border-transparent hover:border-pink-200"
              >
                <div className="aspect-square bg-gradient-to-br from-pink-50 to-blue-50 relative overflow-hidden">
                  {illustration.imageFileId ? (
                    <img
                      src={`${BACKEND_URL}/api/illustrations/${illustration.id}/image`}
                      alt={illustration.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <span className="text-6xl opacity-30">🦄</span>
                    </div>
                  )}
                  
                  {/* Badge */}
                  <div className="absolute top-2 right-2">
                    <Badge className={illustration.isFree 
                      ? 'bg-green-500 text-white' 
                      : 'bg-pink-500 text-white'
                    }>
                      {illustration.isFree ? 'Gratis' : 'Premium'}
                    </Badge>
                  </div>

                  {/* Hover Overlay */}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <Button
                      size="sm"
                      className={illustration.isFree 
                        ? 'bg-white text-pink-600 hover:bg-pink-50'
                        : 'bg-gray-100 text-gray-500 cursor-not-allowed'
                      }
                      onClick={() => handleDownload(illustration)}
                    >
                      {illustration.isFree ? (
                        <>
                          <Download className="w-4 h-4 mr-1" />
                          Scarica
                        </>
                      ) : (
                        <>
                          <Lock className="w-4 h-4 mr-1" />
                          Premium
                        </>
                      )}
                    </Button>
                  </div>
                </div>
                
                <CardContent className="p-3">
                  <h3 className="font-medium text-gray-800 text-sm truncate">{illustration.title}</h3>
                  {illustration.themeName && (
                    <p className="text-xs text-gray-500 truncate">{illustration.themeName}</p>
                  )}
                  {!illustration.isFree && (
                    <p className="text-xs text-yellow-600 mt-1">Pagamenti non ancora attivi</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* No Results State */}
        {!loading && searched && results.length === 0 && (
          <div className="text-center py-16">
            <div className="text-6xl mb-6">🔍</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-3">
              Nessuna illustrazione trovata
            </h2>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              Non abbiamo trovato illustrazioni per "{query}". 
              Prova con una di queste ricerche:
            </p>
            
            {/* Suggestion Chips */}
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="px-4 py-2 bg-pink-100 text-pink-700 rounded-full hover:bg-pink-200 transition-colors text-sm font-medium"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Empty Query State */}
        {!loading && !searched && (
          <div className="text-center py-16">
            <div className="text-6xl mb-6">🦄</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-3">
              Cosa vuoi colorare oggi?
            </h2>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              Usa la barra di ricerca per trovare le illustrazioni di Poppiconni!
            </p>
            
            {/* Suggestion Chips */}
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="px-4 py-2 bg-pink-100 text-pink-700 rounded-full hover:bg-pink-200 transition-colors text-sm font-medium"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <Footer />
    </div>
  );
};

export default SearchPage;
