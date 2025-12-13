import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Download, FileText, Package, Star, Check, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { getBundles, getIllustrations, downloadIllustration, checkDownloadStatus, getSiteSettings } from '../services/api';
import { toast } from 'sonner';

const DownloadPage = () => {
  const [bundles, setBundles] = useState([]);
  const [freeIllustrations, setFreeIllustrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState({});
  const [siteSettings, setSiteSettings] = useState({ stripe_enabled: false });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [bundlesData, illustrationsData, settingsData] = await Promise.all([
          getBundles(),
          getIllustrations(null, true), // Only free illustrations
          getSiteSettings()
        ]);
        setBundles(bundlesData);
        setFreeIllustrations(illustrationsData);
        setSiteSettings(settingsData);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleDownloadIllustration = async (illustration) => {
    // Check if file is available
    try {
      const status = await checkDownloadStatus(illustration.id);
      if (!status.available) {
        toast.error('File non ancora disponibile. Il PDF deve essere caricato dall\'amministratore.');
        return;
      }
    } catch (error) {
      toast.error('Errore nel verificare la disponibilità del file');
      return;
    }
    
    setDownloading(prev => ({ ...prev, [illustration.id]: true }));
    
    try {
      const response = await downloadIllustration(illustration.id);
      
      // Create blob and trigger download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pompiconni_${illustration.title.replace(/\s+/g, '_')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success(`Download di "${illustration.title}" completato!`);
      
      // Refresh to update counts
      const updatedIllustrations = await getIllustrations(null, true);
      setFreeIllustrations(updatedIllustrations);
      
    } catch (error) {
      console.error('Download error:', error);
      if (error.response?.status === 404) {
        toast.error('File non ancora disponibile');
      } else {
        toast.error('Errore durante il download');
      }
    } finally {
      setDownloading(prev => ({ ...prev, [illustration.id]: false }));
    }
  };

  const handleBundleAction = (bundle) => {
    if (bundle.isFree) {
      toast.info('Bundle gratuito - funzionalità in arrivo');
    } else {
      if (!siteSettings.stripe_enabled) {
        toast.error('Pagamenti non ancora attivi');
      } else {
        toast.info('Funzionalità di acquisto in arrivo');
      }
    }
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-green-50 to-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-100 rounded-full mb-6">
              <Download className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-green-700">Download Center</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 mb-4">
              <span className="gradient-text">Scarica</span> le Tavole
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Tavole gratuite e bundle completi pronti per la stampa in formato PDF A4
            </p>
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-800">Tavole Gratuite</h2>
              <p className="text-gray-600">{freeIllustrations.length} tavole disponibili gratis</p>
            </div>
            <Badge variant="secondary" className="bg-green-100 text-green-700 px-4 py-2">
              <Star className="w-4 h-4 mr-1" />100% Gratis
            </Badge>
          </div>
          
          {loading ? (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {[...Array(8)].map((_, idx) => (
                <div key={idx} className="animate-pulse">
                  <div className="h-32 bg-gray-200 rounded-lg mb-4" />
                  <div className="h-4 bg-gray-200 rounded mb-2" />
                  <div className="h-10 bg-gray-200 rounded" />
                </div>
              ))}
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {freeIllustrations.slice(0, 8).map((illustration) => (
                <Card key={illustration.id} className="border-2 border-green-100 hover-lift">
                  <CardContent className="p-4">
                    <div className="h-32 bg-green-50 rounded-lg flex items-center justify-center mb-4">
                      <FileText className="w-12 h-12 text-green-300" />
                    </div>
                    <h3 className="font-semibold text-gray-800 mb-1 truncate">{illustration.title}</h3>
                    <p className="text-sm text-gray-500 mb-4 truncate">{illustration.description}</p>
                    <Button 
                      className="w-full bg-green-500 hover:bg-green-600" 
                      onClick={() => handleDownloadIllustration(illustration)}
                      disabled={downloading[illustration.id]}
                    >
                      {downloading[illustration.id] ? (
                        <>
                          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                          Scaricando...
                        </>
                      ) : (
                        <>
                          <Download className="w-4 h-4 mr-2" />Scarica PDF
                        </>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
          
          {freeIllustrations.length > 8 && (
            <div className="text-center mt-8">
              <Link to="/galleria">
                <Button variant="outline" className="border-green-300 text-green-600 hover:bg-green-50">Vedi tutte le tavole gratuite</Button>
              </Link>
            </div>
          )}
        </div>
      </section>

      <section className="py-16 bg-gradient-to-b from-white to-pink-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-800 mb-4">Bundle & <span className="gradient-text">Pacchetti</span></h2>
            <p className="text-gray-600 max-w-xl mx-auto">Risparmia con i nostri pacchetti completi! PDF pronti per la stampa in formato A4.</p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {bundles.map((bundle, idx) => (
              <Card key={bundle.id} className={`border-2 hover-lift relative overflow-hidden ${
                idx === bundles.length - 1 ? 'border-pink-300 bg-gradient-to-b from-pink-50 to-white' : bundle.isFree ? 'border-green-200' : 'border-gray-200'
              }`}>
                {idx === bundles.length - 1 && <div className="absolute top-0 right-0 bg-pink-500 text-white text-xs font-bold px-3 py-1 rounded-bl-lg">BEST VALUE</div>}
                <CardHeader className="text-center pb-2">
                  <div className={`w-16 h-16 mx-auto rounded-2xl flex items-center justify-center mb-2 ${bundle.isFree ? 'bg-green-100' : 'bg-pink-100'}`}>
                    <Package className={`w-8 h-8 ${bundle.isFree ? 'text-green-500' : 'text-pink-500'}`} />
                  </div>
                  <CardTitle className="text-lg">{bundle.name}</CardTitle>
                </CardHeader>
                <CardContent className="text-center">
                  <p className="text-sm text-gray-600 mb-4 h-12">{bundle.description}</p>
                  <div className="mb-4"><span className="text-4xl font-bold text-gray-800">{bundle.isFree ? 'Gratis' : `€${bundle.price}`}</span></div>
                  <ul className="text-sm text-gray-600 mb-6 space-y-2">
                    <li className="flex items-center justify-center gap-2"><Check className="w-4 h-4 text-green-500" />{bundle.illustrationCount} illustrazioni</li>
                    <li className="flex items-center justify-center gap-2"><Check className="w-4 h-4 text-green-500" />Formato PDF A4</li>
                    <li className="flex items-center justify-center gap-2"><Check className="w-4 h-4 text-green-500" />Pronto per stampa</li>
                  </ul>
                  {!bundle.isFree && !siteSettings.stripe_enabled ? (
                    <div className="text-center p-3 bg-yellow-50 rounded-lg">
                      <AlertCircle className="w-4 h-4 text-yellow-500 mx-auto mb-1" />
                      <p className="text-xs text-yellow-700">Pagamenti non ancora attivi</p>
                    </div>
                  ) : (
                    <Button 
                      className={`w-full ${bundle.isFree ? 'bg-green-500 hover:bg-green-600' : 'bg-pink-500 hover:bg-pink-600'}`} 
                      onClick={() => handleBundleAction(bundle)}
                    >
                      <Download className="w-4 h-4 mr-2" />{bundle.isFree ? 'Scarica Gratis' : 'Acquista Ora'}
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-gradient-to-r from-blue-50 to-pink-50 rounded-2xl p-8 text-center">
            <h3 className="text-2xl font-bold text-gray-800 mb-4">Come funziona?</h3>
            <div className="grid sm:grid-cols-3 gap-6">
              <div>
                <div className="w-12 h-12 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-3"><span className="text-xl font-bold text-pink-500">1</span></div>
                <h4 className="font-semibold text-gray-800 mb-2">Scegli</h4>
                <p className="text-sm text-gray-600">Seleziona la tavola o il bundle che preferisci</p>
              </div>
              <div>
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3"><span className="text-xl font-bold text-blue-500">2</span></div>
                <h4 className="font-semibold text-gray-800 mb-2">Scarica</h4>
                <p className="text-sm text-gray-600">Ricevi il PDF direttamente sul tuo dispositivo</p>
              </div>
              <div>
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3"><span className="text-xl font-bold text-green-500">3</span></div>
                <h4 className="font-semibold text-gray-800 mb-2">Stampa e Colora!</h4>
                <p className="text-sm text-gray-600">Stampa in formato A4 e inizia a colorare</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default DownloadPage;
