import React, { useState, useEffect, useRef } from 'react';
import { 
  Image as ImageIcon, Plus, Trash2, Edit, Upload, Download, Ban,
  FileText, Check, X, Eye, EyeOff, Search
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { 
  getAdminPosters, createPoster, updatePoster, deletePoster,
  uploadPosterImage, uploadPosterPdf, getPosterStats, togglePosterDownload
} from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminPosters = () => {
  const [posters, setPosters] = useState([]);
  const [stats, setStats] = useState({ total: 0, published: 0, drafts: 0, free: 0, paid: 0, totalDownloads: 0 });
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [togglingDownload, setTogglingDownload] = useState({});
  
  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingPoster, setEditingPoster] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    price: 0,
    status: 'draft'
  });

  // File upload refs
  const imageInputRef = useRef(null);
  const pdfInputRef = useRef(null);
  const [uploadingFor, setUploadingFor] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [postersData, statsData] = await Promise.all([
        getAdminPosters(),
        getPosterStats()
      ]);
      setPosters(postersData);
      setStats(statsData);
    } catch (error) {
      toast.error('Errore nel caricamento dei poster');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingPoster(null);
    setFormData({ title: '', description: '', price: 0, status: 'draft' });
    setShowModal(true);
  };

  const handleEdit = (poster) => {
    setEditingPoster(poster);
    setFormData({
      title: poster.title,
      description: poster.description || '',
      price: poster.price || 0,
      status: poster.status || 'draft'
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title.trim()) {
      toast.error('Il titolo è obbligatorio');
      return;
    }

    try {
      if (editingPoster) {
        await updatePoster(editingPoster.id, formData);
        toast.success('Poster aggiornato');
      } else {
        await createPoster(formData);
        toast.success('Poster creato! Ora carica immagine e PDF.');
      }
      setShowModal(false);
      fetchData();
    } catch (error) {
      toast.error('Errore nel salvataggio');
    }
  };

  const handleDelete = async (poster) => {
    if (!window.confirm(`Eliminare "${poster.title}"?`)) return;
    
    try {
      await deletePoster(poster.id);
      toast.success('Poster eliminato');
      fetchData();
    } catch (error) {
      toast.error('Errore nell\'eliminazione');
    }
  };

  const handleToggleDownload = async (poster) => {
    // Download toggle only relevant for published posters
    if (poster.status !== 'published') {
      toast.error('Pubblica prima il poster per gestire il download');
      return;
    }
    setTogglingDownload(prev => ({ ...prev, [poster.id]: true }));
    try {
      const result = await togglePosterDownload(poster.id);
      setPosters(prev => prev.map(p => 
        p.id === poster.id 
          ? { ...p, downloadEnabled: result.downloadEnabled }
          : p
      ));
      toast.success(result.downloadEnabled ? 'Download abilitato!' : 'Download disabilitato');
    } catch (error) {
      console.error('Toggle download error:', error);
      toast.error('Errore nel cambio stato download');
    } finally {
      setTogglingDownload(prev => ({ ...prev, [poster.id]: false }));
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingFor) return;

    try {
      await uploadPosterImage(uploadingFor, file);
      toast.success('Immagine caricata');
      fetchData();
    } catch (error) {
      toast.error('Errore nel caricamento immagine');
    } finally {
      setUploadingFor(null);
    }
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingFor) return;

    try {
      await uploadPosterPdf(uploadingFor, file);
      toast.success('PDF caricato');
      fetchData();
    } catch (error) {
      toast.error('Errore nel caricamento PDF');
    } finally {
      setUploadingFor(null);
    }
  };

  const filteredPosters = posters.filter(poster => {
    const matchesSearch = poster.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || poster.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Hidden file inputs */}
      <input
        ref={imageInputRef}
        type="file"
        accept=".jpg,.jpeg,.png"
        onChange={handleImageUpload}
        className="hidden"
      />
      <input
        ref={pdfInputRef}
        type="file"
        accept=".pdf"
        onChange={handlePdfUpload}
        className="hidden"
      />

      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
            <ImageIcon className="w-8 h-8 text-pink-500" />
            Poster
          </h1>
          <p className="text-gray-600">Gestisci i poster decorativi da stampare e incorniciare</p>
        </div>
        <Button 
          onClick={handleCreate}
          className="bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nuovo Poster
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <Card className="border-0 shadow-md">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-pink-500">{stats.total}</p>
            <p className="text-sm text-gray-500">Totale</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-md">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-green-500">{stats.published}</p>
            <p className="text-sm text-gray-500">Pubblicati</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-md">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-yellow-500">{stats.drafts}</p>
            <p className="text-sm text-gray-500">Bozze</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-md">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-blue-500">{stats.free}</p>
            <p className="text-sm text-gray-500">Gratuiti</p>
          </CardContent>
        </Card>
        <Card className="border-0 shadow-md">
          <CardContent className="p-4 text-center">
            <p className="text-2xl font-bold text-purple-500">{stats.totalDownloads}</p>
            <p className="text-sm text-gray-500">Download</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Cerca poster..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Stato" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tutti</SelectItem>
            <SelectItem value="published">Pubblicati</SelectItem>
            <SelectItem value="draft">Bozze</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Posters Grid */}
      {filteredPosters.length === 0 ? (
        <Card className="border-2 border-dashed border-gray-200">
          <CardContent className="py-16 text-center">
            <ImageIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500 mb-2">Nessun poster trovato</p>
            <Button variant="outline" onClick={handleCreate}>
              <Plus className="w-4 h-4 mr-2" />
              Crea il primo poster
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredPosters.map(poster => (
            <Card key={poster.id} className="border-0 shadow-lg overflow-hidden group">
              {/* Image */}
              <div className="h-48 bg-gradient-to-br from-pink-100 to-purple-100 relative">
                {poster.imageUrl ? (
                  <img 
                    src={`${BACKEND_URL}${poster.imageUrl}`}
                    alt={poster.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-6xl">🖼️</span>
                  </div>
                )}
                
                {/* Status badge */}
                <div className="absolute top-2 left-2">
                  {poster.status === 'published' ? (
                    <span className="bg-green-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
                      <Eye className="w-3 h-3" /> Pubblicato
                    </span>
                  ) : (
                    <span className="bg-yellow-500 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
                      <EyeOff className="w-3 h-3" /> Bozza
                    </span>
                  )}
                </div>

                {/* Price badge */}
                <div className="absolute top-2 right-2">
                  {poster.price === 0 ? (
                    <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full font-medium">
                      Gratis
                    </span>
                  ) : (
                    <span className="bg-purple-100 text-purple-700 text-xs px-2 py-1 rounded-full font-medium">
                      €{poster.price?.toFixed(2)}
                    </span>
                  )}
                </div>

                {/* Upload buttons overlay */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <Button 
                    variant="secondary" 
                    size="sm"
                    onClick={() => {
                      setUploadingFor(poster.id);
                      imageInputRef.current?.click();
                    }}
                  >
                    <Upload className="w-4 h-4 mr-1" />
                    Immagine
                  </Button>
                  <Button 
                    variant="secondary" 
                    size="sm"
                    onClick={() => {
                      setUploadingFor(poster.id);
                      pdfInputRef.current?.click();
                    }}
                  >
                    <FileText className="w-4 h-4 mr-1" />
                    PDF
                  </Button>
                </div>
              </div>

              <CardContent className="p-4">
                <h3 className="font-bold text-gray-800 mb-1 line-clamp-1">{poster.title}</h3>
                {poster.description && (
                  <p className="text-sm text-gray-500 mb-3 line-clamp-2">{poster.description}</p>
                )}
                
                {/* File status */}
                <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
                  <span className={poster.imageFileId ? 'text-green-500' : ''}>
                    {poster.imageFileId ? <Check className="w-3 h-3 inline" /> : <X className="w-3 h-3 inline" />} Img
                  </span>
                  <span className={poster.pdfFileId ? 'text-green-500' : ''}>
                    {poster.pdfFileId ? <Check className="w-3 h-3 inline" /> : <X className="w-3 h-3 inline" />} PDF
                  </span>
                  <span>
                    <Download className="w-3 h-3 inline" /> {poster.downloadCount || 0}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="flex-1" onClick={() => handleEdit(poster)}>
                    <Edit className="w-4 h-4 mr-1" />
                    Modifica
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => handleToggleDownload(poster)}
                    disabled={togglingDownload[poster.id] || poster.status !== 'published'}
                    title={poster.status !== 'published' ? 'Pubblica prima per gestire il download' : (poster.downloadEnabled !== false ? 'Disabilita download' : 'Abilita download')}
                    className={poster.status !== 'published' ? 'text-gray-300' : (poster.downloadEnabled !== false ? 'text-blue-500' : 'text-red-400')}
                  >
                    {togglingDownload[poster.id] ? (
                      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    ) : poster.downloadEnabled !== false ? (
                      <Download className="w-4 h-4" />
                    ) : (
                      <DownloadOff className="w-4 h-4" />
                    )}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleDelete(poster)}>
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md border-0 shadow-2xl">
            <CardHeader>
              <CardTitle>{editingPoster ? 'Modifica Poster' : 'Nuovo Poster'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label>Titolo *</Label>
                  <Input
                    value={formData.title}
                    onChange={(e) => setFormData({...formData, title: e.target.value})}
                    placeholder="Es: Poppiconni al Mare"
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Descrizione</Label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    placeholder="Descrizione del poster..."
                    rows={3}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Prezzo (€)</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={formData.price}
                      onChange={(e) => setFormData({...formData, price: parseFloat(e.target.value) || 0})}
                    />
                    <p className="text-xs text-gray-400">0 = gratuito</p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Stato</Label>
                    <Select 
                      value={formData.status} 
                      onValueChange={(val) => setFormData({...formData, status: val})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="draft">Bozza</SelectItem>
                        <SelectItem value="published">Pubblicato</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="flex gap-3 pt-4">
                  <Button type="button" variant="outline" className="flex-1" onClick={() => setShowModal(false)}>
                    Annulla
                  </Button>
                  <Button type="submit" className="flex-1 bg-pink-500 hover:bg-pink-600">
                    {editingPoster ? 'Salva' : 'Crea'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default AdminPosters;
