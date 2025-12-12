import React from 'react';
import { Mail, MapPin } from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';

const ContattiLegaliPage = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-pink-50 to-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-8">Contatti & Informazioni Legali</h1>
          
          <div className="bg-white rounded-xl shadow-lg p-8">
            <h2 className="text-xl font-bold text-gray-800 mb-6">Titolare:</h2>
            
            <div className="space-y-4">
              <p className="text-lg font-semibold text-gray-700">Matteo Calipa – Pompiconni Project</p>
              
              <div className="flex items-center gap-3 text-gray-600">
                <MapPin className="w-5 h-5 text-pink-500" />
                <span>Ventimiglia (IM), Italia</span>
              </div>
              
              <div className="flex items-center gap-3 text-gray-600">
                <Mail className="w-5 h-5 text-pink-500" />
                <a href="mailto:pompiconni@gmail.com" className="text-pink-500 hover:text-pink-600 transition-colors">
                  pompiconni@gmail.com
                </a>
              </div>
            </div>
            
            <div className="mt-8 pt-8 border-t border-gray-200">
              <p className="text-gray-600">
                Per richieste legali, rimozioni contenuti, privacy o GDPR contattare l'indirizzo sopra.
              </p>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default ContattiLegaliPage;
