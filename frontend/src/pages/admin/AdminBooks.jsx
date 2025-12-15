import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Edit2, Trash2, Book, Eye, EyeOff, Upload, Image, CheckCircle, XCircle, Search, FileEdit } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { getAdminBooks, createBook, updateBook, deleteBook, uploadBookCover } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminBooks = () => {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingBook, setEditingBook] = useState(null);
  const [uploading, setUploading] = useState(false);
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    isFree: true,
    price: 4.99,
    isVisible: true,
    allowDownload: true
  });

  const fetchBooks = useCallback(async () => {
    try {
      const data = await getAdminBooks();
      setBooks(data);
    } catch (error) {
      console.error('Error fetching books:', error);
      if (error.response?.status === 401) {
        toast.error('Sessione scaduta. Effettua nuovamente il login.');
      } else if (error.response?.status === 403) {
        toast.error('Accesso non autorizzato.');
      } else {
        toast.error('Errore nel caricamento dei libri');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [fetchBooks]);

  const filteredBooks = books.filter(book =>
    book.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    book.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingBook) {
        await updateBook(editingBook.id, formData);
        toast.success('Libro aggiornato!');
      } else {
        await createBook(formData);
        toast.success('Libro creato!');
      }
      resetForm();
      fetchBooks();
    } catch (error) {
      console.error('Error saving book:', error);
      if (error.response?.status === 401) {
        toast.error('Sessione scaduta. Effettua nuovamente il login.');
      } else if (error.response?.status === 403) {
        toast.error('Accesso non autorizzato.');
      } else {
        toast.error('Errore nel salvataggio del libro');
      }
    }
  };

  const handleDelete = async (bookId, bookTitle) => {
    if (!window.confirm(`Sei sicuro di voler eliminare "${bookTitle}"? Verranno eliminate anche tutte le scene associate.`)) {
      return;
    }
    try {
      await deleteBook(bookId);
      toast.success('Libro eliminato');
      fetchBooks();
    } catch (error) {
      console.error('Error deleting book:', error);
      if (error.response?.status === 401) {
        toast.error('Sessione scaduta. Effettua nuovamente il login.');
      } else if (error.response?.status === 403) {
        toast.error('Accesso non autorizzato.');
      } else {
        toast.error('Errore nell\'eliminazione del libro');
      }
    }
  };

  const handleCoverUpload = async (bookId, file) => {
    setUploading(true);
    try {
      await uploadBookCover(bookId, file);
      toast.success('Copertina caricata!');
      fetchBooks();
    } catch (error) {
      console.error('Error uploading cover:', error);
      if (error.response?.status === 401) {
        toast.error('Sessione scaduta. Effettua nuovamente il login.');
      } else if (error.response?.status === 403) {
        toast.error('Accesso non autorizzato.');
      } else if (error.response?.status === 400) {
        toast.error('Formato file non valido. Usa JPG, JPEG o PNG.');
      } else {
        toast.error('Errore nel caricamento della copertina');
      }
    } finally {
      setUploading(false);
    }
  };

  const handleEdit = (book) => {
    setEditingBook(book);
    setFormData({
      title: book.title,
      description: book.description,
      isFree: book.isFree,
      price: book.price || 4.99,
      isVisible: book.isVisible,
      allowDownload: book.allowDownload
    });
    setIsAddOpen(true);
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      isFree: true,
      price: 4.99,
      isVisible: true,
      allowDownload: true
    });
    setEditingBook(null);
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
          <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-3">
            <Book className="w-8 h-8 text-pink-500" />
            Gestione Libri
          </h1>
          <p className="text-gray-600 mt-1">Crea e gestisci i libri illustrati di Pompiconni</p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsAddOpen(true); }}>
          <DialogTrigger asChild>
            <Button className="bg-pink-500 hover:bg-pink-600">
              <Plus className="w-4 h-4 mr-2" />Nuovo Libro
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{editingBook ? 'Modifica Libro' : 'Nuovo Libro'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Titolo</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="es. Le Avventure di Pompiconni"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Descrizione</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Breve descrizione del libro"
                  required
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label>Gratuito</Label>
                  <p className="text-xs text-gray-500">Rendi il libro accessibile gratis</p>
                </div>
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
                    min="0"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
                  />
                </div>
              )}
              <div className="flex items-center justify-between">
                <div>
                  <Label>Visibile</Label>
                  <p className="text-xs text-gray-500">Mostra nel sito pubblico</p>
                </div>
                <Switch
                  checked={formData.isVisible}
                  onCheckedChange={(checked) => setFormData({ ...formData, isVisible: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label>Permetti Download</Label>
                  <p className="text-xs text-gray-500">Consenti download PDF</p>
                </div>
                <Switch
                  checked={formData.allowDownload}
                  onCheckedChange={(checked) => setFormData({ ...formData, allowDownload: checked })}
                />
              </div>
              <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded-lg">
                <p>Dopo aver creato il libro, potrai aggiungere la copertina e le scene dalla card.</p>
              </div>
              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={resetForm} className="flex-1">
                  Annulla
                </Button>
                <Button type="submit" className="flex-1 bg-pink-500 hover:bg-pink-600">
                  {editingBook ? 'Salva' : 'Crea Libro'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="Cerca libri..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Books Grid */}
      {filteredBooks.length === 0 ? (
        <div className="text-center py-20">
          <Book className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">
            {searchTerm ? 'Nessun libro trovato' : 'Nessun libro creato'}
          </p>
          {!searchTerm && <p className="text-gray-400">Crea il primo libro di Pompiconni!</p>}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBooks.map((book) => (
            <Card key={book.id} className="border-2 border-pink-100 hover:shadow-lg transition-shadow overflow-hidden">
              {/* Cover */}
              <div className="relative h-48 bg-gradient-to-br from-pink-100 to-blue-100 flex items-center justify-center group">
                {book.coverImageFileId ? (
                  <img 
                    src={`${BACKEND_URL}/api/books/${book.id}/cover`}
                    alt={book.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="text-center">
                    <div className="text-5xl mb-1">📖</div>
                    <div className="text-3xl">🦄</div>
                  </div>
                )}
                
                {/* Upload cover overlay */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png"
                    onChange={(e) => e.target.files[0] && handleCoverUpload(book.id, e.target.files[0])}
                    className="hidden"
                    id={`cover-${book.id}`}
                    disabled={uploading}
                  />
                  <label 
                    htmlFor={`cover-${book.id}`}
                    className="cursor-pointer bg-white text-pink-500 px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-pink-50"
                  >
                    <Upload className="w-4 h-4" />
                    {uploading ? 'Caricamento...' : 'Carica Copertina'}
                  </label>
                </div>

                {/* Status badges */}
                <div className="absolute top-2 left-2 flex gap-2">
                  {book.isFree ? (
                    <Badge className="bg-green-500 text-white">Gratis</Badge>
                  ) : (
                    <Badge className="bg-pink-500 text-white">€{book.price?.toFixed(2)}</Badge>
                  )}
                </div>
                <div className="absolute top-2 right-2">
                  {book.isVisible ? (
                    <Badge variant="secondary" className="bg-white/90"><Eye className="w-3 h-3 mr-1" />Visibile</Badge>
                  ) : (
                    <Badge variant="secondary" className="bg-gray-200"><EyeOff className="w-3 h-3 mr-1" />Nascosto</Badge>
                  )}
                </div>
              </div>

              <CardContent className="p-4">
                {/* File status */}
                <div className="flex gap-2 mb-3">
                  <Badge 
                    variant="outline" 
                    className={book.coverImageFileId ? 'border-green-300 text-green-600' : 'border-gray-300 text-gray-400'}
                  >
                    <Image className="w-3 h-3 mr-1" />
                    {book.coverImageFileId ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                  </Badge>
                  <Badge variant="outline" className="border-blue-300 text-blue-600">
                    {book.sceneCount || 0}/15 scene
                  </Badge>
                </div>

                <h3 className="font-bold text-lg text-gray-800 mb-1 line-clamp-1">{book.title}</h3>
                <p className="text-sm text-gray-600 mb-4 line-clamp-2">{book.description}</p>
                
                <div className="flex items-center justify-between pt-3 border-t">
                  <div className="text-xs text-gray-400">
                    {book.viewCount || 0} visualizzazioni • {book.downloadCount || 0} download
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => handleEdit(book)} title="Modifica">
                      <Edit2 className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-red-500 hover:text-red-600 hover:bg-red-50"
                      onClick={() => handleDelete(book.id, book.title)}
                      title="Elimina"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default AdminBooks;
