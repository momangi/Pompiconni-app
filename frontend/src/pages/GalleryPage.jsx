import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BookOpen } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { themes } from '../data/mock';

const GalleryPage = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-pink-50 to-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 mb-4">
              <span className="gradient-text">Galleria</span> Tematica
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Esplora tutti i temi disponibili e scopri le avventure di Pompiconni!
            </p>
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {themes.map((theme) => (
              <Link key={theme.id} to={`/galleria/${theme.id}`}>
                <Card className="border-0 shadow-xl hover-lift overflow-hidden group cursor-pointer h-full">
                  <div className="h-48 flex items-center justify-center relative overflow-hidden" style={{ backgroundColor: theme.color + '40' }}>
                    <div className="absolute inset-0 opacity-30 transition-opacity group-hover:opacity-40" style={{ backgroundColor: theme.color }} />
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
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default GalleryPage;
