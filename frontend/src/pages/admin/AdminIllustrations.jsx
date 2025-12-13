import React, { useState, useEffect } from 'react';
import { Plus, Search, Edit2, Trash2, Upload, Filter, Image, FileText, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { getThemes, getIllustrations, createIllustration, updateIllustration, deleteIllustration, attachPdfToIllustration, attachImageToIllustration } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminIllustrations = () => {
  const [illustrations, setIllustrations] = useState([]);
  const [themes, setThemes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTheme, setFilterTheme] = useState('all');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingIllustration, setEditingIllustration] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    themeId: '',
    isFree: true,
    price: 0.99,
    imageUrl: null,
    pdfUrl: null
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [illustrationsData, themesData] = await Promise.all([
        getIllustrations(),
        getThemes()
      ]);
      setIllustrations(illustrationsData);
      setThemes(themesData);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Errore nel caricamento dei dati');
    } finally {
      setLoading(false);
    }
  };

  const filteredIllustrations = illustrations.filter(i => {
    const matchesSearch = i.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTheme = filterTheme === 'all' || i.themeId === filterTheme;
    return matchesSearch && matchesTheme;
  });

  const handleFileUpload = async (file, type) => {
    setUploading(true);
    try {
      const result = await uploadFile(file, type);
      if (type === 'image') {
        setFormData(prev => ({ ...prev, imageUrl: result.url }));
      } else {
        setFormData(prev => ({ ...prev, pdfUrl: result.url }));
      }
      toast.success('File caricato con successo!');
    } catch (error) {
      toast.error('Errore nel caricamento del file');
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingIllustration) {
        await updateIllustration(editingIllustration.id, formData);
        toast.success('Illustrazione aggiornata!');
      } else {
        await createIllustration(formData);
        toast.success('Illustrazione aggiunta!');
      }
      resetForm();
      fetchData();
    } catch (error) {
      toast.error('Errore nel salvataggio');
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Sei sicuro di voler eliminare questa illustrazione?')) {
      try {
        await deleteIllustration(id);
        toast.success('Illustrazione eliminata!');
        fetchData();
      } catch (error) {
        toast.error('Errore nell\'eliminazione');
      }
    }
  };

  const handleEdit = (illustration) => {
    setEditingIllustration(illustration);
    setFormData({
      title: illustration.title,
      description: illustration.description,
      themeId: illustration.themeId,
      isFree: illustration.isFree,
      price: illustration.price || 0.99,
      imageUrl: illustration.imageUrl,
      pdfUrl: illustration.pdfUrl
    });
    setIsAddOpen(true);
  };

  const resetForm = () => {
    setFormData({ title: '', description: '', themeId: '', isFree: true, price: 0.99, imageUrl: null, pdfUrl: null });
    setEditingIllustration(null);
    setIsAddOpen(false);
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
          <h1 className="text-3xl font-bold text-gray-800">Illustrazioni</h1>
          <p className="text-gray-600">Gestisci le tavole da colorare</p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsAddOpen(true); }}>
          <DialogTrigger asChild>
            <Button className="bg-pink-500 hover:bg-pink-600">
              <Plus className="w-4 h-4 mr-2" />Nuova Illustrazione
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{editingIllustration ? 'Modifica Illustrazione' : 'Nuova Illustrazione'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Titolo</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="es. Pompiconni Pompiere"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Descrizione</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Breve descrizione dell'illustrazione"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Tema</Label>
                <Select value={formData.themeId} onValueChange={(value) => setFormData({ ...formData, themeId: value })}>
                  <SelectTrigger><SelectValue placeholder="Seleziona tema" /></SelectTrigger>
                  <SelectContent>
                    {themes.map(theme => (
                      <SelectItem key={theme.id} value={theme.id}>{theme.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label>Gratuita</Label>
                <Switch
                  checked={formData.isFree}
                  onCheckedChange={(checked) => setFormData({ ...formData, isFree: checked })}
                />
              </div>
              {!formData.isFree && (
                <div className="space-y-2">
                  <Label>Prezzo (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label>Immagine</Label>
                <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                  {formData.imageUrl ? (
                    <div className="mb-2">
                      <img src={`${BACKEND_URL}${formData.imageUrl}`} alt="Preview" className="h-20 mx-auto rounded" />
                      <Button type="button" variant="ghost" size="sm" onClick={() => setFormData(prev => ({ ...prev, imageUrl: null }))}>
                        Rimuovi
                      </Button>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-6 h-6 mx-auto text-gray-400 mb-2" />
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0], 'image')}
                        className="hidden"
                        id="image-upload"
                      />
                      <label htmlFor="image-upload" className="cursor-pointer text-sm text-pink-500 hover:text-pink-600">
                        {uploading ? 'Caricamento...' : 'Carica immagine'}
                      </label>
                    </>
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <Label>PDF</Label>
                <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                  {formData.pdfUrl ? (
                    <div>
                      <p className="text-sm text-green-600 mb-2">PDF caricato ✓</p>
                      <Button type="button" variant="ghost" size="sm" onClick={() => setFormData(prev => ({ ...prev, pdfUrl: null }))}>
                        Rimuovi
                      </Button>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-6 h-6 mx-auto text-gray-400 mb-2" />
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={(e) => e.target.files[0] && handleFileUpload(e.target.files[0], 'pdf')}
                        className="hidden"
                        id="pdf-upload"
                      />
                      <label htmlFor="pdf-upload" className="cursor-pointer text-sm text-pink-500 hover:text-pink-600">
                        {uploading ? 'Caricamento...' : 'Carica PDF'}
                      </label>
                    </>
                  )}
                </div>
              </div>
              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={resetForm} className="flex-1">Annulla</Button>
                <Button type="submit" className="flex-1 bg-pink-500 hover:bg-pink-600">
                  {editingIllustration ? 'Salva Modifiche' : 'Aggiungi'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Cerca illustrazioni..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={filterTheme} onValueChange={setFilterTheme}>
          <SelectTrigger className="w-48">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Tutti i temi" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutti i temi</SelectItem>
            {themes.map(theme => (
              <SelectItem key={theme.id} value={theme.id}>{theme.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Illustrations Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredIllustrations.map((illustration) => (
          <Card key={illustration.id} className="border shadow-sm hover:shadow-md transition-shadow">
            <CardContent className="p-4">
              <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center mb-3 overflow-hidden">
                {illustration.imageUrl ? (
                  <img src={`${BACKEND_URL}${illustration.imageUrl}`} alt={illustration.title} className="w-full h-full object-cover" />
                ) : (
                  <span className="text-4xl opacity-30">🦄</span>
                )}
              </div>
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-800 truncate">{illustration.title}</h3>
                  <p className="text-xs text-gray-500">{themes.find(t => t.id === illustration.themeId)?.name}</p>
                </div>
                <Badge className={illustration.isFree ? 'bg-green-100 text-green-700' : 'bg-pink-100 text-pink-700'}>
                  {illustration.isFree ? 'Gratis' : `€${illustration.price}`}
                </Badge>
              </div>
              <p className="text-sm text-gray-600 truncate mb-3">{illustration.description}</p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">{illustration.downloadCount} download</span>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => handleEdit(illustration)}>
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-red-500 hover:text-red-600 hover:bg-red-50" onClick={() => handleDelete(illustration.id)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredIllustrations.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gray-500">Nessuna illustrazione trovata</p>
        </div>
      )}
    </div>
  );
};

export default AdminIllustrations;
