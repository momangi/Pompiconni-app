import React, { useState, useEffect } from 'react';
import { Settings, Upload, Trash2, Image, Eye, CheckCircle, AlertCircle, RefreshCw, Save, Edit3 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Switch } from '../../components/ui/switch';
import { Label } from '../../components/ui/label';
import { getAdminSettings, updateAdminSettings, getHeroStatus, uploadHeroImage, deleteHeroImage, getAdminCharacterImages, uploadCharacterImage, deleteCharacterImage, updateCharacterText } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminSettings = () => {
  const [settings, setSettings] = useState(null);
  const [heroStatus, setHeroStatus] = useState({ hasHeroImage: false });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Character images state
  const [characterImages, setCharacterImages] = useState({});
  const [characterUploading, setCharacterUploading] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [settingsData, heroData, characterData] = await Promise.all([
        getAdminSettings(),
        getHeroStatus(),
        getAdminCharacterImages().catch(() => [])
      ]);
      setSettings(settingsData);
      setHeroStatus(heroData);
      // Convert array to object keyed by trait
      const charObj = {};
      characterData.forEach(item => {
        charObj[item.trait] = item;
      });
      setCharacterImages(charObj);
    } catch (error) {
      console.error('Error fetching settings:', error);
      toast.error('Errore nel caricamento delle impostazioni');
    } finally {
      setLoading(false);
    }
  };

  const handleSettingChange = async (key, value) => {
    setSaving(true);
    try {
      await updateAdminSettings({ [key]: value });
      setSettings(prev => ({ ...prev, [key]: value }));
      toast.success('Impostazione aggiornata');
    } catch (error) {
      toast.error('Errore nel salvataggio');
    } finally {
      setSaving(false);
    }
  };

  const handleHeroUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(file.type)) {
      toast.error('Solo file JPG, JPEG o PNG sono permessi');
      return;
    }

    setUploading(true);
    try {
      await uploadHeroImage(file);
      toast.success('Hero image aggiornata con successo!');
      // Refresh hero status
      const heroData = await getHeroStatus();
      setHeroStatus(heroData);
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Errore durante il caricamento');
    } finally {
      setUploading(false);
    }
  };

  const handleHeroDelete = async () => {
    if (!window.confirm('Sei sicuro di voler rimuovere la hero image? Verrà ripristinato il default.')) {
      return;
    }

    try {
      await deleteHeroImage();
      toast.success('Hero image rimossa, ripristinato default');
      setHeroStatus({ hasHeroImage: false });
    } catch (error) {
      toast.error('Errore durante la rimozione');
    }
  };

  // Character Image Handlers
  const handleCharacterUpload = async (trait, e) => {
    const file = e.target.files[0];
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!validTypes.includes(file.type)) {
      toast.error('Solo file JPG, JPEG o PNG sono permessi');
      return;
    }

    setCharacterUploading(prev => ({ ...prev, [trait]: true }));
    try {
      const result = await uploadCharacterImage(trait, file);
      toast.success(`Immagine "${trait}" caricata con successo!`);
      setCharacterImages(prev => ({
        ...prev,
        [trait]: { trait, imageUrl: result.imageUrl, fileId: result.fileId }
      }));
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Errore durante il caricamento');
    } finally {
      setCharacterUploading(prev => ({ ...prev, [trait]: false }));
    }
  };

  const handleCharacterDelete = async (trait) => {
    if (!window.confirm(`Sei sicuro di voler rimuovere l'immagine "${trait}"?`)) {
      return;
    }

    try {
      await deleteCharacterImage(trait);
      toast.success(`Immagine "${trait}" rimossa`);
      setCharacterImages(prev => {
        const newState = { ...prev };
        delete newState[trait];
        return newState;
      });
    } catch (error) {
      toast.error('Errore durante la rimozione');
    }
  };

  const characterTraits = [
    { key: 'dolce', label: 'Dolce', color: 'pink', emoji: '💖' },
    { key: 'simpatico', label: 'Simpatico', color: 'blue', emoji: '✨' },
    { key: 'impacciato', label: 'Impacciato', color: 'yellow', emoji: '⭐' }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-4 border-pink-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
          <Settings className="w-8 h-8 text-pink-500" />
          Impostazioni Sito
        </h1>
        <p className="text-gray-600 mt-1">Gestisci le impostazioni generali del sito</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Hero Image Section */}
        <Card className="border-2 border-pink-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Image className="w-5 h-5 text-pink-500" />
              Hero Image (Home)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600">
              L&apos;immagine principale mostrata nella sezione hero della homepage.
            </p>

            {/* Preview */}
            <div className="relative h-48 bg-gradient-to-br from-pink-100 to-blue-100 rounded-xl flex items-center justify-center overflow-hidden">
              {heroStatus.hasHeroImage ? (
                <img
                  src={`${BACKEND_URL}/api/site/hero-image?t=${Date.now()}`}
                  alt="Hero"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-center">
                  <div className="text-6xl mb-2">🦄</div>
                  <p className="text-sm text-gray-500">Default (emoji)</p>
                </div>
              )}
              {heroStatus.hasHeroImage && (
                <div className="absolute top-2 right-2">
                  <CheckCircle className="w-6 h-6 text-green-500 bg-white rounded-full" />
                </div>
              )}
            </div>

            {/* Upload Section */}
            <div className="flex gap-3">
              <input
                type="file"
                accept=".jpg,.jpeg,.png"
                onChange={handleHeroUpload}
                className="hidden"
                id="hero-upload"
                disabled={uploading}
              />
              <label
                htmlFor="hero-upload"
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg cursor-pointer transition-colors ${
                  uploading
                    ? 'bg-gray-100 text-gray-400'
                    : 'bg-pink-50 text-pink-600 hover:bg-pink-100'
                }`}
              >
                {uploading ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-pink-500 border-t-transparent rounded-full" />
                    Caricamento...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    {heroStatus.hasHeroImage ? 'Sostituisci' : 'Carica Immagine'}
                  </>
                )}
              </label>

              {heroStatus.hasHeroImage && (
                <Button
                  variant="outline"
                  className="border-red-200 text-red-500 hover:bg-red-50"
                  onClick={handleHeroDelete}
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Rimuovi
                </Button>
              )}
            </div>

            <p className="text-xs text-gray-400">
              Formati supportati: JPG, JPEG, PNG. Dimensione consigliata: 800x800px
            </p>
          </CardContent>
        </Card>

        {/* General Settings */}
        <Card className="border-2 border-blue-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-blue-500" />
              Impostazioni Generali
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Show Reviews Toggle */}
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base">Mostra Recensioni</Label>
                <p className="text-sm text-gray-500">
                  Abilita/disabilita la sezione recensioni sulla homepage
                </p>
              </div>
              <Switch
                checked={settings?.show_reviews ?? true}
                onCheckedChange={(checked) => handleSettingChange('show_reviews', checked)}
                disabled={saving}
              />
            </div>

            {/* Stripe Status (read-only) */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <Label className="text-base">Pagamenti Stripe</Label>
                <p className="text-sm text-gray-500">
                  {settings?.stripe_configured
                    ? 'Chiavi Stripe configurate'
                    : 'Chiavi Stripe non configurate'}
                </p>
              </div>
              {settings?.stripe_configured ? (
                <CheckCircle className="w-6 h-6 text-green-500" />
              ) : (
                <AlertCircle className="w-6 h-6 text-yellow-500" />
              )}
            </div>

            {!settings?.stripe_configured && (
              <div className="p-4 bg-yellow-50 rounded-lg text-sm text-yellow-700">
                <p className="font-medium mb-1">Pagamenti non attivi</p>
                <p>Per abilitare i pagamenti, aggiungi le seguenti variabili al file .env:</p>
                <code className="block mt-2 p-2 bg-yellow-100 rounded text-xs">
                  STRIPE_SECRET_KEY=sk_test_xxx<br />
                  STRIPE_PUBLISHABLE_KEY=pk_test_xxx
                </code>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Character Images Section */}
        <Card className="lg:col-span-2 border-2 border-purple-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Image className="w-5 h-5 text-purple-500" />
              Immagini Caratteristiche (Chi è Poppiconni?)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600">
              Gestisci le immagini per le tre caratteristiche di Poppiconni mostrate nella homepage.
            </p>

            <div className="grid md:grid-cols-3 gap-6">
              {characterTraits.map(({ key, label, color, emoji }) => (
                <div key={key} className="space-y-3">
                  <h4 className="font-medium text-gray-700 flex items-center gap-2">
                    <span>{emoji}</span> {label}
                  </h4>
                  
                  {/* Preview */}
                  <div className={`relative h-40 bg-gradient-to-br from-${color}-100 to-${color}-200 rounded-xl flex items-center justify-center overflow-hidden`}>
                    {characterImages[key]?.imageUrl ? (
                      <img
                        src={`${BACKEND_URL}${characterImages[key].imageUrl}?t=${Date.now()}`}
                        alt={label}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="text-center text-gray-400">
                        <div className="text-4xl mb-1">{emoji}</div>
                        <p className="text-xs">Nessuna immagine</p>
                      </div>
                    )}
                    {characterImages[key]?.imageUrl && (
                      <div className="absolute top-2 right-2">
                        <CheckCircle className="w-5 h-5 text-green-500 bg-white rounded-full" />
                      </div>
                    )}
                  </div>

                  {/* Upload/Delete Buttons */}
                  <div className="flex gap-2">
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png"
                      onChange={(e) => handleCharacterUpload(key, e)}
                      className="hidden"
                      id={`character-upload-${key}`}
                      disabled={characterUploading[key]}
                    />
                    <label
                      htmlFor={`character-upload-${key}`}
                      className={`flex-1 flex items-center justify-center gap-1 px-3 py-2 text-sm rounded-lg cursor-pointer transition-colors ${
                        characterUploading[key]
                          ? 'bg-gray-100 text-gray-400'
                          : `bg-${color}-50 text-${color}-600 hover:bg-${color}-100`
                      }`}
                    >
                      {characterUploading[key] ? (
                        <>
                          <RefreshCw className="w-3 h-3 animate-spin" />
                          <span>...</span>
                        </>
                      ) : (
                        <>
                          <Upload className="w-3 h-3" />
                          <span>{characterImages[key]?.imageUrl ? 'Cambia' : 'Carica'}</span>
                        </>
                      )}
                    </label>

                    {characterImages[key]?.imageUrl && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="border-red-200 text-red-500 hover:bg-red-50 px-2"
                        onClick={() => handleCharacterDelete(key)}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <p className="text-xs text-gray-400 mt-4">
              Formati supportati: JPG, JPEG, PNG. Le immagini verranno mostrate nelle card della sezione &quot;Chi è Poppiconni?&quot; sulla homepage.
            </p>
          </CardContent>
        </Card>

        {/* Preview Link */}
        <Card className="lg:col-span-2 border-2 border-green-100">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-800">Anteprima Sito</h3>
                <p className="text-sm text-gray-500">Visualizza le modifiche sul sito pubblico</p>
              </div>
              <Button
                variant="outline"
                className="border-green-200 text-green-600 hover:bg-green-50"
                onClick={() => window.open('/', '_blank')}
              >
                <Eye className="w-4 h-4 mr-2" />
                Apri Homepage
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AdminSettings;
