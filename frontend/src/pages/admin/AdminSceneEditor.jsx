import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, Upload, Image, Save, Eye, ChevronLeft, ChevronRight, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import SceneTextEditor from '../../components/editor/SceneTextEditor';
import { 
  getAdminBooks, 
  getBookScenes, 
  createScene, 
  updateScene, 
  deleteScene,
  uploadSceneColoredImage,
  uploadSceneLineartImage
} from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const MAX_SCENES = 15;

const AdminSceneEditor = () => {
  const { bookId } = useParams();
  const navigate = useNavigate();
  
  const [book, setBook] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedScene, setSelectedScene] = useState(null);
  const [editorContent, setEditorContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState({ colored: false, lineart: false });
  const [previewOpen, setPreviewOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      // Get book details
      const books = await getAdminBooks();
      const currentBook = books.find(b => b.id === bookId);
      if (!currentBook) {
        toast.error('Libro non trovato');
        navigate('/admin/books');
        return;
      }
      setBook(currentBook);

      // Get scenes
      const scenesData = await getBookScenes(bookId);
      setScenes(scenesData);

      // Select first scene if available
      if (scenesData.length > 0 && !selectedScene) {
        setSelectedScene(scenesData[0]);
        setEditorContent(scenesData[0].text?.html || '');
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      if (error.response?.status === 401) {
        toast.error('Sessione scaduta. Effettua nuovamente il login.');
        navigate('/admin/login');
      } else {
        toast.error('Errore nel caricamento dei dati');
      }
    } finally {
      setLoading(false);
    }
  }, [bookId, navigate, selectedScene]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateScene = async () => {
    if (scenes.length >= MAX_SCENES) {
      toast.error(`Limite massimo di ${MAX_SCENES} scene raggiunto`);
      return;
    }

    // Find next available scene number
    const usedNumbers = scenes.map(s => s.sceneNumber);
    let nextNumber = 1;
    while (usedNumbers.includes(nextNumber) && nextNumber <= MAX_SCENES) {
      nextNumber++;
    }

    if (nextNumber > MAX_SCENES) {
      toast.error('Tutti i numeri di scena sono già utilizzati');
      return;
    }

    try {
      const newScene = await createScene(bookId, {
        sceneNumber: nextNumber,
        text: { html: '' }
      });
      toast.success(`Scena ${nextNumber} creata`);
      
      // Refresh and select new scene
      const scenesData = await getBookScenes(bookId);
      setScenes(scenesData);
      const created = scenesData.find(s => s.id === newScene.id);
      if (created) {
        setSelectedScene(created);
        setEditorContent('');
      }
      
      // Update book scene count
      if (book) {
        setBook({ ...book, sceneCount: (book.sceneCount || 0) + 1 });
      }
    } catch (error) {
      console.error('Error creating scene:', error);
      if (error.response?.status === 400) {
        toast.error(error.response.data.detail || 'Errore nella creazione');
      } else {
        toast.error('Errore nella creazione della scena');
      }
    }
  };

  const handleSelectScene = (scene) => {
    // Save current scene before switching
    if (selectedScene && editorContent !== (selectedScene.text?.html || '')) {
      handleSaveText();
    }
    setSelectedScene(scene);
    setEditorContent(scene.text?.html || '');
  };

  const handleSaveText = async () => {
    if (!selectedScene) return;

    setSaving(true);
    try {
      await updateScene(bookId, selectedScene.id, { html: editorContent });
      toast.success('Testo salvato');
      
      // Update local state
      setScenes(scenes.map(s => 
        s.id === selectedScene.id 
          ? { ...s, text: { html: editorContent } }
          : s
      ));
      setSelectedScene({ ...selectedScene, text: { html: editorContent } });
    } catch (error) {
      console.error('Error saving text:', error);
      toast.error('Errore nel salvataggio');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteScene = async (sceneId, sceneNumber) => {
    if (!window.confirm(`Eliminare la scena ${sceneNumber}? Questa azione non può essere annullata.`)) {
      return;
    }

    try {
      await deleteScene(bookId, sceneId);
      toast.success(`Scena ${sceneNumber} eliminata`);
      
      const scenesData = await getBookScenes(bookId);
      setScenes(scenesData);
      
      // Select another scene or clear
      if (selectedScene?.id === sceneId) {
        if (scenesData.length > 0) {
          setSelectedScene(scenesData[0]);
          setEditorContent(scenesData[0].text?.html || '');
        } else {
          setSelectedScene(null);
          setEditorContent('');
        }
      }
      
      // Update book scene count
      if (book) {
        setBook({ ...book, sceneCount: Math.max(0, (book.sceneCount || 1) - 1) });
      }
    } catch (error) {
      console.error('Error deleting scene:', error);
      toast.error('Errore nell\'eliminazione');
    }
  };

  const handleUploadImage = async (type, file) => {
    if (!selectedScene) return;

    setUploading(prev => ({ ...prev, [type]: true }));
    try {
      if (type === 'colored') {
        await uploadSceneColoredImage(bookId, selectedScene.id, file);
      } else {
        await uploadSceneLineartImage(bookId, selectedScene.id, file);
      }
      toast.success(`Immagine ${type === 'colored' ? 'colorata' : 'line art'} caricata`);
      
      // Refresh scenes
      const scenesData = await getBookScenes(bookId);
      setScenes(scenesData);
      const updated = scenesData.find(s => s.id === selectedScene.id);
      if (updated) {
        setSelectedScene(updated);
      }
    } catch (error) {
      console.error('Error uploading image:', error);
      if (error.response?.status === 400) {
        toast.error('Formato file non valido. Usa JPG, JPEG o PNG.');
      } else {
        toast.error('Errore nel caricamento');
      }
    } finally {
      setUploading(prev => ({ ...prev, [type]: false }));
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
    <div className="min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link to="/admin/books">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Torna ai Libri
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{book?.title}</h1>
            <p className="text-gray-500 text-sm">Editor Scene • {scenes.length}/{MAX_SCENES} scene</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={() => setPreviewOpen(true)}
            disabled={!selectedScene}
          >
            <Eye className="w-4 h-4 mr-2" />
            Anteprima
          </Button>
          <Button 
            onClick={handleCreateScene}
            disabled={scenes.length >= MAX_SCENES}
            className="bg-pink-500 hover:bg-pink-600"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nuova Scena
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Scene List Sidebar */}
        <div className="col-span-3">
          <Card>
            <CardContent className="p-4">
              <h3 className="font-semibold text-gray-700 mb-3">Scene</h3>
              {scenes.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-4">
                  Nessuna scena.<br/>Crea la prima!
                </p>
              ) : (
                <div className="space-y-2">
                  {scenes.sort((a, b) => a.sceneNumber - b.sceneNumber).map((scene) => (
                    <div
                      key={scene.id}
                      className={`p-3 rounded-lg cursor-pointer transition-all ${
                        selectedScene?.id === scene.id
                          ? 'bg-pink-100 border-2 border-pink-300'
                          : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                      }`}
                      onClick={() => handleSelectScene(scene)}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium">Scena {scene.sceneNumber}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-red-500 hover:text-red-600 hover:bg-red-50"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteScene(scene.id, scene.sceneNumber);
                          }}
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                      <div className="flex gap-1 mt-2">
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${scene.coloredImageFileId ? 'border-green-300 text-green-600' : 'border-gray-200 text-gray-400'}`}
                        >
                          {scene.coloredImageFileId ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                          <span className="ml-1">Color</span>
                        </Badge>
                        <Badge 
                          variant="outline" 
                          className={`text-xs ${scene.lineArtImageFileId ? 'border-green-300 text-green-600' : 'border-gray-200 text-gray-400'}`}
                        >
                          {scene.lineArtImageFileId ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                          <span className="ml-1">Line</span>
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Editor Area */}
        <div className="col-span-9">
          {selectedScene ? (
            <div className="space-y-6">
              {/* Text Editor */}
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <Label className="text-lg font-semibold">
                      Testo Scena {selectedScene.sceneNumber}
                    </Label>
                    <Button
                      onClick={handleSaveText}
                      disabled={saving}
                      className="bg-green-500 hover:bg-green-600"
                    >
                      {saving ? (
                        <>
                          <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2" />
                          Salvataggio...
                        </>
                      ) : (
                        <>
                          <Save className="w-4 h-4 mr-2" />
                          Salva Testo
                        </>
                      )}
                    </Button>
                  </div>
                  <SceneTextEditor
                    content={editorContent}
                    onChange={setEditorContent}
                    placeholder="Scrivi il testo della scena..."
                  />
                </CardContent>
              </Card>

              {/* Image Uploads */}
              <div className="grid grid-cols-2 gap-4">
                {/* Colored Image */}
                <Card>
                  <CardContent className="p-4">
                    <Label className="flex items-center gap-2 mb-3">
                      <Image className="w-4 h-4 text-pink-500" />
                      Immagine Colorata (sfondo tenue)
                    </Label>
                    <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                      {selectedScene.coloredImageFileId ? (
                        <div>
                          <img
                            src={`${BACKEND_URL}/api/books/${bookId}/scene/${selectedScene.sceneNumber}/colored-image`}
                            alt="Colored"
                            className="w-full h-40 object-contain rounded mb-2"
                          />
                          <p className="text-xs text-green-600">Immagine presente</p>
                        </div>
                      ) : (
                        <div className="py-4">
                          <Image className="w-12 h-12 mx-auto text-gray-300 mb-2" />
                          <p className="text-sm text-gray-400">Nessuna immagine</p>
                        </div>
                      )}
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png"
                        onChange={(e) => e.target.files[0] && handleUploadImage('colored', e.target.files[0])}
                        className="hidden"
                        id="upload-colored"
                        disabled={uploading.colored}
                      />
                      <label
                        htmlFor="upload-colored"
                        className={`inline-flex items-center px-4 py-2 mt-3 rounded-lg cursor-pointer transition-colors ${
                          uploading.colored
                            ? 'bg-gray-100 text-gray-400'
                            : 'bg-pink-50 text-pink-600 hover:bg-pink-100'
                        }`}
                      >
                        {uploading.colored ? (
                          <>
                            <div className="animate-spin w-4 h-4 border-2 border-pink-500 border-t-transparent rounded-full mr-2" />
                            Caricamento...
                          </>
                        ) : (
                          <>
                            <Upload className="w-4 h-4 mr-2" />
                            {selectedScene.coloredImageFileId ? 'Sostituisci' : 'Carica'}
                          </>
                        )}
                      </label>
                    </div>
                  </CardContent>
                </Card>

                {/* Line Art Image */}
                <Card>
                  <CardContent className="p-4">
                    <Label className="flex items-center gap-2 mb-3">
                      <Image className="w-4 h-4 text-gray-600" />
                      Immagine Line Art (da colorare)
                    </Label>
                    <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                      {selectedScene.lineArtImageFileId ? (
                        <div>
                          <img
                            src={`${BACKEND_URL}/api/books/${bookId}/scene/${selectedScene.sceneNumber}/lineart-image`}
                            alt="Line Art"
                            className="w-full h-40 object-contain rounded mb-2"
                          />
                          <p className="text-xs text-green-600">Immagine presente</p>
                        </div>
                      ) : (
                        <div className="py-4">
                          <Image className="w-12 h-12 mx-auto text-gray-300 mb-2" />
                          <p className="text-sm text-gray-400">Nessuna immagine</p>
                        </div>
                      )}
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png"
                        onChange={(e) => e.target.files[0] && handleUploadImage('lineart', e.target.files[0])}
                        className="hidden"
                        id="upload-lineart"
                        disabled={uploading.lineart}
                      />
                      <label
                        htmlFor="upload-lineart"
                        className={`inline-flex items-center px-4 py-2 mt-3 rounded-lg cursor-pointer transition-colors ${
                          uploading.lineart
                            ? 'bg-gray-100 text-gray-400'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {uploading.lineart ? (
                          <>
                            <div className="animate-spin w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full mr-2" />
                            Caricamento...
                          </>
                        ) : (
                          <>
                            <Upload className="w-4 h-4 mr-2" />
                            {selectedScene.lineArtImageFileId ? 'Sostituisci' : 'Carica'}
                          </>
                        )}
                      </label>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="p-12 text-center">
                <div className="text-6xl mb-4">📖</div>
                <p className="text-gray-500 text-lg mb-2">Seleziona o crea una scena</p>
                <p className="text-gray-400 text-sm">Ogni libro può avere fino a {MAX_SCENES} scene</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-5xl">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Anteprima Scena {selectedScene?.sceneNumber}</span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!selectedScene || selectedScene.sceneNumber <= 1}
                  onClick={() => {
                    const prev = scenes.find(s => s.sceneNumber === selectedScene.sceneNumber - 1);
                    if (prev) {
                      setSelectedScene(prev);
                      setEditorContent(prev.text?.html || '');
                    }
                  }}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!selectedScene || selectedScene.sceneNumber >= scenes.length}
                  onClick={() => {
                    const next = scenes.find(s => s.sceneNumber === selectedScene.sceneNumber + 1);
                    if (next) {
                      setSelectedScene(next);
                      setEditorContent(next.text?.html || '');
                    }
                  }}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </DialogTitle>
          </DialogHeader>
          
          {selectedScene && (
            <div className="mt-4">
              {/* Desktop: Side by Side */}
              <div className="hidden md:grid grid-cols-2 gap-4 min-h-[400px]">
                {/* Left Page: Text + Faint Background */}
                <div 
                  className="relative rounded-lg overflow-hidden border-2 border-gray-200 p-6"
                  style={{
                    backgroundImage: selectedScene.coloredImageFileId 
                      ? `url(${BACKEND_URL}/api/books/${bookId}/scene/${selectedScene.sceneNumber}/colored-image)`
                      : 'none',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  }}
                >
                  {/* Overlay for faint effect */}
                  <div className="absolute inset-0 bg-white/85" />
                  {/* Text Content */}
                  <div 
                    className="relative z-10 prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: editorContent || '<p class="text-gray-400 italic">Nessun testo</p>' }}
                  />
                </div>
                
                {/* Right Page: Line Art */}
                <div className="rounded-lg overflow-hidden border-2 border-gray-200 bg-white flex items-center justify-center">
                  {selectedScene.lineArtImageFileId ? (
                    <img
                      src={`${BACKEND_URL}/api/books/${bookId}/scene/${selectedScene.sceneNumber}/lineart-image`}
                      alt="Line Art"
                      className="max-w-full max-h-full object-contain"
                    />
                  ) : (
                    <div className="text-center text-gray-400">
                      <Image className="w-16 h-16 mx-auto mb-2 opacity-30" />
                      <p>Line art non caricata</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Mobile: Stacked */}
              <div className="md:hidden space-y-4">
                {/* Text + Background */}
                <div 
                  className="relative rounded-lg overflow-hidden border-2 border-gray-200 p-4 min-h-[200px]"
                  style={{
                    backgroundImage: selectedScene.coloredImageFileId 
                      ? `url(${BACKEND_URL}/api/books/${bookId}/scene/${selectedScene.sceneNumber}/colored-image)`
                      : 'none',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                  }}
                >
                  <div className="absolute inset-0 bg-white/85" />
                  <div 
                    className="relative z-10 prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: editorContent || '<p class="text-gray-400 italic">Nessun testo</p>' }}
                  />
                </div>
                
                {/* Line Art */}
                <div className="rounded-lg overflow-hidden border-2 border-gray-200 bg-white p-4 min-h-[200px] flex items-center justify-center">
                  {selectedScene.lineArtImageFileId ? (
                    <img
                      src={`${BACKEND_URL}/api/books/${bookId}/scene/${selectedScene.sceneNumber}/lineart-image`}
                      alt="Line Art"
                      className="max-w-full max-h-[200px] object-contain"
                    />
                  ) : (
                    <div className="text-center text-gray-400">
                      <Image className="w-12 h-12 mx-auto mb-2 opacity-30" />
                      <p className="text-sm">Line art non caricata</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminSceneEditor;
