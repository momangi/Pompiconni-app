import React from 'react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';

const PrivacyPage = () => {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-pink-50 to-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Privacy Policy – Pompiconni</h1>
          <p className="text-gray-500 mb-8">Ultimo aggiornamento: 12 dicembre 2025</p>
          
          <div className="prose prose-lg max-w-none text-gray-700">
            <div className="bg-white rounded-xl shadow-sm p-8 mb-8">
              <h2 className="text-xl font-bold text-gray-800 mb-4">Titolare del trattamento:</h2>
              <p className="mb-2">Matteo Calipa – Pompiconni Project</p>
              <p className="mb-2">Ventimiglia (IM), Italia</p>
              <p>Email: <a href="mailto:pompiconni@gmail.com" className="text-pink-500 hover:text-pink-600">pompiconni@gmail.com</a></p>
            </div>

            <div className="space-y-8">
              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">1. Tipologie di dati raccolti</h2>
                <p className="mb-2">Il sito tratta:</p>
                <ul className="list-disc pl-6 space-y-1">
                  <li>dati tecnici (IP anonimizzato, browser, data e ora, pagine visitate)</li>
                  <li>credenziali admin (solo per accesso amministrativo)</li>
                  <li>dati volontari inviati via email (nome, email, contenuto del messaggio)</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">2. Finalità del trattamento</h2>
                <ul className="list-disc pl-6 space-y-1">
                  <li>funzionamento tecnico del sito</li>
                  <li>sicurezza e prevenzione attività malevole</li>
                  <li>gestione area amministrativa</li>
                  <li>risposta a richieste via email</li>
                  <li>adempimento obblighi legali</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">3. Base giuridica</h2>
                <p>Art. 6(1)(b), Art. 6(1)(f), Art. 6(1)(c) GDPR.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">4. Conservazione dei dati</h2>
                <ul className="list-disc pl-6 space-y-1">
                  <li>dati tecnici: 30 giorni</li>
                  <li>email: per la durata della richiesta</li>
                  <li>credenziali admin: fino a modifica</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">5. Destinatari</h2>
                <p>Sviluppatori e fornitori tecnici. Nessuna cessione a fini commerciali.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">6. Trasferimenti extra-UE</h2>
                <p>Possibili tramite servizi tecnici; adottate garanzie adeguate.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">7. Diritti dell'interessato</h2>
                <p>Art. 15–22 GDPR (accesso, rettifica, cancellazione, limitazione, opposizione, portabilità).</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">8. Sicurezza</h2>
                <p>HTTPS, firewall, password criptate, accesso admin protetto.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">9. Minori</h2>
                <p>Contenuti destinati ai minori, nessuna raccolta dati minori.</p>
              </section>

              <section>
                <h2 className="text-xl font-bold text-gray-800 mb-3">10. Modifiche</h2>
                <p>Policy soggetta a aggiornamenti.</p>
              </section>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default PrivacyPage;
