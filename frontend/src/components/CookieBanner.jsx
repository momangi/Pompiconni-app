import React, { useState, useEffect } from 'react';
import { Cookie, X, Settings } from 'lucide-react';
import { Button } from './ui/button';

const CookieBanner = () => {
  const [showBanner, setShowBanner] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('pompiconni_cookie_consent');
    if (!consent) {
      setShowBanner(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('pompiconni_cookie_consent', 'accepted');
    localStorage.setItem('pompiconni_cookie_date', new Date().toISOString());
    setShowBanner(false);
  };

  const handleReject = () => {
    localStorage.setItem('pompiconni_cookie_consent', 'rejected');
    localStorage.setItem('pompiconni_cookie_date', new Date().toISOString());
    setShowBanner(false);
  };

  const handleSavePreferences = () => {
    localStorage.setItem('pompiconni_cookie_consent', 'custom');
    localStorage.setItem('pompiconni_cookie_date', new Date().toISOString());
    setShowBanner(false);
    setShowPreferences(false);
  };

  if (!showBanner) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
          {!showPreferences ? (
            <div className="p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-pink-100 rounded-xl flex items-center justify-center flex-shrink-0">
                  <Cookie className="w-6 h-6 text-pink-500" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-gray-800 mb-2">Informativa Cookie</h3>
                  <p className="text-gray-600 text-sm leading-relaxed">
                    Questo sito utilizza cookie tecnici necessari al funzionamento e, previo consenso, 
                    cookie opzionali per migliorare l'esperienza. Puoi accettare, rifiutare o gestire le preferenze.
                  </p>
                </div>
              </div>
              
              <div className="flex flex-wrap gap-3 mt-6 justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowPreferences(true)}
                  className="border-gray-300 text-gray-600 hover:bg-gray-50"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Gestisci preferenze
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleReject}
                  className="border-gray-300 text-gray-600 hover:bg-gray-50"
                >
                  Rifiuta
                </Button>
                <Button
                  size="sm"
                  onClick={handleAccept}
                  className="bg-pink-500 hover:bg-pink-600 text-white"
                >
                  Accetta
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-gray-800">Gestisci preferenze cookie</h3>
                <button
                  onClick={() => setShowPreferences(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="space-y-4 mb-6">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-800">Cookie tecnici</p>
                    <p className="text-sm text-gray-500">Necessari per il funzionamento del sito</p>
                  </div>
                  <span className="text-sm text-green-600 font-medium">Sempre attivi</span>
                </div>
                
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-800">Cookie opzionali</p>
                    <p className="text-sm text-gray-500">Attualmente non utilizzati</p>
                  </div>
                  <span className="text-sm text-gray-400 font-medium">Non attivi</span>
                </div>
              </div>
              
              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowPreferences(false)}
                >
                  Annulla
                </Button>
                <Button
                  size="sm"
                  onClick={handleSavePreferences}
                  className="bg-pink-500 hover:bg-pink-600 text-white"
                >
                  Salva preferenze
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CookieBanner;
