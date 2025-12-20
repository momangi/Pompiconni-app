import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Play, Clock, ArrowLeft, Star, Users, Sparkles } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getGame } from '../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const GameDetailPage = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [game, setGame] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchGame = async () => {
      try {
        const data = await getGame(slug);
        setGame(data);
      } catch (error) {
        console.error('Error fetching game:', error);
        // Fallback data
        const fallbackGames = {
          'bolle-magiche': {
            id: '1',
            slug: 'bolle-magiche',
            title: 'Bolle Magiche',
            shortDescription: 'Scoppia le bolle colorate con Poppiconni!',
            longDescription: 'Aiuta Poppiconni a scoppiare tutte le bolle colorate che fluttuano nel cielo! Un gioco semplice e divertente, perfetto per i più piccoli. Tocca le bolle per farle scoppiare e accumula punti. Attenzione: le bolle diventano sempre più veloci!',
            status: 'available',
            ageRecommended: '3+',
            howToPlay: [
              'Tocca o clicca sulle bolle per farle scoppiare',
              'Accumula punti scoppiando più bolle possibili',
              'Non lasciare che le bolle raggiungano il fondo!'
            ]
          },
          'puzzle-poppiconni': {
            id: '2',
            slug: 'puzzle-poppiconni',
            title: 'Puzzle Poppiconni',
            shortDescription: 'Ricomponi le immagini di Poppiconni!',
            longDescription: 'Metti alla prova le tue abilità con i puzzle di Poppiconni! Ricomponi le immagini delle avventure del nostro amico elefantino.',
            status: 'coming_soon',
            ageRecommended: '4+',
            howToPlay: [
              'Trascina i pezzi nella posizione corretta',
              'Completa il puzzle per sbloccare nuove immagini',
              'Sfida te stesso con puzzle sempre più difficili!'
            ]
          },
          'memory-poppiconni': {
            id: '3',
            slug: 'memory-poppiconni',
            title: 'Memory Poppiconni',
            shortDescription: 'Trova le coppie con le carte di Poppiconni!',
            longDescription: 'Allena la tua memoria con il gioco di carte Memory! Trova tutte le coppie delle carte con le immagini di Poppiconni.',
            status: 'coming_soon',
            ageRecommended: '3+',
            howToPlay: [
              'Gira due carte alla volta',
              'Cerca di trovare le coppie uguali',
              'Completa il gioco con meno mosse possibili!'
            ]
          }
        };
        setGame(fallbackGames[slug] || null);
      } finally {
        setLoading(false);
      }
    };
    fetchGame();
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-pink-50/30 to-white">
        <Navbar />
        <div className="max-w-4xl mx-auto px-4 py-20">
          <div className="animate-pulse">
            <div className="h-64 bg-gray-200 rounded-2xl mb-8" />
            <div className="h-10 bg-gray-200 rounded w-1/2 mb-4" />
            <div className="h-4 bg-gray-200 rounded mb-2" />
            <div className="h-4 bg-gray-200 rounded w-3/4" />
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  if (!game) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-pink-50/30 to-white">
        <Navbar />
        <div className="max-w-4xl mx-auto px-4 py-20 text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">Gioco non trovato</h1>
          <Link to="/giochi">
            <Button>Torna ai giochi</Button>
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-pink-50/30 to-white relative">
      {/* Page Background Image (if exists) */}
      {game.pageImageUrl && (
        <div 
          className="fixed inset-0 bg-cover bg-center pointer-events-none"
          style={{ 
            backgroundImage: `url(${BACKEND_URL}${game.pageImageUrl})`,
            opacity: (game.pageImageOpacity || 25) / 100,
            zIndex: 0
          }}
        />
      )}
      
      <div className="relative z-10">
        <Navbar />
      
      {/* Back Button */}
      <div className="max-w-4xl mx-auto px-4 pt-6">
        <Link to="/giochi" className="inline-flex items-center text-gray-600 hover:text-pink-600 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Torna ai giochi
        </Link>
      </div>

      {/* Hero Section */}
      <section className="py-8">
        <div className="max-w-4xl mx-auto px-4">
          {/* Cover Image */}
          <div className="h-64 sm:h-80 rounded-3xl overflow-hidden bg-gradient-to-br from-pink-100 via-purple-50 to-blue-100 relative mb-8 shadow-xl">
            {game.thumbnailUrl ? (
              <img 
                src={`${BACKEND_URL}${game.thumbnailUrl}`}
                alt={game.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center relative overflow-hidden">
                {/* Animated bubbles background */}
                {[...Array(12)].map((_, i) => (
                  <div
                    key={i}
                    className="absolute rounded-full animate-bubble-float"
                    style={{
                      width: `${40 + Math.random() * 60}px`,
                      height: `${40 + Math.random() * 60}px`,
                      left: `${5 + Math.random() * 90}%`,
                      top: `${5 + Math.random() * 90}%`,
                      background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.9), rgba(236,72,153,0.2))`,
                      boxShadow: 'inset 0 0 30px rgba(255,255,255,0.6), 0 0 15px rgba(255,255,255,0.4)',
                      animationDelay: `${i * 0.3}s`,
                      animationDuration: `${4 + Math.random() * 3}s`
                    }}
                  />
                ))}
                <div className="text-center relative z-10">
                  <Sparkles className="w-20 h-20 text-pink-400 mx-auto mb-4" />
                  <span className="text-pink-500 font-semibold text-lg">{game.title}</span>
                </div>
              </div>
            )}
            
            {/* Status Badge */}
            <div className="absolute top-6 right-6">
              {game.status === 'available' ? (
                <Badge className="bg-green-100 text-green-700 border-green-200 text-sm px-3 py-1">Disponibile</Badge>
              ) : (
                <Badge className="bg-amber-100 text-amber-700 border-amber-200 text-sm px-3 py-1">In arrivo</Badge>
              )}
            </div>
          </div>

          {/* Game Info */}
          <div className="space-y-8">
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-4">{game.title}</h1>
              <p className="text-lg text-gray-600">{game.longDescription || game.shortDescription}</p>
            </div>

            {/* Age & Info Badges */}
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2 bg-pink-50 px-4 py-2 rounded-full">
                <Users className="w-5 h-5 text-pink-500" />
                <span className="text-sm font-medium text-gray-700">Età consigliata: {game.ageRecommended || '3+'}</span>
              </div>
              <div className="flex items-center gap-2 bg-purple-50 px-4 py-2 rounded-full">
                <Star className="w-5 h-5 text-purple-500" />
                <span className="text-sm font-medium text-gray-700">Gioco gratuito</span>
              </div>
            </div>

            {/* How to Play */}
            {game.howToPlay && game.howToPlay.length > 0 && (
              <div className="bg-gradient-to-br from-pink-50 to-purple-50 rounded-2xl p-6">
                <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-pink-500" />
                  Come si gioca
                </h2>
                <ol className="space-y-3">
                  {game.howToPlay.map((step, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-7 h-7 bg-gradient-to-br from-pink-400 to-purple-400 text-white rounded-full flex items-center justify-center text-sm font-bold">
                        {index + 1}
                      </span>
                      <span className="text-gray-700 pt-0.5">{step}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Play Button */}
            <div className="pt-4">
              {game.status === 'available' ? (
                <Button 
                  onClick={() => navigate(`/giochi/${slug}/play`)}
                  className="w-full sm:w-auto bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 text-white rounded-xl py-6 px-10 text-lg font-semibold shadow-lg hover:shadow-xl transition-all"
                >
                  <Play className="w-6 h-6 mr-2" />
                  Gioca ora
                </Button>
              ) : (
                <Button 
                  disabled
                  className="w-full sm:w-auto bg-gray-100 text-gray-400 rounded-xl py-6 px-10 text-lg cursor-not-allowed"
                >
                  <Clock className="w-6 h-6 mr-2" />
                  In arrivo
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>

      <Footer />
      
      <style>{`
        @keyframes bubble-float {
          0%, 100% { transform: translateY(0) scale(1); opacity: 0.7; }
          50% { transform: translateY(-20px) scale(1.05); opacity: 0.9; }
        }
        .animate-bubble-float {
          animation: bubble-float 4s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default GameDetailPage;
