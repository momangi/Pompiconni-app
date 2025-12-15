import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Book, BookOpen, Eye, Download } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getBooks, getSiteSettings } from '../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const BooksPage = () => {
  const [books, setBooks] = useState([]);
  const [siteSettings, setSiteSettings] = useState({ stripe_enabled: false });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [booksData, settingsData] = await Promise.all([
          getBooks(),
          getSiteSettings()
        ]);
        setBooks(booksData);
        setSiteSettings(settingsData);
      } catch (error) {
        console.error('Error fetching books:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

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

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      {/* Hero Section */}
      <section className="py-16 bg-gradient-to-b from-pink-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-pink-200 to-blue-200 rounded-3xl mb-6">
              <BookOpen className="w-10 h-10 text-pink-500" />
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 mb-4">
              Libri <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-blue-400">Poppiconni</span>
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Storie illustrate da leggere e colorare insieme al tuo unicorno preferito!
            </p>
          </div>
        </div>
      </section>

      {/* Books Grid */}
      <section className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {books.length === 0 ? (
            <div className="text-center py-20">
              <Book className="w-20 h-20 text-gray-200 mx-auto mb-6" />
              <h2 className="text-2xl font-bold text-gray-400 mb-2">Prossimamente...</h2>
              <p className="text-gray-400">I libri di Poppiconni stanno arrivando!</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {books.map((book) => (
                <Card key={book.id} className="group border-0 shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden">
                  {/* Cover Image */}
                  <div className="relative h-64 bg-gradient-to-br from-pink-100 to-blue-100 flex items-center justify-center overflow-hidden">
                    {book.coverImageFileId ? (
                      <img 
                        src={`${BACKEND_URL}/api/books/${book.id}/cover`}
                        alt={book.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="text-center">
                        <div className="text-6xl mb-2">📖</div>
                        <div className="text-4xl">🦄</div>
                      </div>
                    )}
                    
                    {/* Badges */}
                    <div className="absolute top-3 left-3 flex gap-2">
                      {book.isFree ? (
                        <Badge className="bg-green-500 text-white">Gratis</Badge>
                      ) : (
                        <Badge className="bg-pink-500 text-white">Premium</Badge>
                      )}
                    </div>
                    
                    {/* Scene count */}
                    <div className="absolute bottom-3 right-3">
                      <Badge variant="secondary" className="bg-white/90">
                        {book.sceneCount} scene
                      </Badge>
                    </div>
                  </div>
                  
                  <CardContent className="p-5">
                    <h3 className="font-bold text-lg text-gray-800 mb-2 line-clamp-1">{book.title}</h3>
                    <p className="text-sm text-gray-600 mb-4 line-clamp-2">{book.description}</p>
                    
                    <div className="flex items-center justify-between">
                      {book.isFree || siteSettings.stripe_enabled ? (
                        <Link to={`/libri/${book.id}`} className="flex-1">
                          <Button className="w-full bg-pink-500 hover:bg-pink-600">
                            <Eye className="w-4 h-4 mr-2" />
                            Leggi Ora
                          </Button>
                        </Link>
                      ) : (
                        <div className="flex-1 text-center p-3 bg-yellow-50 rounded-lg">
                          <p className="text-xs text-yellow-700">Pagamenti non ancora attivi</p>
                        </div>
                      )}
                    </div>
                    
                    {!book.isFree && (
                      <p className="text-center text-pink-500 font-semibold mt-3">
                        €{book.price?.toFixed(2)}
                      </p>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Info Section */}
      <section className="py-16 bg-gradient-to-b from-white to-pink-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            Ogni libro è un&apos;avventura!
          </h2>
          <p className="text-gray-600 mb-8">
            Leggi le storie di Poppiconni e poi colora le scene: ogni pagina ha una versione 
            colorata per la lettura e una versione in bianco e nero da colorare!
          </p>
          <div className="flex flex-wrap justify-center gap-6">
            <div className="flex items-center gap-2 text-gray-600">
              <div className="w-10 h-10 bg-pink-100 rounded-full flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-pink-500" />
              </div>
              <span>Storie illustrate</span>
            </div>
            <div className="flex items-center gap-2 text-gray-600">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-xl">🎨</span>
              </div>
              <span>Tavole da colorare</span>
            </div>
            <div className="flex items-center gap-2 text-gray-600">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <Download className="w-5 h-5 text-green-500" />
              </div>
              <span>Scaricabili in PDF</span>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default BooksPage;
