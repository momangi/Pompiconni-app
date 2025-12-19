import React, { useState, useEffect } from 'react';
import { Package, Plus, Edit2, Trash2, Upload, Image, GripVertical, Eye, EyeOff, Save, X, Check } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Switch } from '../../components/ui/switch';
import { Label } from '../../components/ui/label';
import { getAdminBundles, createBundle, updateBundle, deleteBundle, uploadBundleBackground, getIllustrations } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminBundles = () => {
  const [bundles, setBundles] = useState([]);
  const [illustrations, setIllustrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingBundle, setEditingBundle] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [saving, setSaving] = useState(false);

  const emptyBundle = {
    title: '',
    subtitle: '',
    price: 0,
    currency: 'EUR',
    isFree: true,
    badgeText: '',
    isActive: true,
    sortOrder: 0,
    illustrationIds: []
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [bundlesData, illustrationsData] = await Promise.all([
        getAdminBundles(),
        getIllustrations()
      ]);
      setBundles(bundlesData);
      setIllustrations(illustrationsData);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Errore nel caricamento dei bundle');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    const maxOrder = bundles.length > 0 ? Math.max(...bundles.map(b => b.sortOrder || 0)) : 0;
    setEditingBundle({ ...emptyBundle, sortOrder: maxOrder + 1 });
    setIsCreating(true);
  };

  const handleEdit = (bundle) => {
    setEditingBundle({ ...bundle });
    setIsCreating(false);
  };

  const handleCancel = () => {
    setEditingBundle(null);
    setIsCreating(false);
  };

  const handleSave = async () => {
    if (!editingBundle.title.trim()) {
      toast.error('Il titolo è obbligatorio');
      return;
    }

    setSaving(true);
    try {
      if (isCreating) {
        const newBundle = await createBundle(editingBundle);
        setBundles(prev => [...prev, newBundle].sort((a, b) => a.sortOrder - b.sortOrder));
        toast.success('Bundle creato con successo!');
      } else {
        const updated = await updateBundle(editingBundle.id, editingBundle);
        setBundles(prev => prev.map(b => b.id === editingBundle.id ? updated : b).sort((a, b) => a.sortOrder - b.sortOrder));
        toast.success('Bundle aggiornato!');
      }
      setEditingBundle(null);
      setIsCreating(false);
    } catch (error) {
      console.error('Save error:', error);
      toast.error('Errore durante il salvataggio');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (bundleId) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo bundle?')) return;

    try {
      await deleteBundle(bundleId);
      setBundles(prev => prev.filter(b => b.id !== bundleId));
      toast.success('Bundle eliminato');
    } catch (error) {
      toast.error('Errore durante l\'eliminazione');
    }
  };

  const handleBackgroundUpload = async (bundleId, e) => {
    const file = e.target.files[0];
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      toast.error('Solo file JPG, PNG o WEBP');
      return;
    }

    try {
      const result = await uploadBundleBackground(bundleId, file);
      setBundles(prev => prev.map(b => 
        b.id === bundleId ? { ...b, backgroundImageUrl: result.backgroundImageUrl } : b
      ));
      if (editingBundle?.id === bundleId) {
        setEditingBundle(prev => ({ ...prev, backgroundImageUrl: result.backgroundImageUrl }));
      }
      toast.success('Immagine sfondo caricata!');
    } catch (error) {
      toast.error('Errore durante il caricamento immagine');
    }
  };

  const handleToggleActive = async (bundle) => {
    try {
      const updated = await updateBundle(bundle.id, { isActive: !bundle.isActive });
      setBundles(prev => prev.map(b => b.id === bundle.id ? updated : b));
      toast.success(updated.isActive ? 'Bundle attivato' : 'Bundle disattivato');
    } catch (error) {
      toast.error('Errore durante l\'aggiornamento');
    }
  };

  const handleIllustrationToggle = (illustId) => {
    if (!editingBundle) return;
    const ids = editingBundle.illustrationIds || [];
    const newIds = ids.includes(illustId) 
      ? ids.filter(id => id !== illustId)
      : [...ids, illustId];
    setEditingBundle(prev => ({ ...prev, illustrationIds: newIds }));
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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
            <Package className="w-8 h-8 text-pink-500" />
            Gestione Bundle
          </h1>
          <p className="text-gray-600 mt-1">Crea e gestisci i bundle per la sezione Download</p>
        </div>
        <Button onClick={handleCreate} className="bg-pink-500 hover:bg-pink-600">
          <Plus className="w-4 h-4 mr-2" />
          Nuovo Bundle
        </Button>
      </div>

      {/* Edit/Create Form */}
      {editingBundle && (
        <Card className="mb-8 border-2 border-pink-200">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{isCreating ? 'Nuovo Bundle' : 'Modifica Bundle'}</span>
              <Button variant="ghost" size="sm" onClick={handleCancel}>
                <X className="w-4 h-4" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Left Column - Details */}
              <div className="space-y-4">
                <div>
                  <Label>Titolo *</Label>
                  <input
                    type="text"
                    value={editingBundle.title}
                    onChange={(e) => setEditingBundle(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-200"
                    placeholder="es. Starter Pack Poppiconni"
                  />
                </div>

                <div>
                  <Label>Sottotitolo</Label>
                  <input
                    type="text"
                    value={editingBundle.subtitle}
                    onChange={(e) => setEditingBundle(prev => ({ ...prev, subtitle: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-200"
                    placeholder="es. 10 tavole gratuite per iniziare!"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Prezzo (€)</Label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={editingBundle.price}
                      onChange={(e) => setEditingBundle(prev => ({ ...prev, price: parseFloat(e.target.value) || 0 }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-200"
                      disabled={editingBundle.isFree}
                    />
                  </div>
                  <div>
                    <Label>Ordine</Label>
                    <input
                      type="number"
                      min="0"
                      value={editingBundle.sortOrder}
                      onChange={(e) => setEditingBundle(prev => ({ ...prev, sortOrder: parseInt(e.target.value) || 0 }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-200"
                    />
                  </div>
                </div>

                <div>
                  <Label>Badge (testo)</Label>
                  <input
                    type="text"
                    value={editingBundle.badgeText}
                    onChange={(e) => setEditingBundle(prev => ({ ...prev, badgeText: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-pink-200"
                    placeholder="es. GRATIS, NUOVO, PROMO"
                  />
                </div>

                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={editingBundle.isFree}
                      onCheckedChange={(checked) => setEditingBundle(prev => ({ 
                        ...prev, 
                        isFree: checked,
                        price: checked ? 0 : prev.price,
                        badgeText: checked && !prev.badgeText ? 'GRATIS' : prev.badgeText
                      }))}
                    />
                    <Label>Gratuito</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={editingBundle.isActive}
                      onCheckedChange={(checked) => setEditingBundle(prev => ({ ...prev, isActive: checked }))}
                    />
                    <Label>Attivo</Label>
                  </div>
                </div>
              </div>

              {/* Right Column - Files */}
              <div className="space-y-4">
                {/* Background Image + Opacity with Live Preview */}
                <div>
                  <Label>Immagine Sfondo + Opacità</Label>
                  {/* Live Preview Container - stessa logica della homepage */}
                  <div className="mt-2 h-40 rounded-lg overflow-hidden relative bg-gray-100">
                    {/* Background image with live opacity */}
                    {editingBundle.backgroundImageUrl ? (
                      <>
                        {/* Layer immagine - sempre opacity 1, blur proporzionale */}
                        <img 
                          src={`${BACKEND_URL}${editingBundle.backgroundImageUrl}?t=${Date.now()}`}
                          alt=""
                          className="absolute inset-0 w-full h-full object-cover"
                          style={{ 
                            filter: `blur(${((editingBundle.backgroundOpacity || 0) / 80) * 8}px)`,
                            transform: 'scale(1.1)',
                            opacity: 1
                          }}
                        />
                        {/* Layer velo - opacità controllata dallo slider */}
                        <div 
                          className="absolute inset-0" 
                          style={{ 
                            backgroundColor: 'rgba(255, 250, 245, 1)', 
                            opacity: (editingBundle.backgroundOpacity || 0) / 100 
                          }} 
                        />
                        {/* Sample content preview */}
                        <div className="absolute inset-0 flex flex-col items-center justify-center z-10 text-center p-4">
                          <span className="text-xs bg-pink-100 text-pink-600 px-2 py-0.5 rounded-full mb-1">PREVIEW</span>
                          <span className="font-bold text-gray-800 text-sm">{editingBundle.title || 'Titolo Bundle'}</span>
                          <span className="text-xs text-gray-600">{editingBundle.subtitle || 'Sottotitolo'}</span>
                        </div>
                      </>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400 bg-gray-100">
                        <div className="text-center">
                          <Image className="w-8 h-8 mx-auto mb-1" />
                          <span className="text-xs">Carica un&apos;immagine</span>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Upload button */}
                  {!isCreating && (
                    <div className="mt-2">
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png,.webp"
                        onChange={(e) => handleBackgroundUpload(editingBundle.id, e)}
                        className="hidden"
                        id="bg-upload"
                      />
                      <label
                        htmlFor="bg-upload"
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg cursor-pointer"
                      >
                        <Upload className="w-3 h-3" />
                        {editingBundle.backgroundImageUrl ? 'Cambia immagine' : 'Carica immagine'}
                      </label>
                    </div>
                  )}

                  {/* Opacity Slider - ora controlla il velo, non l'immagine */}
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-gray-600">Velatura sfondo</span>
                      <span className="text-sm font-bold text-pink-500">
                        {editingBundle.backgroundOpacity || 0}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="80"
                      value={editingBundle.backgroundOpacity || 0}
                      onChange={(e) => setEditingBundle(prev => ({ ...prev, backgroundOpacity: parseInt(e.target.value) }))}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-pink-500"
                    />
                    <div className="flex justify-between text-xs text-gray-400 mt-1">
                      <span>0% (nitida)</span>
                      <span>80% (velata)</span>
                    </div>
                  </div>
                </div>

                {/* Illustrations Count */}
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">
                    <strong>Illustrazioni incluse:</strong> {(editingBundle.illustrationIds || []).length}
                  </p>
                  <p className="text-xs text-blue-500 mt-1">
                    Il conteggio si aggiorna automaticamente
                  </p>
                </div>
              </div>
            </div>

            {/* Illustrations Selection */}
            {!isCreating && illustrations.length > 0 && (
              <div>
                <Label className="mb-2 block">Seleziona Illustrazioni</Label>
                <div className="max-h-48 overflow-y-auto border border-gray-200 rounded-lg p-2">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {illustrations.map(illust => (
                      <label
                        key={illust.id}
                        className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors ${
                          (editingBundle.illustrationIds || []).includes(illust.id)
                            ? 'bg-pink-100 border border-pink-300'
                            : 'bg-gray-50 hover:bg-gray-100'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={(editingBundle.illustrationIds || []).includes(illust.id)}
                          onChange={() => handleIllustrationToggle(illust.id)}
                          className="sr-only"
                        />
                        <div className={`w-4 h-4 rounded border flex items-center justify-center ${
                          (editingBundle.illustrationIds || []).includes(illust.id)
                            ? 'bg-pink-500 border-pink-500 text-white'
                            : 'border-gray-300'
                        }`}>
                          {(editingBundle.illustrationIds || []).includes(illust.id) && (
                            <Check className="w-3 h-3" />
                          )}
                        </div>
                        <span className="text-xs truncate">{illust.title}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Save/Cancel */}
            <div className="flex gap-3 pt-4 border-t">
              <Button onClick={handleSave} disabled={saving} className="bg-pink-500 hover:bg-pink-600">
                {saving ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                    Salvataggio...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    {isCreating ? 'Crea Bundle' : 'Salva Modifiche'}
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={handleCancel}>Annulla</Button>
              {isCreating && (
                <p className="text-xs text-gray-500 ml-auto self-center">
                  Dopo la creazione potrai caricare immagine e PDF
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bundle List */}
      <div className="space-y-4">
        {bundles.length === 0 ? (
          <Card className="border-dashed border-2">
            <CardContent className="p-12 text-center">
              <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Nessun bundle creato</p>
              <Button onClick={handleCreate} className="mt-4 bg-pink-500 hover:bg-pink-600">
                <Plus className="w-4 h-4 mr-2" />
                Crea il primo bundle
              </Button>
            </CardContent>
          </Card>
        ) : (
          bundles.map((bundle) => (
            <Card 
              key={bundle.id} 
              className={`transition-all ${!bundle.isActive ? 'opacity-60' : ''} ${editingBundle?.id === bundle.id ? 'ring-2 ring-pink-300' : ''}`}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  {/* Drag Handle & Order */}
                  <div className="flex items-center gap-2 text-gray-400">
                    <GripVertical className="w-4 h-4" />
                    <span className="text-xs font-mono">#{bundle.sortOrder}</span>
                  </div>

                  {/* Background Preview */}
                  <div className="w-16 h-16 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0">
                    {bundle.backgroundImageUrl ? (
                      <img
                        src={`${BACKEND_URL}${bundle.backgroundImageUrl}`}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Image className="w-6 h-6 text-gray-300" />
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-800 truncate">{bundle.title}</h3>
                      {bundle.badgeText && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          bundle.isFree ? 'bg-green-100 text-green-600' : 'bg-pink-100 text-pink-600'
                        }`}>
                          {bundle.badgeText}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 truncate">{bundle.subtitle}</p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                      <span>{bundle.isFree ? 'Gratuito' : `€${bundle.price}`}</span>
                      <span>{bundle.illustrationCount || 0} illustrazioni</span>
                      <span>Opacità: {bundle.backgroundOpacity || 30}%</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleToggleActive(bundle)}
                      className={`p-2 rounded-lg transition-colors ${
                        bundle.isActive ? 'text-green-500 hover:bg-green-50' : 'text-gray-400 hover:bg-gray-100'
                      }`}
                      title={bundle.isActive ? 'Disattiva' : 'Attiva'}
                    >
                      {bundle.isActive ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => handleEdit(bundle)}
                      className="p-2 text-blue-500 hover:bg-blue-50 rounded-lg"
                      title="Modifica"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(bundle.id)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                      title="Elimina"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default AdminBundles;
