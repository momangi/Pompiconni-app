import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Gamepad2, Sparkles, Clock, Play } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getGames } from '../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GamesListPage = () => {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGames = async () => {
      try {
        const data = await getGames();
        setGames(data);
      } catch (error) {
        console.error('Error fetching games:', error);
        // Fallback to default games if API fails
        setGames([
          {
            id: '1',
            slug: 'bolle-magiche',
            title: 'Bolle Magiche',
            shortDescription: 'Scoppia le bolle colorate con Poppiconni! Un gioco divertente per tutti.',
            status: 'available',
            thumbnailUrl: null,
            sortOrder: 1
          },
          {
            id: '2',
            slug: 'puzzle-poppiconni',
            title: 'Puzzle Poppiconni',
            shortDescription: 'Ricomponi le immagini di Poppiconni in tanti puzzle colorati!',
            status: 'coming_soon',
            thumbnailUrl: null,
            sortOrder: 2
          },
          {
            id: '3',
            slug: 'memory-poppiconni',
            title: 'Memory Poppiconni',
            shortDescription: 'Trova le coppie e allena la memoria con le carte di Poppiconni!',
            status: 'coming_soon',
            thumbnailUrl: null,
            sortOrder: 3
          }
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchGames();
  }, []);

  const getStatusBadge = (status) => {
    if (status === 'available') {
      return <Badge className="bg-green-100 text-green-700 border-green-200">Nuovo</Badge>;
    }
    return <Badge className="bg-amber-100 text-amber-700 border-amber-200">In arrivo</Badge>;
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-pink-50/30 to-white">
      <Navbar />
      
      {/* Hero Section */}
      <section className="py-16 relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-10 left-10 w-32 h-32 bg-pink-200/30 rounded-full blur-3xl" />
          <div className="absolute top-20 right-20 w-40 h-40 bg-blue-200/30 rounded-full blur-3xl" />
          <div className="absolute bottom-10 left-1/3 w-36 h-36 bg-purple-200/30 rounded-full blur-3xl" />
        </div>
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-pink-400 to-purple-400 rounded-3xl mb-6 shadow-lg">
              <Gamepad2 className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 mb-4">
              <span className="bg-gradient-to-r from-pink-500 to-purple-500 bg-clip-text text-transparent">Giochi</span> di Poppiconni
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Divertiti con i giochi di Poppiconni! Perfetti per i piccoli esploratori e tutta la famiglia. 🎮✨
            </p>
          </div>
        </div>
      </section>

      {/* Games Grid */}
      <section className="py-12 pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {loading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-48 bg-gray-200 rounded-t-2xl" />
                  <div className="p-6 bg-white rounded-b-2xl shadow-lg">
                    <div className="h-6 bg-gray-200 rounded mb-3 w-3/4" />
                    <div className="h-4 bg-gray-200 rounded mb-4" />
                    <div className="h-10 bg-gray-200 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
              {games.map((game) => (
                <Card 
                  key={game.id} 
                  className="border-0 shadow-xl hover:shadow-2xl transition-all duration-500 overflow-hidden group rounded-2xl"
                >
                  {/* Game Thumbnail/Card Image */}
                  <div className="h-48 relative overflow-hidden bg-gradient-to-br from-pink-100 via-purple-50 to-blue-100">
                    {/* Card Background Image (with opacity) */}
                    {game.cardImageUrl && (
                      <div 
                        className="absolute inset-0 bg-cover bg-center"
                        style={{ 
                          backgroundImage: `url(${BACKEND_URL}${game.cardImageUrl})`,
                          opacity: (game.cardImageOpacity || 35) / 100
                        }}
                      />
                    )}
                    
                    {/* Thumbnail overlay (if exists and no card image) */}
                    {game.thumbnailUrl && !game.cardImageUrl ? (
                      <img 
                        src={`${BACKEND_URL}${game.thumbnailUrl}`}
                        alt={game.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                    ) : !game.cardImageUrl && (
                      <div className="w-full h-full flex items-center justify-center relative">
                        {/* Decorative bubbles for games without card image */}
                        <div className="absolute inset-0 overflow-hidden">
                          {[...Array(6)].map((_, i) => (
                            <div
                              key={i}
                              className="absolute rounded-full animate-float"
                              style={{
                                width: `${30 + Math.random() * 40}px`,
                                height: `${30 + Math.random() * 40}px`,
                                left: `${10 + Math.random() * 80}%`,
                                top: `${10 + Math.random() * 80}%`,
                                background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.8), rgba(${game.slug === 'bolle-magiche' ? '236,72,153' : game.slug === 'puzzle-poppiconni' ? '147,51,234' : '59,130,246'},0.3))`,
                                boxShadow: 'inset 0 0 20px rgba(255,255,255,0.5), 0 0 10px rgba(255,255,255,0.3)',
                                animationDelay: `${i * 0.5}s`,
                                animationDuration: `${3 + Math.random() * 2}s`
                              }}
                            />
                          ))}
                        </div>
                        <Gamepad2 className="w-16 h-16 text-pink-300 relative z-10" />
                      </div>
                    )}
                    
                    {/* Status Badge */}
                    <div className="absolute top-4 right-4 z-10">
                      {getStatusBadge(game.status)}
                    </div>
                  </div>
                  
                  <CardContent className="p-6">
                    <h3 className="text-xl font-bold text-gray-800 mb-2 group-hover:text-pink-600 transition-colors">
                      {game.title}
                    </h3>
                    <p className="text-gray-600 text-sm mb-5 line-clamp-2">
                      {game.shortDescription}
                    </p>
                    
                    {game.status === 'available' ? (
                      <Link to={`/giochi/${game.slug}`}>
                        <Button className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 text-white rounded-xl py-5 font-semibold group">
                          <Play className="w-5 h-5 mr-2 group-hover:scale-110 transition-transform" />
                          Gioca
                        </Button>
                      </Link>
                    ) : (
                      <Button 
                        disabled 
                        className="w-full bg-gray-100 text-gray-400 rounded-xl py-5 cursor-not-allowed"
                      >
                        <Clock className="w-5 h-5 mr-2" />
                        Presto disponibile
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </section>

      <Footer />
      
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50% { transform: translateY(-15px) rotate(5deg); }
        }
        .animate-float {
          animation: float 3s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default GamesListPage;
