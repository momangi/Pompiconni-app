import React, { useState, useEffect } from 'react';
import { Plus, Search, Edit2, Trash2, Upload, Filter, Image, FileText, CheckCircle, XCircle, Eye, EyeOff, Download, Ban } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { getThemes, getAdminIllustrations, createIllustration, updateIllustration, deleteIllustration, attachPdfToIllustration, attachImageToIllustration, toggleIllustrationPublish, toggleIllustrationDownload } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminIllustrations = () => {
  const [illustrations, setIllustrations] = useState([]);
  const [themes, setThemes] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTheme, setFilterTheme] = useState('all');
  const [filterPublished, setFilterPublished] = useState('all');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingIllustration, setEditingIllustration] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState({ image: false, pdf: false });
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadTarget, setUploadTarget] = useState(null);
  const [togglingPublish, setTogglingPublish] = useState({});
  const [togglingDownload, setTogglingDownload] = useState({});
  
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
        getAdminIllustrations(),
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
    const matchesPublished = filterPublished === 'all' || 
      (filterPublished === 'published' && i.isPublished) ||
      (filterPublished === 'draft' && !i.isPublished);
    return matchesSearch && matchesTheme && matchesPublished;
  });

  const handleTogglePublish = async (illustration) => {
    setTogglingPublish(prev => ({ ...prev, [illustration.id]: true }));
    try {
      const result = await toggleIllustrationPublish(illustration.id);
      setIllustrations(prev => prev.map(i => 
        i.id === illustration.id 
          ? { ...i, isPublished: result.isPublished, publishedAt: result.publishedAt }
          : i
      ));
      toast.success(result.isPublished ? 'Illustrazione pubblicata!' : 'Illustrazione messa in bozza');
    } catch (error) {
      console.error('Toggle publish error:', error);
      toast.error('Errore nel cambio stato');
    } finally {
      setTogglingPublish(prev => ({ ...prev, [illustration.id]: false }));
    }
  };

  const handleToggleDownload = async (illustration) => {
    // Download toggle only relevant for published illustrations
    if (!illustration.isPublished) {
      toast.error('Pubblica prima l\'illustrazione per gestire il download');
      return;
    }
    setTogglingDownload(prev => ({ ...prev, [illustration.id]: true }));
    try {
      const result = await toggleIllustrationDownload(illustration.id);
      setIllustrations(prev => prev.map(i => 
        i.id === illustration.id 
          ? { ...i, downloadEnabled: result.downloadEnabled }
          : i
      ));
      toast.success(result.downloadEnabled ? 'Download abilitato!' : 'Download disabilitato');
    } catch (error) {
      console.error('Toggle download error:', error);
      toast.error('Errore nel cambio stato download');
    } finally {
      setTogglingDownload(prev => ({ ...prev, [illustration.id]: false }));
    }
  };

  // Upload file directly to an existing illustration via GridFS
  const handleAttachFile = async (illustrationId, file, type) => {
    setUploading(prev => ({ ...prev, [type]: true }));
    try {
      if (type === 'image') {
        await attachImageToIllustration(illustrationId, file);
        toast.success('Immagine caricata con successo!');
      } else {
        await attachPdfToIllustration(illustrationId, file);
        toast.success('PDF caricato con successo!');
      }
      fetchData(); // Refresh data
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(`Errore nel caricamento del ${type === 'image' ? 'immagine' : 'PDF'}`);
    } finally {
      setUploading(prev => ({ ...prev, [type]: false }));
      setUploadDialogOpen(false);
      setUploadTarget(null);
    }
  };

  const openUploadDialog = (illustration) => {
    setUploadTarget(illustration);
    setUploadDialogOpen(true);
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
                  placeholder="es. Poppiconni Pompiere"
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
              <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded-lg">
                <p className="font-medium text-gray-700 mb-1">Nota:</p>
                <p>Dopo aver creato l&apos;illustrazione, potrai caricare immagine e PDF cliccando sul pulsante upload nella card.</p>
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
        <Select value={filterPublished} onValueChange={setFilterPublished}>
          <SelectTrigger className="w-48">
            <Eye className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Tutti gli stati" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutti gli stati</SelectItem>
            <SelectItem value="published">✅ Pubblicate</SelectItem>
            <SelectItem value="draft">📝 Bozze</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Illustrations Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredIllustrations.map((illustration) => (
          <Card key={illustration.id} className={`border shadow-sm hover:shadow-md transition-shadow ${!illustration.isPublished ? 'border-amber-200 bg-amber-50/30' : ''}`}>
            <CardContent className="p-4">
              <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center mb-3 overflow-hidden relative">
                {illustration.imageFileId ? (
                  <img 
                    src={`${BACKEND_URL}/api/illustrations/${illustration.id}/image`} 
                    alt={illustration.title} 
                    className="w-full h-full object-cover" 
                  />
                ) : illustration.imageUrl ? (
                  <img 
                    src={`${BACKEND_URL}${illustration.imageUrl}`} 
                    alt={illustration.title} 
                    className="w-full h-full object-cover" 
                  />
                ) : (
                  <span className="text-4xl opacity-30">🦄</span>
                )}
                {/* Published status overlay */}
                {!illustration.isPublished && (
                  <div className="absolute top-2 left-2">
                    <Badge className="bg-amber-500 text-white text-xs">
                      📝 Bozza
                    </Badge>
                  </div>
                )}
              </div>
              
              {/* File status badges */}
              <div className="flex gap-2 mb-2">
                <Badge 
                  variant="outline" 
                  className={illustration.imageFileId ? 'border-green-300 text-green-600' : 'border-gray-300 text-gray-400'}
                >
                  <Image className="w-3 h-3 mr-1" />
                  {illustration.imageFileId ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                </Badge>
                <Badge 
                  variant="outline" 
                  className={illustration.pdfFileId ? 'border-green-300 text-green-600' : 'border-gray-300 text-gray-400'}
                >
                  <FileText className="w-3 h-3 mr-1" />
                  {illustration.pdfFileId ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                </Badge>
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
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => handleTogglePublish(illustration)}
                    disabled={togglingPublish[illustration.id]}
                    title={illustration.isPublished ? 'Metti in bozza' : 'Pubblica'}
                    className={illustration.isPublished ? 'text-green-600 hover:text-green-700 hover:bg-green-50' : 'text-amber-600 hover:text-amber-700 hover:bg-amber-50'}
                  >
                    {togglingPublish[illustration.id] ? (
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    ) : illustration.isPublished ? (
                      <Eye className="w-4 h-4" />
                    ) : (
                      <EyeOff className="w-4 h-4" />
                    )}
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => handleToggleDownload(illustration)}
                    disabled={togglingDownload[illustration.id] || !illustration.isPublished}
                    title={!illustration.isPublished ? 'Pubblica prima per gestire il download' : (illustration.downloadEnabled !== false ? 'Disabilita download' : 'Abilita download')}
                    className={!illustration.isPublished ? 'text-gray-300 cursor-not-allowed' : (illustration.downloadEnabled !== false ? 'text-blue-600 hover:text-blue-700 hover:bg-blue-50' : 'text-red-400 hover:text-red-500 hover:bg-red-50')}
                  >
                    {togglingDownload[illustration.id] ? (
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    ) : illustration.downloadEnabled !== false ? (
                      <Download className="w-4 h-4" />
                    ) : (
                      <span className="relative">
                        <Download className="w-4 h-4" />
                        <Ban className="w-4 h-4 absolute -top-0.5 -left-0.5 text-red-500" />
                      </span>
                    )}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => openUploadDialog(illustration)} title="Carica file">
                    <Upload className="w-4 h-4" />
                  </Button>
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
      
      {/* Upload Dialog for existing illustration */}
      <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Carica file per: {uploadTarget?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {/* Image Upload */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Image className="w-4 h-4" />
                Immagine (JPG, JPEG, PNG)
                {uploadTarget?.imageFileId && <CheckCircle className="w-4 h-4 text-green-500" />}
              </Label>
              <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                {uploadTarget?.imageFileId ? (
                  <div>
                    <p className="text-sm text-green-600 mb-2">Immagine presente</p>
                    <p className="text-xs text-gray-400">Carica una nuova immagine per sostituire</p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 mb-2">Nessuna immagine caricata</p>
                )}
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png"
                  onChange={(e) => e.target.files[0] && handleAttachFile(uploadTarget?.id, e.target.files[0], 'image')}
                  className="hidden"
                  id="attach-image"
                  disabled={uploading.image}
                />
                <label 
                  htmlFor="attach-image" 
                  className={`inline-flex items-center px-4 py-2 rounded-lg cursor-pointer ${uploading.image ? 'bg-gray-100 text-gray-400' : 'bg-pink-50 text-pink-600 hover:bg-pink-100'}`}
                >
                  {uploading.image ? (
                    <><div className="animate-spin w-4 h-4 border-2 border-pink-500 border-t-transparent rounded-full mr-2" />Caricamento...</>
                  ) : (
                    <><Upload className="w-4 h-4 mr-2" />Carica immagine</>
                  )}
                </label>
              </div>
            </div>
            
            {/* PDF Upload */}
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                PDF (per download)
                {uploadTarget?.pdfFileId && <CheckCircle className="w-4 h-4 text-green-500" />}
              </Label>
              <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                {uploadTarget?.pdfFileId ? (
                  <div>
                    <p className="text-sm text-green-600 mb-2">PDF presente</p>
                    <p className="text-xs text-gray-400">Carica un nuovo PDF per sostituire</p>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 mb-2">Nessun PDF caricato</p>
                )}
                <input
                  type="file"
                  accept=".pdf"
                  onChange={(e) => e.target.files[0] && handleAttachFile(uploadTarget?.id, e.target.files[0], 'pdf')}
                  className="hidden"
                  id="attach-pdf"
                  disabled={uploading.pdf}
                />
                <label 
                  htmlFor="attach-pdf" 
                  className={`inline-flex items-center px-4 py-2 rounded-lg cursor-pointer ${uploading.pdf ? 'bg-gray-100 text-gray-400' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'}`}
                >
                  {uploading.pdf ? (
                    <><div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full mr-2" />Caricamento...</>
                  ) : (
                    <><Upload className="w-4 h-4 mr-2" />Carica PDF</>
                  )}
                </label>
              </div>
            </div>
            
            <Button variant="outline" className="w-full" onClick={() => setUploadDialogOpen(false)}>
              Chiudi
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminIllustrations;
