import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, Home, BookOpen, Download, Maximize2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getBook, getReadingProgress, saveReadingProgress, getSiteSettings } from '../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Generate a simple visitor ID for tracking progress
const getVisitorId = () => {
  let id = localStorage.getItem('pompiconni_visitor_id');
  if (!id) {
    id = 'visitor_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
    localStorage.setItem('pompiconni_visitor_id', id);
  }
  return id;
};

const BookReaderPage = () => {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const [book, setBook] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [currentScene, setCurrentScene] = useState(1);
  const [loading, setLoading] = useState(true);
  const [siteSettings, setSiteSettings] = useState({ stripe_enabled: false });
  const [showResume, setShowResume] = useState(false);
  const [savedProgress, setSavedProgress] = useState(1);

  const visitorId = getVisitorId();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [bookData, settingsData, progressData] = await Promise.all([
          getBook(bookId),
          getSiteSettings(),
          getReadingProgress(bookId, visitorId)
        ]);
        
        setBook(bookData.book);
        setScenes(bookData.scenes);
        setSiteSettings(settingsData);
        
        // Check for saved progress
        if (progressData.hasProgress && progressData.currentScene > 1) {
          setSavedProgress(progressData.currentScene);
          setShowResume(true);
        }
      } catch (error) {
        console.error('Error fetching book:', error);
        toast.error('Errore nel caricamento del libro');
        navigate('/libri');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [bookId, visitorId, navigate]);

  // Save progress when scene changes
  const saveProgress = useCallback(async (scene) => {
    try {
      await saveReadingProgress(bookId, visitorId, scene);
    } catch (error) {
      console.error('Error saving progress:', error);
    }
  }, [bookId, visitorId]);

  const goToScene = (scene) => {
    if (scene >= 1 && scene <= scenes.length) {
      setCurrentScene(scene);
      saveProgress(scene);
      setShowResume(false);
    }
  };

  const handleResume = () => {
    setCurrentScene(savedProgress);
    setShowResume(false);
  };

  const handleStartFresh = () => {
    setCurrentScene(1);
    setShowResume(false);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        goToScene(currentScene + 1);
      } else if (e.key === 'ArrowLeft') {
        goToScene(currentScene - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentScene, scenes.length]);

  if (loading) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin w-12 h-12 border-4 border-pink-500 border-t-transparent rounded-full" />
        </div>
        <Footer />
      </div>
    );
  }

  if (!book) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex flex-col items-center justify-center h-96">
          <p className="text-gray-500 mb-4">Libro non trovato</p>
          <Link to="/libri">
            <Button variant="outline">Torna ai Libri</Button>
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  const currentSceneData = scenes.find(s => s.sceneNumber === currentScene);
  
  // Font size styles for TipTap HTML rendering
  const fontSizeStyles = `
    .scene-text .font-size-s { font-size: 0.875rem; line-height: 1.4; }
    .scene-text .font-size-m { font-size: 1rem; line-height: 1.5; }
    .scene-text .font-size-l { font-size: 1.25rem; line-height: 1.6; }
    .scene-text p { margin-bottom: 0.75rem; }
    .scene-text ul { list-style-type: disc; padding-left: 1.5rem; margin-bottom: 0.75rem; }
    .scene-text li { margin-bottom: 0.25rem; }
    .scene-text p[style*="text-align: center"], .scene-text .text-center { text-align: center; }
    .scene-text p[style*="text-align: right"], .scene-text .text-right { text-align: right; }
  `;

  return (
    <div className="min-h-screen bg-gradient-to-b from-pink-50 to-white">
      <style>{fontSizeStyles}</style>
      <Navbar />
      
      {/* Resume Modal */}
      {showResume && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full text-center shadow-2xl">
            <div className="text-5xl mb-4">📖</div>
            <h3 className="text-xl font-bold text-gray-800 mb-2">Bentornato!</h3>
            <p className="text-gray-600 mb-6">
              Hai lasciato la lettura alla scena {savedProgress} di {scenes.length}
            </p>
            <div className="space-y-3">
              <Button 
                className="w-full bg-pink-500 hover:bg-pink-600"
                onClick={handleResume}
              >
                Riprendi da dove eri rimasto
              </Button>
              <Button 
                variant="outline" 
                className="w-full"
                onClick={handleStartFresh}
              >
                Ricomincia dall&apos;inizio
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/libri">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-1" />
                Indietro
              </Button>
            </Link>
            <div>
              <h1 className="font-bold text-gray-800 line-clamp-1">{book.title}</h1>
              <p className="text-xs text-gray-500">Scena {currentScene} di {scenes.length}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {book.allowDownload && (
              <Button variant="outline" size="sm" className="hidden sm:flex">
                <Download className="w-4 h-4 mr-1" />
                PDF
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Reader Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {scenes.length === 0 ? (
          <div className="text-center py-20">
            <BookOpen className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">Questo libro non ha ancora scene</p>
          </div>
        ) : currentSceneData ? (
          <>
            {/* Desktop: Side by side */}
            <div className="hidden md:grid md:grid-cols-2 gap-6 mb-8">
              {/* Left Page: Text + Colored Image */}
              <div className="bg-white rounded-2xl shadow-lg overflow-hidden border-2 border-pink-100">
                <div className="p-6 min-h-[500px] flex flex-col">
                  {/* Text */}
                  <div 
                    className="scene-text flex-1 text-gray-700 leading-relaxed mb-4"
                    dangerouslySetInnerHTML={{ 
                      __html: currentSceneData?.text?.html || '<p class="text-gray-400 italic">Testo della storia...</p>' 
                    }}
                  />
                  
                  {/* Colored Image (soft, faded) */}
                  <div className="h-64 bg-gradient-to-b from-pink-50 to-blue-50 rounded-xl flex items-center justify-center overflow-hidden">
                    {currentSceneData?.coloredImageFileId ? (
                      <img 
                        src={`${BACKEND_URL}/api/books/${bookId}/scene/${currentScene}/colored-image`}
                        alt={`Scena ${currentScene} - colorata`}
                        className="w-full h-full object-contain opacity-80"
                      />
                    ) : (
                      <div className="text-6xl opacity-30">🦄</div>
                    )}
                  </div>
                </div>
                <div className="bg-pink-50 px-4 py-2 text-center">
                  <span className="text-xs text-pink-500">Pagina {currentScene * 2 - 1}</span>
                </div>
              </div>

              {/* Right Page: Line Art for coloring */}
              <div className="bg-white rounded-2xl shadow-lg overflow-hidden border-2 border-blue-100">
                <div className="p-6 min-h-[500px] flex flex-col">
                  <div className="flex-1 flex items-center justify-center bg-gray-50 rounded-xl">
                    {currentSceneData?.lineArtImageFileId ? (
                      <img 
                        src={`${BACKEND_URL}/api/books/${bookId}/scene/${currentScene}/lineart-image`}
                        alt={`Scena ${currentScene} - da colorare`}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center text-gray-400">
                        <div className="text-6xl mb-2">🎨</div>
                        <p className="text-sm">Tavola da colorare</p>
                      </div>
                    )}
                  </div>
                </div>
                <div className="bg-blue-50 px-4 py-2 text-center">
                  <span className="text-xs text-blue-500">Pagina {currentScene * 2} - Da colorare</span>
                </div>
              </div>
            </div>

            {/* Mobile: Stacked */}
            <div className="md:hidden space-y-4 mb-8">
              {/* Text + Colored Image */}
              <div className="bg-white rounded-2xl shadow-lg overflow-hidden border-2 border-pink-100">
                <div className="p-4">
                  <div className={`${fontSize} ${textAlign} ${currentSceneData?.text?.isBold ? 'font-bold' : ''} ${currentSceneData?.text?.isItalic ? 'italic' : ''} text-gray-700 leading-relaxed whitespace-pre-wrap mb-4`}>
                    {currentSceneData?.text?.content || 'Testo della storia...'}
                  </div>
                  <div className="h-48 bg-gradient-to-b from-pink-50 to-blue-50 rounded-xl flex items-center justify-center overflow-hidden">
                    {currentSceneData?.coloredImageFileId ? (
                      <img 
                        src={`${BACKEND_URL}/api/books/${bookId}/scene/${currentScene}/colored-image`}
                        alt={`Scena ${currentScene} - colorata`}
                        className="w-full h-full object-contain opacity-80"
                      />
                    ) : (
                      <div className="text-5xl opacity-30">🦄</div>
                    )}
                  </div>
                </div>
              </div>

              {/* Line Art */}
              <div className="bg-white rounded-2xl shadow-lg overflow-hidden border-2 border-blue-100">
                <div className="p-4">
                  <p className="text-xs text-blue-500 mb-2 text-center">✏️ Da colorare</p>
                  <div className="h-48 bg-gray-50 rounded-xl flex items-center justify-center overflow-hidden">
                    {currentSceneData?.lineArtImageFileId ? (
                      <img 
                        src={`${BACKEND_URL}/api/books/${bookId}/scene/${currentScene}/lineart-image`}
                        alt={`Scena ${currentScene} - da colorare`}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center text-gray-400">
                        <div className="text-5xl">🎨</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-500">Scena non trovata</p>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="lg"
            onClick={() => goToScene(currentScene - 1)}
            disabled={currentScene <= 1}
            className="rounded-full"
          >
            <ChevronLeft className="w-5 h-5" />
          </Button>
          
          {/* Scene indicators */}
          <div className="flex gap-2 overflow-x-auto max-w-xs sm:max-w-md">
            {scenes.map((scene) => (
              <button
                key={scene.id}
                onClick={() => goToScene(scene.sceneNumber)}
                className={`w-8 h-8 rounded-full text-xs font-medium transition-all flex-shrink-0 ${
                  scene.sceneNumber === currentScene
                    ? 'bg-pink-500 text-white scale-110'
                    : 'bg-gray-100 text-gray-600 hover:bg-pink-100'
                }`}
              >
                {scene.sceneNumber}
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="lg"
            onClick={() => goToScene(currentScene + 1)}
            disabled={currentScene >= scenes.length}
            className="rounded-full"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        {/* End of book */}
        {currentScene === scenes.length && scenes.length > 0 && (
          <div className="text-center mt-12 p-8 bg-gradient-to-r from-pink-50 to-blue-50 rounded-2xl">
            <div className="text-5xl mb-4">🎉</div>
            <h3 className="text-xl font-bold text-gray-800 mb-2">Fine della storia!</h3>
            <p className="text-gray-600 mb-4">Hai finito di leggere &quot;{book.title}&quot;</p>
            <div className="flex justify-center gap-3">
              <Button variant="outline" onClick={() => goToScene(1)}>
                Rileggi
              </Button>
              <Link to="/libri">
                <Button className="bg-pink-500 hover:bg-pink-600">
                  Altri Libri
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>

      <Footer />
    </div>
  );
};

export default BookReaderPage;
