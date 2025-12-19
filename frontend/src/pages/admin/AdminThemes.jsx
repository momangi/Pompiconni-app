import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Palette, BookOpen, AlertTriangle, Check, Upload, Image } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { getThemes, createTheme, updateTheme, checkThemeDelete, deleteTheme, getThemeColorPalette, uploadThemeBackground } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminThemes = () => {
  const [themes, setThemes] = useState([]);
  const [colorPalette, setColorPalette] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingTheme, setEditingTheme] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, theme: null, info: null });
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    icon: 'BookOpen',
    color: '#FFB6C1',
    backgroundOpacity: 30
  });
  const [bgUploading, setBgUploading] = useState(false);

  const iconOptions = [
    { value: 'BookOpen', label: 'Libro' },
    { value: 'Palette', label: 'Tavolozza' },
    { value: 'Star', label: 'Stella' },
    { value: 'Heart', label: 'Cuore' },
    { value: 'Sun', label: 'Sole' },
    { value: 'Cloud', label: 'Nuvola' },
    { value: 'Flower', label: 'Fiore' },
    { value: 'Home', label: 'Casa' }
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [themesData, paletteData] = await Promise.all([
        getThemes(),
        getThemeColorPalette()
      ]);
      setThemes(themesData);
      setColorPalette(paletteData);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Errore nel caricamento dei temi');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingTheme) {
        await updateTheme(editingTheme.id, formData);
        toast.success('Tema aggiornato!');
      } else {
        await createTheme(formData);
        toast.success('Tema creato!');
      }
      resetForm();
      fetchData();
    } catch (error) {
      toast.error('Errore nel salvataggio');
    }
  };

  const handleDeleteClick = async (theme) => {
    try {
      const info = await checkThemeDelete(theme.id);
      setDeleteDialog({ open: true, theme, info });
    } catch (error) {
      toast.error('Errore nella verifica');
    }
  };

  const handleDeleteConfirm = async (force = false) => {
    try {
      await deleteTheme(deleteDialog.theme.id, force);
      toast.success('Tema eliminato!');
      setDeleteDialog({ open: false, theme: null, info: null });
      fetchData();
    } catch (error) {
      toast.error('Errore nell\'eliminazione');
    }
  };

  const handleEdit = (theme) => {
    setEditingTheme(theme);
    setFormData({
      name: theme.name,
      description: theme.description,
      icon: theme.icon || 'BookOpen',
      color: theme.color || '#FFB6C1',
      backgroundOpacity: theme.backgroundOpacity ?? 30
    });
    setIsAddOpen(true);
  };

  const resetForm = () => {
    setFormData({ name: '', description: '', icon: 'BookOpen', color: '#FFB6C1', backgroundOpacity: 30 });
    setEditingTheme(null);
    setIsAddOpen(false);
  };

  const handleBackgroundUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !editingTheme) return;

    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      toast.error('Solo file JPG, PNG o WEBP');
      return;
    }

    setBgUploading(true);
    try {
      const result = await uploadThemeBackground(editingTheme.id, file);
      setEditingTheme(prev => ({ ...prev, backgroundImageUrl: result.backgroundImageUrl }));
      toast.success('Immagine sfondo caricata!');
      fetchData();
    } catch (error) {
      toast.error('Errore durante il caricamento');
    } finally {
      setBgUploading(false);
    }
  };

  // Get colors already used by other themes (excluding current editing theme)
  const usedColors = themes
    .filter(t => !editingTheme || t.id !== editingTheme.id)
    .map(t => t.color);

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
            <Palette className="w-8 h-8 text-pink-500" />
            Gestione Temi
          </h1>
          <p className="text-gray-600 mt-1">Crea e gestisci i temi delle illustrazioni</p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsAddOpen(true); }}>
          <DialogTrigger asChild>
            <Button className="bg-pink-500 hover:bg-pink-600">
              <Plus className="w-4 h-4 mr-2" />Nuovo Tema
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{editingTheme ? 'Modifica Tema' : 'Nuovo Tema'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Nome Tema</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="es. Animali della Fattoria"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Descrizione</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Breve descrizione del tema"
                  required
                />
              </div>
              
              {/* Color Palette Selection */}
              <div className="space-y-2">
                <Label>Colore Tema</Label>
                <div className="grid grid-cols-6 gap-2">
                  {colorPalette.map((color) => {
                    const isUsed = usedColors.includes(color.value);
                    const isSelected = formData.color === color.value;
                    return (
                      <button
                        key={color.value}
                        type="button"
                        onClick={() => !isUsed && setFormData({ ...formData, color: color.value })}
                        className={`
                          w-10 h-10 rounded-lg border-2 transition-all relative
                          ${isSelected ? 'border-gray-800 scale-110 ring-2 ring-gray-400' : 'border-transparent'}
                          ${isUsed ? 'opacity-40 cursor-not-allowed' : 'hover:scale-105 cursor-pointer'}
                        `}
                        style={{ backgroundColor: color.value }}
                        title={`${color.name}${isUsed ? ' (già in uso)' : ''}`}
                        disabled={isUsed}
                      >
                        {isSelected && (
                          <Check className="w-4 h-4 text-white absolute inset-0 m-auto drop-shadow-md" />
                        )}
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-gray-500">
                  Colore selezionato: {colorPalette.find(c => c.value === formData.color)?.name || 'Custom'}
                </p>
              </div>

              {/* Background Image + Opacity (only for editing existing themes) */}
              {editingTheme && (
                <div className="space-y-3 p-3 bg-gray-50 rounded-lg">
                  <Label className="flex items-center gap-2">
                    <Image className="w-4 h-4" />
                    Immagine Sfondo + Opacità
                  </Label>
                  
                  {/* Preview */}
                  <div className="h-24 rounded-lg overflow-hidden relative bg-gray-800">
                    {editingTheme.backgroundImageUrl ? (
                      <>
                        <div 
                          className="absolute inset-0 bg-cover bg-center"
                          style={{ 
                            backgroundImage: `url(${BACKEND_URL}${editingTheme.backgroundImageUrl}?t=${Date.now()})`,
                            filter: 'blur(4px)',
                            transform: 'scale(1.1)',
                            opacity: (formData.backgroundOpacity ?? 30) / 100
                          }}
                        />
                        <div className="absolute inset-0 bg-white/60" />
                        <div className="absolute inset-0 flex items-center justify-center z-10">
                          <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full">PREVIEW LIVE</span>
                        </div>
                      </>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400 bg-gray-100">
                        <span className="text-xs">Nessuna immagine</span>
                      </div>
                    )}
                  </div>

                  {/* Upload */}
                  <div>
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.webp"
                      onChange={handleBackgroundUpload}
                      className="hidden"
                      id="theme-bg-upload"
                      disabled={bgUploading}
                    />
                    <label
                      htmlFor="theme-bg-upload"
                      className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg cursor-pointer ${
                        bgUploading ? 'bg-gray-100 text-gray-400' : 'bg-pink-50 text-pink-600 hover:bg-pink-100'
                      }`}
                    >
                      <Upload className="w-3 h-3" />
                      {bgUploading ? 'Caricamento...' : editingTheme.backgroundImageUrl ? 'Cambia immagine' : 'Carica immagine'}
                    </label>
                  </div>

                  {/* Opacity Slider */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-600">Opacità sfondo</span>
                      <span className="text-sm font-bold text-pink-500">{formData.backgroundOpacity ?? 30}%</span>
                    </div>
                    <input
                      type="range"
                      min="10"
                      max="80"
                      value={formData.backgroundOpacity ?? 30}
                      onChange={(e) => setFormData({ ...formData, backgroundOpacity: parseInt(e.target.value) })}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-pink-500"
                    />
                    <div className="flex justify-between text-xs text-gray-400">
                      <span>10%</span>
                      <span>80%</span>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={resetForm} className="flex-1">
                  Annulla
                </Button>
                <Button type="submit" className="flex-1 bg-pink-500 hover:bg-pink-600">
                  {editingTheme ? 'Salva Modifiche' : 'Crea Tema'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Themes Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {themes.map((theme) => (
          <Card 
            key={theme.id} 
            className="border-2 hover:shadow-lg transition-shadow overflow-hidden"
            style={{ borderColor: theme.color }}
          >
            <div 
              className="h-3"
              style={{ backgroundColor: theme.color }}
            />
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div 
                  className="w-12 h-12 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${theme.color}30` }}
                >
                  <BookOpen className="w-6 h-6" style={{ color: theme.color }} />
                </div>
                <Badge variant="outline" className="text-xs">
                  {theme.illustrationCount || 0} illustrazioni
                </Badge>
              </div>
              
              <h3 className="font-bold text-lg text-gray-800 mb-1">{theme.name}</h3>
              <p className="text-sm text-gray-600 mb-4 line-clamp-2">{theme.description}</p>
              
              <div className="flex items-center justify-between pt-3 border-t">
                <div 
                  className="w-6 h-6 rounded-full border-2 border-white shadow"
                  style={{ backgroundColor: theme.color }}
                  title={colorPalette.find(c => c.value === theme.color)?.name || theme.color}
                />
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => handleEdit(theme)}>
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="text-red-500 hover:text-red-600 hover:bg-red-50"
                    onClick={() => handleDeleteClick(theme)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {themes.length === 0 && (
        <div className="text-center py-16">
          <Palette className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">Nessun tema creato</p>
          <p className="text-gray-400">Crea il primo tema per organizzare le illustrazioni</p>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onOpenChange={(open) => !open && setDeleteDialog({ open: false, theme: null, info: null })}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              Elimina Tema
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <p className="text-gray-600">
              Stai per eliminare il tema <strong>{deleteDialog.theme?.name}</strong>.
            </p>
            
            {deleteDialog.info?.illustrationCount > 0 ? (
              <div className="p-4 bg-yellow-50 rounded-lg">
                <p className="text-yellow-700 font-medium">
                  Attenzione: questo tema ha {deleteDialog.info.illustrationCount} illustrazioni associate.
                </p>
                <p className="text-sm text-yellow-600 mt-1">
                  Eliminando il tema, le illustrazioni verranno riassegnate a &quot;Senza tema&quot;.
                </p>
              </div>
            ) : (
              <p className="text-green-600 text-sm">
                Questo tema non ha illustrazioni associate e può essere eliminato.
              </p>
            )}
            
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={() => setDeleteDialog({ open: false, theme: null, info: null })}
                className="flex-1"
              >
                Annulla
              </Button>
              <Button 
                className="flex-1 bg-red-500 hover:bg-red-600"
                onClick={() => handleDeleteConfirm(deleteDialog.info?.illustrationCount > 0)}
              >
                {deleteDialog.info?.illustrationCount > 0 ? 'Elimina Comunque' : 'Elimina'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminThemes;
