import React from 'react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';

const CookiePolicyPage = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-pink-50 to-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-8">Cookie Policy – Pompiconni</h1>
          
          <div className="prose prose-lg max-w-none text-gray-700">
            <div className="space-y-8">
              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">1. Cosa sono i cookie</h2>
                <p>Piccoli file inviati al browser per garantire funzionalità tecniche del sito.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">2. Tipologie di cookie usati</h2>
                <ul className="list-disc pl-6 space-y-2">
                  <li><strong>Cookie tecnici (sempre attivi):</strong> sessione admin, sicurezza, funzionalità di navigazione.</li>
                  <li><strong>Cookie di terze parti:</strong> solo se attivati in futuro (es. Analytics). In tal caso verrà richiesto consenso.</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">3. Cookie NON presenti</h2>
                <p>Nessun cookie pubblicitario o di profilazione.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">4. Gestione dei cookie</h2>
                <p>L'utente può accettare, rifiutare o modificare le preferenze tramite banner cookie.</p>
              </section>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default CookiePolicyPage;
