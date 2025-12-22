import React, { useState, useEffect } from 'react';
import { Settings, Upload, Trash2, Image, Eye, CheckCircle, AlertCircle, RefreshCw, Save, Edit3, Instagram, Music2, Mail, MapPin, Building2, FileText } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Switch } from '../../components/ui/switch';
import { Label } from '../../components/ui/label';
import { Input } from '../../components/ui/input';
import { Checkbox } from '../../components/ui/checkbox';
import { getAdminSettings, updateAdminSettings, getHeroStatus, uploadHeroImage, deleteHeroImage, getAdminCharacterImages, uploadCharacterImage, deleteCharacterImage, updateCharacterText, getBrandLogoStatus, uploadBrandLogo, deleteBrandLogo, updateSocialLinks } from '../../services/api';
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
  const [characterTexts, setCharacterTexts] = useState({});
  const [characterSaving, setCharacterSaving] = useState({});
  const [editingTrait, setEditingTrait] = useState(null);
  
  // Brand logo state
  const [brandLogoStatus, setBrandLogoStatus] = useState({ hasBrandLogo: false });
  const [brandLogoUploading, setBrandLogoUploading] = useState(false);
  
  // Social links state
  const [socialLinks, setSocialLinks] = useState({ instagramUrl: '', tiktokUrl: '' });
  const [socialSaving, setSocialSaving] = useState(false);

  // Legal contact info state
  const [legalInfo, setLegalInfo] = useState({
    legal_company_name: '',
    show_legal_company_name: true,
    legal_address: '',
    show_legal_address: true,
    legal_vat_number: '',
    show_legal_vat_number: true,
    legal_email: '',
    show_legal_email: true,
    legal_pec_email: '',
    show_legal_pec_email: true
  });
  const [legalSaving, setLegalSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [settingsData, heroData, characterData, brandLogoData] = await Promise.all([
        getAdminSettings(),
        getHeroStatus(),
        getAdminCharacterImages().catch(() => []),
        getBrandLogoStatus().catch(() => ({ hasBrandLogo: false }))
      ]);
      setSettings(settingsData);
      setHeroStatus(heroData);
      setBrandLogoStatus(brandLogoData);
      setSocialLinks({
        instagramUrl: settingsData?.instagramUrl || '',
        tiktokUrl: settingsData?.tiktokUrl || ''
      });
      // Load legal info from settings
      setLegalInfo({
        legal_company_name: settingsData?.legal_company_name || '',
        show_legal_company_name: settingsData?.show_legal_company_name ?? true,
        legal_address: settingsData?.legal_address || '',
        show_legal_address: settingsData?.show_legal_address ?? true,
        legal_vat_number: settingsData?.legal_vat_number || '',
        show_legal_vat_number: settingsData?.show_legal_vat_number ?? true,
        legal_email: settingsData?.legal_email || '',
        show_legal_email: settingsData?.show_legal_email ?? true,
        legal_pec_email: settingsData?.legal_pec_email || '',
        show_legal_pec_email: settingsData?.show_legal_pec_email ?? true
      });
      // Convert array to object keyed by trait
      const charObj = {};
      const textsObj = {
        dolce: { title: '', shortDescription: '', longDescription: '' },
        simpatico: { title: '', shortDescription: '', longDescription: '' },
        impacciato: { title: '', shortDescription: '', longDescription: '' }
      };
      characterData.forEach(item => {
        charObj[item.trait] = item;
        textsObj[item.trait] = {
          title: item.title || '',
          shortDescription: item.shortDescription || '',
          longDescription: item.longDescription || ''
        };
      });
      setCharacterImages(charObj);
      setCharacterTexts(textsObj);
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
    { key: 'dolce', label: 'Dolce', color: 'pink', emoji: '💖', defaultShort: 'Con i suoi occhi grandi e le guanciotte rosate, Poppiconni conquista tutti con la sua dolcezza', defaultLong: 'Con i suoi occhi grandi e le guanciotte rosate, Poppiconni conquista tutti con la sua dolcezza. Il suo sguardo tenero e il suo sorriso gentile scaldano il cuore di grandi e piccini.' },
    { key: 'simpatico', label: 'Simpatico', color: 'blue', emoji: '✨', defaultShort: 'Sempre pronto a far sorridere con le sue espressioni buffe e le sue avventure divertenti', defaultLong: 'Sempre pronto a far sorridere con le sue espressioni buffe e le sue avventure divertenti. Poppiconni sa come trasformare ogni momento in un\'occasione per ridere insieme.' },
    { key: 'impacciato', label: 'Impacciato', color: 'yellow', emoji: '⭐', defaultShort: 'Un po\' goffo ma adorabile, si caccia sempre in situazioni comiche ma trova sempre la soluzione', defaultLong: 'Un po\' goffo ma adorabile, si caccia sempre in situazioni comiche ma trova sempre la soluzione. Le sue disavventure insegnano che dagli errori si impara e che non bisogna mai arrendersi.' }
  ];

  // Brand Logo Handlers
  const handleBrandLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      toast.error('Solo file JPG, PNG o WEBP sono permessi');
      return;
    }

    setBrandLogoUploading(true);
    try {
      const result = await uploadBrandLogo(file);
      toast.success('Logo caricato con successo!');
      setBrandLogoStatus({ hasBrandLogo: true, brandLogoUrl: result.brandLogoUrl });
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Errore durante il caricamento');
    } finally {
      setBrandLogoUploading(false);
    }
  };

  const handleBrandLogoDelete = async () => {
    if (!window.confirm('Sei sicuro di voler rimuovere il logo?')) return;

    try {
      await deleteBrandLogo();
      toast.success('Logo rimosso');
      setBrandLogoStatus({ hasBrandLogo: false, brandLogoUrl: null });
    } catch (error) {
      toast.error('Errore durante la rimozione');
    }
  };

  // Social Links Handler
  const handleSocialLinksSave = async () => {
    setSocialSaving(true);
    try {
      await updateSocialLinks(socialLinks.instagramUrl, socialLinks.tiktokUrl);
      toast.success('Link social salvati!');
    } catch (error) {
      toast.error('Errore durante il salvataggio');
    } finally {
      setSocialSaving(false);
    }
  };

  // Legal Info Handler
  const handleLegalInfoSave = async () => {
    setLegalSaving(true);
    try {
      await updateAdminSettings(legalInfo);
      toast.success('Informazioni legali salvate!');
    } catch (error) {
      toast.error('Errore durante il salvataggio');
    } finally {
      setLegalSaving(false);
    }
  };

  const handleTextChange = (trait, field, value) => {
    setCharacterTexts(prev => ({
      ...prev,
      [trait]: {
        title: prev[trait]?.title || '',
        shortDescription: prev[trait]?.shortDescription || '',
        longDescription: prev[trait]?.longDescription || '',
        [field]: value
      }
    }));
  };

  const handleSaveText = async (trait) => {
    const textData = characterTexts[trait] || { title: '', shortDescription: '', longDescription: '' };
    
    setCharacterSaving(prev => ({ ...prev, [trait]: true }));
    try {
      await updateCharacterText(trait, textData);
      toast.success(`Testi "${trait}" salvati con successo!`);
      setEditingTrait(null);
    } catch (error) {
      console.error('Save error:', error);
      toast.error('Errore durante il salvataggio');
    } finally {
      setCharacterSaving(prev => ({ ...prev, [trait]: false }));
    }
  };

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

        {/* Brand Logo */}
        <Card className="border-2 border-purple-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Image className="w-5 h-5 text-purple-500" />
              Logo Poppiconni
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600">
              Logo/avatar mostrato nell&apos;header e footer del sito.
            </p>

            {/* Preview */}
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-pink-200 to-blue-200 flex items-center justify-center overflow-hidden">
                {brandLogoStatus.hasBrandLogo ? (
                  <img
                    src={`${BACKEND_URL}/api/site/brand-logo?t=${Date.now()}`}
                    alt="Brand Logo"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-gray-400 text-xs text-center">Nessun logo</span>
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-600 mb-2">
                  {brandLogoStatus.hasBrandLogo ? 'Logo configurato' : 'Nessun logo caricato'}
                </p>
                <div className="flex gap-2">
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp"
                    onChange={handleBrandLogoUpload}
                    className="hidden"
                    id="brand-logo-upload"
                    disabled={brandLogoUploading}
                  />
                  <label
                    htmlFor="brand-logo-upload"
                    className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg cursor-pointer transition-colors ${
                      brandLogoUploading
                        ? 'bg-gray-100 text-gray-400'
                        : 'bg-purple-50 text-purple-600 hover:bg-purple-100'
                    }`}
                  >
                    {brandLogoUploading ? (
                      <RefreshCw className="w-3 h-3 animate-spin" />
                    ) : (
                      <Upload className="w-3 h-3" />
                    )}
                    {brandLogoStatus.hasBrandLogo ? 'Cambia' : 'Carica'}
                  </label>
                  {brandLogoStatus.hasBrandLogo && (
                    <button
                      onClick={handleBrandLogoDelete}
                      className="px-3 py-1.5 text-sm text-red-500 hover:bg-red-50 rounded-lg"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-400">
              Dimensione consigliata: 200x200px. Sarà mostrato 32px su desktop, 28px su mobile.
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

            {/* Show Bundles Toggle */}
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base">Mostra Sezione Bundle</Label>
                <p className="text-sm text-gray-500">
                  Abilita/disabilita la sezione &quot;Download &amp; Bundle&quot; sulla homepage
                </p>
              </div>
              <Switch
                checked={settings?.showBundlesSection ?? true}
                onCheckedChange={(checked) => handleSettingChange('showBundlesSection', checked)}
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

            {/* Social Links */}
            <div className="pt-4 border-t border-gray-200">
              <Label className="text-base mb-3 block">Link Social</Label>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Instagram className="w-5 h-5 text-pink-500" />
                  <input
                    type="url"
                    value={socialLinks.instagramUrl}
                    onChange={(e) => setSocialLinks(prev => ({ ...prev, instagramUrl: e.target.value }))}
                    placeholder="https://instagram.com/poppiconni"
                    className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <Music2 className="w-5 h-5 text-gray-800" />
                  <input
                    type="url"
                    value={socialLinks.tiktokUrl}
                    onChange={(e) => setSocialLinks(prev => ({ ...prev, tiktokUrl: e.target.value }))}
                    placeholder="https://tiktok.com/@poppiconni"
                    className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200"
                  />
                </div>
                <Button
                  size="sm"
                  onClick={handleSocialLinksSave}
                  disabled={socialSaving}
                  className="bg-blue-500 hover:bg-blue-600"
                >
                  {socialSaving ? (
                    <>
                      <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                      Salvataggio...
                    </>
                  ) : (
                    <>
                      <Save className="w-3 h-3 mr-1" />
                      Salva Link Social
                    </>
                  )}
                </Button>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                I link appariranno nel footer. Lascia vuoto per nascondere l&apos;icona.
              </p>
            </div>
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
              Gestisci le immagini e i testi per le tre caratteristiche di Poppiconni mostrate nella homepage.
            </p>

            <div className="grid md:grid-cols-3 gap-6">
              {characterTraits.map(({ key, label, color, emoji, defaultShort, defaultLong }) => (
                <div key={key} className="space-y-3 p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-gray-700 flex items-center gap-2">
                      <span>{emoji}</span> {label}
                    </h4>
                    <button
                      onClick={() => setEditingTrait(editingTrait === key ? null : key)}
                      className={`p-1.5 rounded-lg transition-colors ${editingTrait === key ? 'bg-purple-100 text-purple-600' : 'hover:bg-gray-200 text-gray-500'}`}
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  {/* Preview */}
                  <div className={`relative h-32 bg-gradient-to-br from-${color}-100 to-${color}-200 rounded-xl flex items-center justify-center overflow-hidden`}>
                    {characterImages[key]?.imageUrl ? (
                      <img
                        src={`${BACKEND_URL}${characterImages[key].imageUrl}?t=${Date.now()}`}
                        alt={label}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="text-center text-gray-400">
                        <div className="text-3xl mb-1">{emoji}</div>
                        <p className="text-xs">Nessuna immagine</p>
                      </div>
                    )}
                    {characterImages[key]?.imageUrl && (
                      <div className="absolute top-2 right-2">
                        <CheckCircle className="w-4 h-4 text-green-500 bg-white rounded-full" />
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

                  {/* Text Fields - Collapsible */}
                  {editingTrait === key && (
                    <div className="space-y-3 pt-3 border-t border-gray-200">
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Titolo</label>
                        <input
                          type="text"
                          value={characterTexts[key]?.title || ''}
                          onChange={(e) => handleTextChange(key, 'title', e.target.value)}
                          placeholder={label}
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-200"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Descrizione breve (card)</label>
                        <textarea
                          value={characterTexts[key]?.shortDescription || ''}
                          onChange={(e) => handleTextChange(key, 'shortDescription', e.target.value)}
                          placeholder={defaultShort}
                          rows={2}
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-200 resize-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">Descrizione estesa (modale)</label>
                        <textarea
                          value={characterTexts[key]?.longDescription || ''}
                          onChange={(e) => handleTextChange(key, 'longDescription', e.target.value)}
                          placeholder={defaultLong}
                          rows={3}
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-200 resize-none"
                        />
                      </div>
                      <Button
                        size="sm"
                        className="w-full bg-purple-500 hover:bg-purple-600"
                        onClick={() => handleSaveText(key)}
                        disabled={characterSaving[key]}
                      >
                        {characterSaving[key] ? (
                          <>
                            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                            Salvataggio...
                          </>
                        ) : (
                          <>
                            <Save className="w-3 h-3 mr-1" />
                            Salva Testi
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <p className="text-xs text-gray-400 mt-4">
              Formati supportati: JPG, JPEG, PNG. Clicca l&apos;icona ✏️ per modificare i testi di ogni caratteristica.
            </p>
          </CardContent>
        </Card>

        {/* Legal Contact Info Section */}
        <Card className="lg:col-span-2 border-2 border-indigo-100">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-indigo-500" />
              Informazioni Legali (Contatti)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-gray-600">
              Gestisci le informazioni di contatto legali mostrate nella pagina &quot;Contatti Legali&quot;. 
              Usa i checkbox per scegliere quali campi mostrare pubblicamente.
            </p>

            <div className="grid md:grid-cols-2 gap-4">
              {/* Company Name */}
              <div className="space-y-2 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-gray-500" />
                    Nome Azienda / Titolare
                  </Label>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="show_company"
                      checked={legalInfo.show_legal_company_name}
                      onCheckedChange={(checked) => setLegalInfo(prev => ({ ...prev, show_legal_company_name: checked }))}
                    />
                    <label htmlFor="show_company" className="text-xs text-gray-500">Mostra</label>
                  </div>
                </div>
                <Input
                  value={legalInfo.legal_company_name}
                  onChange={(e) => setLegalInfo(prev => ({ ...prev, legal_company_name: e.target.value }))}
                  placeholder="es. Matteo Calipa – Poppiconni Project"
                />
              </div>

              {/* Address */}
              <div className="space-y-2 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-gray-500" />
                    Indirizzo
                  </Label>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="show_address"
                      checked={legalInfo.show_legal_address}
                      onCheckedChange={(checked) => setLegalInfo(prev => ({ ...prev, show_legal_address: checked }))}
                    />
                    <label htmlFor="show_address" className="text-xs text-gray-500">Mostra</label>
                  </div>
                </div>
                <Input
                  value={legalInfo.legal_address}
                  onChange={(e) => setLegalInfo(prev => ({ ...prev, legal_address: e.target.value }))}
                  placeholder="es. Ventimiglia (IM), Italia"
                />
              </div>

              {/* VAT Number */}
              <div className="space-y-2 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-gray-500" />
                    Partita IVA
                  </Label>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="show_vat"
                      checked={legalInfo.show_legal_vat_number}
                      onCheckedChange={(checked) => setLegalInfo(prev => ({ ...prev, show_legal_vat_number: checked }))}
                    />
                    <label htmlFor="show_vat" className="text-xs text-gray-500">Mostra</label>
                  </div>
                </div>
                <Input
                  value={legalInfo.legal_vat_number}
                  onChange={(e) => setLegalInfo(prev => ({ ...prev, legal_vat_number: e.target.value }))}
                  placeholder="es. IT12345678901"
                />
              </div>

              {/* Email */}
              <div className="space-y-2 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-gray-500" />
                    Email
                  </Label>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="show_email"
                      checked={legalInfo.show_legal_email}
                      onCheckedChange={(checked) => setLegalInfo(prev => ({ ...prev, show_legal_email: checked }))}
                    />
                    <label htmlFor="show_email" className="text-xs text-gray-500">Mostra</label>
                  </div>
                </div>
                <Input
                  type="email"
                  value={legalInfo.legal_email}
                  onChange={(e) => setLegalInfo(prev => ({ ...prev, legal_email: e.target.value }))}
                  placeholder="es. info@poppiconni.it"
                />
              </div>

              {/* PEC Email */}
              <div className="space-y-2 p-4 bg-gray-50 rounded-lg md:col-span-2">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-gray-500" />
                    PEC (Posta Elettronica Certificata)
                  </Label>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="show_pec"
                      checked={legalInfo.show_legal_pec_email}
                      onCheckedChange={(checked) => setLegalInfo(prev => ({ ...prev, show_legal_pec_email: checked }))}
                    />
                    <label htmlFor="show_pec" className="text-xs text-gray-500">Mostra</label>
                  </div>
                </div>
                <Input
                  type="email"
                  value={legalInfo.legal_pec_email}
                  onChange={(e) => setLegalInfo(prev => ({ ...prev, legal_pec_email: e.target.value }))}
                  placeholder="es. poppiconni@pec.it"
                />
              </div>
            </div>

            <Button
              onClick={handleLegalInfoSave}
              disabled={legalSaving}
              className="bg-indigo-500 hover:bg-indigo-600"
            >
              {legalSaving ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Salvataggio...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Salva Informazioni Legali
                </>
              )}
            </Button>

            <p className="text-xs text-gray-400">
              I campi verranno mostrati nella pagina &quot;Contatti Legali&quot; solo se hanno un valore e il checkbox &quot;Mostra&quot; è attivo.
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
