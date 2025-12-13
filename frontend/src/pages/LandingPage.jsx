import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Download, Sparkles, Star, Heart, BookOpen, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getThemes, getBundles, getReviews, getIllustrations, getSiteSettings } from '../services/api';

const LandingPage = () => {
  const [themes, setThemes] = useState([]);
  const [bundles, setBundles] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [illustrations, setIllustrations] = useState([]);
  const [siteSettings, setSiteSettings] = useState({ stripe_enabled: false });
  const [currentReviewIndex, setCurrentReviewIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [themesData, bundlesData, reviewsData, illustrationsData, settingsData] = await Promise.all([
          getThemes(),
          getBundles(),
          getReviews(),
          getIllustrations(),
          getSiteSettings()
        ]);
        setThemes(themesData);
        setBundles(bundlesData);
        setReviews(reviewsData);
        setIllustrations(illustrationsData);
        setSiteSettings(settingsData);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Auto-rotate reviews every 15 seconds
  useEffect(() => {
    if (reviews.length === 0) return;
    
    const interval = setInterval(() => {
      setCurrentReviewIndex((prev) => (prev + 1) % reviews.length);
    }, 15000);
    
    return () => clearInterval(interval);
  }, [reviews.length]);

  const nextReview = () => {
    setCurrentReviewIndex((prev) => (prev + 1) % reviews.length);
  };

  const prevReview = () => {
    setCurrentReviewIndex((prev) => (prev - 1 + reviews.length) % reviews.length);
  };

  const currentReview = reviews[currentReviewIndex];

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-pink-50 via-white to-blue-50">
        <div className="absolute inset-0 pattern-stars opacity-30" />
        <div className="absolute top-20 left-10 w-20 h-20 bg-pink-200 rounded-full blur-3xl opacity-50" />
        <div className="absolute top-40 right-20 w-32 h-32 bg-blue-200 rounded-full blur-3xl opacity-50" />
        <div className="absolute bottom-20 left-1/4 w-24 h-24 bg-yellow-200 rounded-full blur-3xl opacity-50" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="text-left">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-pink-100 rounded-full mb-6">
                <Sparkles className="w-4 h-4 text-pink-500" />
                <span className="text-sm font-medium text-pink-600">Libri da colorare per bambini</span>
              </div>
              
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-800 mb-6 leading-tight">
                Ciao, sono{' '}
                <span className="gradient-text">Pompiconni!</span>
              </h1>
              
              <p className="text-lg sm:text-xl text-gray-600 mb-8 max-w-xl">
                Un unicorno dolce, simpatico e leggermente impacciato che ti accompagnerà 
                in tante avventure da colorare. Scopri i mestieri, la fattoria, lo zoo e tanto altro!
              </p>
              
              <div className="flex flex-wrap gap-4">
                <Link to="/galleria">
                  <Button size="lg" className="bg-pink-500 hover:bg-pink-600 text-white px-8 py-6 text-lg rounded-xl hover-lift">
                    Esplora la Galleria
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
                <Link to="/download">
                  <Button size="lg" variant="outline" className="border-2 border-pink-300 text-pink-600 hover:bg-pink-50 px-8 py-6 text-lg rounded-xl">
                    <Download className="w-5 h-5 mr-2" />
                    Scarica Gratis
                  </Button>
                </Link>
              </div>
              
              <div className="flex gap-8 mt-12">
                <div>
                  <p className="text-3xl font-bold text-pink-500">{illustrations.length}+</p>
                  <p className="text-gray-500">Tavole da colorare</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-blue-400">{themes.length}</p>
                  <p className="text-gray-500">Temi diversi</p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-green-400">3-9</p>
                  <p className="text-gray-500">Anni età</p>
                </div>
              </div>
            </div>
            
            <div className="relative flex justify-center lg:justify-end">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-br from-pink-200 via-blue-100 to-green-100 rounded-full blur-3xl opacity-60 scale-110" />
                <div className="relative w-80 h-80 sm:w-96 sm:h-96 bg-gradient-to-br from-pink-100 to-blue-100 rounded-3xl flex items-center justify-center animate-float soft-shadow">
                  <div className="text-center">
                    <div className="text-8xl mb-4">🦄</div>
                    <p className="text-gray-500 font-medium">Pompiconni</p>
                    <p className="text-sm text-gray-400">Il tuo amico unicorno</p>
                  </div>
                </div>
                <div className="absolute -top-4 -right-4 w-16 h-16 bg-yellow-100 rounded-2xl flex items-center justify-center animate-wiggle shadow-lg">
                  <Star className="w-8 h-8 text-yellow-400 fill-yellow-400" />
                </div>
                <div className="absolute -bottom-4 -left-4 w-14 h-14 bg-pink-100 rounded-2xl flex items-center justify-center animate-wiggle shadow-lg" style={{ animationDelay: '0.5s' }}>
                  <Heart className="w-7 h-7 text-pink-400 fill-pink-400" />
                </div>
                <div className="absolute top-1/2 -left-8 w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center animate-float shadow-lg" style={{ animationDelay: '1s' }}>
                  <Sparkles className="w-6 h-6 text-blue-400" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* About Character */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-4">
              Chi è <span className="gradient-text">Pompiconni</span>?
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Un unicorno speciale creato per far sognare e divertire i bambini
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <Card className="border-0 shadow-lg hover-lift bg-gradient-to-b from-white to-gray-50">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-pink-100 flex items-center justify-center">
                  <Heart className="w-8 h-8 text-pink-500" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Dolce</h3>
                <p className="text-gray-600">Con i suoi occhi grandi e le guanciotte rosate, Pompiconni conquista tutti con la sua dolcezza</p>
              </CardContent>
            </Card>
            <Card className="border-0 shadow-lg hover-lift bg-gradient-to-b from-white to-gray-50">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-blue-100 flex items-center justify-center">
                  <Sparkles className="w-8 h-8 text-blue-500" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Simpatico</h3>
                <p className="text-gray-600">Sempre pronto a far sorridere con le sue espressioni buffe e le sue avventure divertenti</p>
              </CardContent>
            </Card>
            <Card className="border-0 shadow-lg hover-lift bg-gradient-to-b from-white to-gray-50">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-yellow-100 flex items-center justify-center">
                  <Star className="w-8 h-8 text-yellow-500" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-3">Impacciato</h3>
                <p className="text-gray-600">Un po' goffo ma adorabile, si caccia sempre in situazioni comiche ma trova sempre la soluzione</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Themes */}
      <section className="py-20 bg-gradient-to-b from-blue-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-4">
              Scopri i <span className="gradient-text">Temi</span>
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Pompiconni ti aspetta in tante avventure diverse. Scegli il tuo tema preferito!
            </p>
          </div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {themes.map((theme) => (
              <Link key={theme.id} to={`/galleria/${theme.id}`}>
                <Card className="border-0 shadow-lg hover-lift overflow-hidden group cursor-pointer h-full">
                  <div className="h-40 flex items-center justify-center relative overflow-hidden" style={{ backgroundColor: theme.color + '40' }}>
                    <div className="absolute inset-0 opacity-20" style={{ backgroundColor: theme.color }} />
                    <BookOpen className="w-16 h-16 text-gray-600 group-hover:scale-110 transition-transform duration-300" />
                  </div>
                  <CardContent className="p-6">
                    <h3 className="text-xl font-bold text-gray-800 mb-2">{theme.name}</h3>
                    <p className="text-gray-600 text-sm mb-4">{theme.description}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-500">{theme.illustrationCount} tavole</span>
                      <ArrowRight className="w-5 h-5 text-pink-500 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Bundles */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-4">
              <span className="gradient-text">Download</span> & Bundle
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">Scarica le tavole gratuite o scegli un pacchetto completo!</p>
          </div>
          
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {bundles.map((bundle) => (
              <Card key={bundle.id} className={`border-2 hover-lift ${bundle.isFree ? 'border-green-200 bg-green-50/30' : 'border-pink-200'}`}>
                <CardContent className="p-6 text-center">
                  {bundle.isFree && <span className="inline-block px-3 py-1 bg-green-100 text-green-600 text-xs font-semibold rounded-full mb-4">GRATIS</span>}
                  <h3 className="text-lg font-bold text-gray-800 mb-2">{bundle.name}</h3>
                  <p className="text-sm text-gray-600 mb-4">{bundle.description}</p>
                  <p className="text-3xl font-bold text-pink-500 mb-4">{bundle.isFree ? 'Gratis' : `€${bundle.price}`}</p>
                  <p className="text-xs text-gray-500 mb-4">{bundle.illustrationCount} illustrazioni</p>
                  <Button className={`w-full ${bundle.isFree ? 'bg-green-500 hover:bg-green-600' : 'bg-pink-500 hover:bg-pink-600'}`}>
                    <Download className="w-4 h-4 mr-2" />
                    {bundle.isFree ? 'Scarica Ora' : 'Acquista'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Single Review with rotation */}
      <section className="py-20 bg-gradient-to-b from-pink-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-4">Cosa dicono di <span className="gradient-text">Pompiconni</span></h2>
          </div>
          
          {currentReview && (
            <div className="max-w-2xl mx-auto">
              <Card className="border-0 shadow-xl hover-lift">
                <CardContent className="p-8 sm:p-12 text-center">
                  <div className="flex justify-center gap-1 mb-6">
                    {[...Array(currentReview.rating)].map((_, i) => (
                      <Star key={i} className="w-6 h-6 text-yellow-400 fill-yellow-400" />
                    ))}
                  </div>
                  <p className="text-xl text-gray-600 mb-8 italic leading-relaxed">"{currentReview.text}"</p>
                  <div>
                    <p className="font-bold text-gray-800 text-lg">{currentReview.name}</p>
                    <p className="text-gray-500">{currentReview.role}</p>
                  </div>
                </CardContent>
              </Card>
              
              {/* Navigation controls */}
              <div className="flex items-center justify-center gap-4 mt-6">
                <button 
                  onClick={prevReview}
                  className="w-10 h-10 rounded-full bg-white shadow-md flex items-center justify-center hover:bg-pink-50 transition-colors"
                >
                  <ChevronLeft className="w-5 h-5 text-gray-600" />
                </button>
                
                <div className="flex gap-2">
                  {reviews.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => setCurrentReviewIndex(idx)}
                      className={`w-2 h-2 rounded-full transition-all ${
                        idx === currentReviewIndex ? 'bg-pink-500 w-6' : 'bg-gray-300'
                      }`}
                    />
                  ))}
                </div>
                
                <button 
                  onClick={nextReview}
                  className="w-10 h-10 rounded-full bg-white shadow-md flex items-center justify-center hover:bg-pink-50 transition-colors"
                >
                  <ChevronRight className="w-5 h-5 text-gray-600" />
                </button>
              </div>
              
              <p className="text-center text-sm text-gray-400 mt-4">
                {currentReviewIndex + 1} di {reviews.length} recensioni
              </p>
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-gradient-to-r from-pink-100 via-blue-50 to-green-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-6">Pronto a colorare con Pompiconni?</h2>
          <p className="text-lg text-gray-600 mb-8">Scarica subito le tavole gratuite e inizia la tua avventura!</p>
          <Link to="/download">
            <Button size="lg" className="bg-pink-500 hover:bg-pink-600 text-white px-12 py-6 text-lg rounded-xl hover-lift">
              <Download className="w-5 h-5 mr-2" />
              Scarica Gratis
            </Button>
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default LandingPage;
