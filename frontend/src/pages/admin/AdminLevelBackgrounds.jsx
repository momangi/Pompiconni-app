import React, { useState, useEffect, useCallback } from 'react';
import { 
  Plus, Trash2, Upload, Image as ImageIcon, Save, 
  Layers, ChevronRight, AlertCircle 
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { 
  adminGetLevelBackgrounds, 
  adminCreateLevelBackground, 
  adminUpdateLevelBackground,
  adminUploadLevelBackgroundImage,
  adminDeleteLevelBackground 
} from '../../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Generate level ranges (1-5, 6-10, 11-15, etc.)
const LEVEL_RANGES = [];
for (let i = 1; i <= 50; i += 5) {
  LEVEL_RANGES.push({ start: i, end: i + 4, label: `Livelli ${i}-${i + 4}` });
}

const AdminLevelBackgrounds = () => {
  const [backgrounds, setBackgrounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // New background form
  const [showForm, setShowForm] = useState(false);
  const [selectedRange, setSelectedRange] = useState(null);
  const [newOpacity, setNewOpacity] = useState(30);
  const [newImage, setNewImage] = useState(null);
  const [newImagePreview, setNewImagePreview] = useState(null);

  const fetchBackgrounds = useCallback(async () => {
    try {
      setLoading(true);
      const data = await adminGetLevelBackgrounds();
      setBackgrounds(data);
      setError(null);
    } catch (err) {
      setError('Errore nel caricamento degli sfondi');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBackgrounds();
  }, [fetchBackgrounds]);

  // Get available ranges (not already used)
  const getAvailableRanges = () => {
    const usedRanges = backgrounds.map(bg => `${bg.levelRangeStart}-${bg.levelRangeEnd}`);
    return LEVEL_RANGES.filter(r => !usedRanges.includes(`${r.start}-${r.end}`));
  };

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setNewImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setNewImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleCreate = async () => {
    if (!selectedRange) {
      setError('Seleziona un range di livelli');
      return;
    }

    try {
      setSaving(true);
      const formData = new FormData();
      formData.append('levelRangeStart', selectedRange.start);
      formData.append('levelRangeEnd', selectedRange.end);
      formData.append('backgroundOpacity', newOpacity);
      if (newImage) {
        formData.append('backgroundImage', newImage);
      }

      await adminCreateLevelBackground(formData);
      
      // Reset form
      setShowForm(false);
      setSelectedRange(null);
      setNewOpacity(30);
      setNewImage(null);
      setNewImagePreview(null);
      
      fetchBackgrounds();
    } catch (err) {
      setError('Errore nella creazione dello sfondo');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateOpacity = async (bgId, opacity) => {
    try {
      const formData = new FormData();
      formData.append('backgroundOpacity', opacity);
      await adminUpdateLevelBackground(bgId, formData);
      
      setBackgrounds(prev => prev.map(bg => 
        bg.id === bgId ? { ...bg, backgroundOpacity: opacity } : bg
      ));
    } catch (err) {
      setError('Errore nell\'aggiornamento');
      console.error(err);
    }
  };

  const handleUploadImage = async (bgId, file) => {
    try {
      setSaving(true);
      await adminUploadLevelBackgroundImage(bgId, file);
      fetchBackgrounds();
    } catch (err) {
      setError('Errore nel caricamento dell\'immagine');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (bgId) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo sfondo?')) return;
    
    try {
      await adminDeleteLevelBackground(bgId);
      fetchBackgrounds();
    } catch (err) {
      setError('Errore nell\'eliminazione');
      console.error(err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Layers className="w-7 h-7 text-pink-500" />
            Sfondi Livelli - Bolle Magiche
          </h1>
          <p className="text-gray-500 mt-1">
            Gestisci gli sfondi di gioco (cambiano ogni 5 livelli)
          </p>
        </div>
        <Button 
          onClick={() => setShowForm(true)}
          className="bg-pink-500 hover:bg-pink-600"
          disabled={getAvailableRanges().length === 0}
        >
          <Plus className="w-4 h-4 mr-2" />
          Nuovo Sfondo
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-2 text-red-700">
          <AlertCircle className="w-5 h-5" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">×</button>
        </div>
      )}

      {/* New Background Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Nuovo Sfondo Livelli</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Range Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Range Livelli
              </label>
              <select
                value={selectedRange ? `${selectedRange.start}-${selectedRange.end}` : ''}
                onChange={(e) => {
                  const [start, end] = e.target.value.split('-').map(Number);
                  setSelectedRange({ start, end });
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-pink-500"
              >
                <option value="">Seleziona range...</option>
                {getAvailableRanges().map(range => (
                  <option key={`${range.start}-${range.end}`} value={`${range.start}-${range.end}`}>
                    {range.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Opacity Slider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Opacità Overlay: {newOpacity}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={newOpacity}
                onChange={(e) => setNewOpacity(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <p className="text-xs text-gray-500 mt-1">
                0% = immagine nitida, 100% = molto velata
              </p>
            </div>

            {/* Image Upload */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Immagine Sfondo
              </label>
              <div className="flex items-start gap-4">
                {/* Preview */}
                <div 
                  className="w-40 h-28 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center overflow-hidden bg-gray-50"
                >
                  {newImagePreview ? (
                    <div className="relative w-full h-full">
                      <img 
                        src={newImagePreview} 
                        alt="Preview" 
                        className="w-full h-full object-cover"
                      />
                      {/* Overlay preview */}
                      <div 
                        className="absolute inset-0"
                        style={{ 
                          backgroundColor: `rgba(255, 255, 255, ${newOpacity / 100})`,
                          backdropFilter: `blur(${newOpacity / 25}px)`,
                        }}
                      />
                    </div>
                  ) : (
                    <ImageIcon className="w-8 h-8 text-gray-400" />
                  )}
                </div>
                
                {/* Upload button */}
                <div className="flex-1">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageSelect}
                    className="hidden"
                    id="new-bg-image"
                  />
                  <label
                    htmlFor="new-bg-image"
                    className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50"
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    Carica Immagine
                  </label>
                  <p className="text-xs text-gray-500 mt-2">
                    Consigliato: 1920x1080, PNG/JPG
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
            <Button 
              variant="outline" 
              onClick={() => {
                setShowForm(false);
                setSelectedRange(null);
                setNewImage(null);
                setNewImagePreview(null);
              }}
            >
              Annulla
            </Button>
            <Button 
              onClick={handleCreate}
              disabled={!selectedRange || saving}
              className="bg-pink-500 hover:bg-pink-600"
            >
              {saving ? 'Salvataggio...' : 'Crea Sfondo'}
            </Button>
          </div>
        </div>
      )}

      {/* Backgrounds List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {backgrounds.map(bg => (
          <div 
            key={bg.id}
            className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow"
          >
            {/* Image Preview with Overlay */}
            <div className="relative h-32 bg-gray-100">
              {bg.backgroundImageUrl ? (
                <>
                  <img 
                    src={`${BACKEND_URL}${bg.backgroundImageUrl}`}
                    alt={`Sfondo ${bg.levelRangeStart}-${bg.levelRangeEnd}`}
                    className="w-full h-full object-cover"
                  />
                  {/* Overlay preview */}
                  <div 
                    className="absolute inset-0"
                    style={{ 
                      backgroundColor: `rgba(255, 255, 255, ${(bg.backgroundOpacity || 30) / 100})`,
                      backdropFilter: `blur(${(bg.backgroundOpacity || 30) / 25}px)`,
                    }}
                  />
                </>
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <ImageIcon className="w-12 h-12 text-gray-300" />
                </div>
              )}
              
              {/* Level badge */}
              <div className="absolute top-2 left-2 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-full text-sm font-medium text-gray-700">
                LV {bg.levelRangeStart}-{bg.levelRangeEnd}
              </div>
            </div>

            {/* Controls */}
            <div className="p-4 space-y-3">
              {/* Opacity Slider */}
              <div>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-600">Opacità Overlay</span>
                  <span className="font-medium">{bg.backgroundOpacity || 30}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={bg.backgroundOpacity || 30}
                  onChange={(e) => handleUpdateOpacity(bg.id, Number(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => {
                    if (e.target.files[0]) {
                      handleUploadImage(bg.id, e.target.files[0]);
                    }
                  }}
                  className="hidden"
                  id={`upload-${bg.id}`}
                />
                <label
                  htmlFor={`upload-${bg.id}`}
                  className="flex-1 flex items-center justify-center gap-1 px-3 py-2 text-sm border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50"
                >
                  <Upload className="w-4 h-4" />
                  {bg.backgroundImageUrl ? 'Cambia' : 'Carica'}
                </label>
                <button
                  onClick={() => handleDelete(bg.id)}
                  className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}

        {/* Empty State */}
        {backgrounds.length === 0 && !showForm && (
          <div className="col-span-full text-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
            <Layers className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-700 mb-1">Nessuno sfondo configurato</h3>
            <p className="text-gray-500 mb-4">Aggiungi sfondi per rendere il gioco più coinvolgente</p>
            <Button onClick={() => setShowForm(true)} className="bg-pink-500 hover:bg-pink-600">
              <Plus className="w-4 h-4 mr-2" />
              Aggiungi Primo Sfondo
            </Button>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-800 mb-2">Come funziona</h4>
        <ul className="text-sm text-blue-700 space-y-1">
          <li className="flex items-center gap-2">
            <ChevronRight className="w-4 h-4" />
            Gli sfondi cambiano automaticamente ogni 5 livelli
          </li>
          <li className="flex items-center gap-2">
            <ChevronRight className="w-4 h-4" />
            L'opacità controlla un overlay bianco + blur (come Temi e Bundle)
          </li>
          <li className="flex items-center gap-2">
            <ChevronRight className="w-4 h-4" />
            0% = immagine nitida, 100% = molto velata
          </li>
          <li className="flex items-center gap-2">
            <ChevronRight className="w-4 h-4" />
            Le bolle rimangono sempre perfettamente leggibili
          </li>
        </ul>
      </div>
    </div>
  );
};

export default AdminLevelBackgrounds;
