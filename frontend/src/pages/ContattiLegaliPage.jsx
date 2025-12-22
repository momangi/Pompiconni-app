import React, { useState, useEffect } from 'react';
import { Mail, MapPin, Building2, FileText, Loader2 } from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getSiteSettings } from '../services/api';

const ContattiLegaliPage = () => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await getSiteSettings();
        setSettings(data);
      } catch (error) {
        console.error('Error fetching settings:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  // Check if a field should be shown (has value AND show flag is true)
  const shouldShow = (value, showFlag) => {
    return value && value.trim() !== '' && showFlag;
  };

  // Check if there are any legal info to display
  const hasAnyLegalInfo = settings && (
    shouldShow(settings.legalCompanyName, settings.showLegalCompanyName) ||
    shouldShow(settings.legalAddress, settings.showLegalAddress) ||
    shouldShow(settings.legalVatNumber, settings.showLegalVatNumber) ||
    shouldShow(settings.legalEmail, settings.showLegalEmail) ||
    shouldShow(settings.legalPecEmail, settings.showLegalPecEmail)
  );

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-pink-50 to-white py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-8">Contatti & Informazioni Legali</h1>
          
          <div className="bg-white rounded-xl shadow-lg p-8">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-pink-500 animate-spin" />
              </div>
            ) : hasAnyLegalInfo ? (
              <>
                <h2 className="text-xl font-bold text-gray-800 mb-6">Titolare:</h2>
                
                <div className="space-y-4">
                  {/* Company Name */}
                  {shouldShow(settings.legalCompanyName, settings.showLegalCompanyName) && (
                    <div className="flex items-center gap-3 text-gray-700">
                      <Building2 className="w-5 h-5 text-pink-500 flex-shrink-0" />
                      <span className="text-lg font-semibold">{settings.legalCompanyName}</span>
                    </div>
                  )}
                  
                  {/* Address */}
                  {shouldShow(settings.legalAddress, settings.showLegalAddress) && (
                    <div className="flex items-center gap-3 text-gray-600">
                      <MapPin className="w-5 h-5 text-pink-500 flex-shrink-0" />
                      <span>{settings.legalAddress}</span>
                    </div>
                  )}
                  
                  {/* VAT Number */}
                  {shouldShow(settings.legalVatNumber, settings.showLegalVatNumber) && (
                    <div className="flex items-center gap-3 text-gray-600">
                      <FileText className="w-5 h-5 text-pink-500 flex-shrink-0" />
                      <span>P.IVA: {settings.legalVatNumber}</span>
                    </div>
                  )}
                  
                  {/* Email */}
                  {shouldShow(settings.legalEmail, settings.showLegalEmail) && (
                    <div className="flex items-center gap-3 text-gray-600">
                      <Mail className="w-5 h-5 text-pink-500 flex-shrink-0" />
                      <a 
                        href={`mailto:${settings.legalEmail}`} 
                        className="text-pink-500 hover:text-pink-600 transition-colors"
                      >
                        {settings.legalEmail}
                      </a>
                    </div>
                  )}
                  
                  {/* PEC Email */}
                  {shouldShow(settings.legalPecEmail, settings.showLegalPecEmail) && (
                    <div className="flex items-center gap-3 text-gray-600">
                      <Mail className="w-5 h-5 text-pink-500 flex-shrink-0" />
                      <div>
                        <span className="text-xs text-gray-400 block">PEC:</span>
                        <a 
                          href={`mailto:${settings.legalPecEmail}`} 
                          className="text-pink-500 hover:text-pink-600 transition-colors"
                        >
                          {settings.legalPecEmail}
                        </a>
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="mt-8 pt-8 border-t border-gray-200">
                  <p className="text-gray-600">
                    Per richieste legali, rimozioni contenuti, privacy o GDPR contattare l&apos;indirizzo sopra.
                  </p>
                </div>
              </>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500">
                  Le informazioni di contatto non sono ancora state configurate.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default ContattiLegaliPage;
