import React from 'react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';

const TerminiCondizioniPage = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-pink-50 to-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-8">Termini e Condizioni d'Uso – Pompiconni</h1>
          
          <div className="prose prose-lg max-w-none text-gray-700">
            <div className="space-y-8">
              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">1. Oggetto</h2>
                <p>Il sito offre contenuti illustrati e schede da colorare.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">2. Diritti d'autore</h2>
                <p className="mb-2">Tutti i contenuti sono di proprietà esclusiva di:</p>
                <p className="font-semibold">Matteo Calipa – Pompiconni Project</p>
                <p className="mt-2">È vietata la distribuzione commerciale senza autorizzazione.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">3. Uso consentito</h2>
                <p>Uso personale o educativo; vietato uso commerciale non autorizzato.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">4. Limitazione responsabilità</h2>
                <p>Nessuna garanzia di continuità o assenza errori.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">5. Contenuti per bambini</h2>
                <p>Contenuti destinati ai minori, senza raccolta dati.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">6. Legge applicabile</h2>
                <p>Italia; GDPR.</p>
              </section>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default TerminiCondizioniPage;
