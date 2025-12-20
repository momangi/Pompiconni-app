import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Gamepad2, GripVertical, Upload, Check, X, Eye, EyeOff } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { getAdminGames, createGame, updateGame, deleteGame, uploadGameThumbnail } from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminGames = () => {
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingGame, setEditingGame] = useState(null);
  const [uploading, setUploading] = useState(false);
  
  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    shortDescription: '',
    longDescription: '',
    status: 'coming_soon',
    ageRecommended: '3+',
    howToPlay: ['', '', ''],
    sortOrder: 0
  });

  useEffect(() => {
    fetchGames();
  }, []);

  const fetchGames = async () => {
    try {
      const data = await getAdminGames();
      setGames(data);
    } catch (error) {
      console.error('Error fetching games:', error);
      // Fallback data
      setGames([
        { id: '1', slug: 'bolle-magiche', title: 'Bolle Magiche', shortDescription: 'Scoppia le bolle colorate!', status: 'available', sortOrder: 1 },
        { id: '2', slug: 'puzzle-poppiconni', title: 'Puzzle Poppiconni', shortDescription: 'Ricomponi le immagini!', status: 'coming_soon', sortOrder: 2 },
        { id: '3', slug: 'memory-poppiconni', title: 'Memory Poppiconni', shortDescription: 'Trova le coppie!', status: 'coming_soon', sortOrder: 3 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const generateSlug = (title) => {
    return title
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .trim();
  };

  const handleTitleChange = (value) => {
    setFormData(prev => ({
      ...prev,
      title: value,
      slug: editingGame ? prev.slug : generateSlug(value)
    }));
  };

  const handleHowToPlayChange = (index, value) => {
    setFormData(prev => {
      const newHowToPlay = [...prev.howToPlay];
      newHowToPlay[index] = value;
      return { ...prev, howToPlay: newHowToPlay };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const gameData = {
      ...formData,
      howToPlay: formData.howToPlay.filter(step => step.trim() !== '')
    };
    
    try {
      if (editingGame) {
        await updateGame(editingGame.id, gameData);
        toast.success('Gioco aggiornato!');
      } else {
        await createGame(gameData);
        toast.success('Gioco creato!');
      }
      resetForm();
      fetchGames();
    } catch (error) {
      toast.error('Errore nel salvataggio');
    }
  };

  const handleDelete = async (gameId) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo gioco?')) return;
    
    try {
      await deleteGame(gameId);
      toast.success('Gioco eliminato!');
      fetchGames();
    } catch (error) {
      toast.error('Errore nell\'eliminazione');
    }
  };

  const handleThumbnailUpload = async (gameId, e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    setUploading(true);
    try {
      await uploadGameThumbnail(gameId, file);
      toast.success('Thumbnail caricata!');
      fetchGames();
    } catch (error) {
      toast.error('Errore nel caricamento');
    } finally {
      setUploading(false);
    }
  };

  const handleEdit = (game) => {
    setEditingGame(game);
    setFormData({
      title: game.title,
      slug: game.slug,
      shortDescription: game.shortDescription || '',
      longDescription: game.longDescription || '',
      status: game.status || 'coming_soon',
      ageRecommended: game.ageRecommended || '3+',
      howToPlay: game.howToPlay || ['', '', ''],
      sortOrder: game.sortOrder || 0
    });
    setIsAddOpen(true);
  };

  const resetForm = () => {
    setFormData({
      title: '',
      slug: '',
      shortDescription: '',
      longDescription: '',
      status: 'coming_soon',
      ageRecommended: '3+',
      howToPlay: ['', '', ''],
      sortOrder: 0
    });
    setEditingGame(null);
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
            <Gamepad2 className="w-8 h-8 text-purple-500" />
            Gestione Giochi
          </h1>
          <p className="text-gray-600 mt-1">Crea e gestisci i giochi di Poppiconni</p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={(open) => { if (!open) resetForm(); else setIsAddOpen(true); }}>
          <DialogTrigger asChild>
            <Button className="bg-purple-500 hover:bg-purple-600">
              <Plus className="w-4 h-4 mr-2" />Nuovo Gioco
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>{editingGame ? 'Modifica Gioco' : 'Nuovo Gioco'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Titolo *</Label>
                  <Input
                    value={formData.title}
                    onChange={(e) => handleTitleChange(e.target.value)}
                    placeholder="es. Bolle Magiche"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Slug *</Label>
                  <Input
                    value={formData.slug}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                    placeholder="es. bolle-magiche"
                    required
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Descrizione Breve</Label>
                <Input
                  value={formData.shortDescription}
                  onChange={(e) => setFormData({ ...formData, shortDescription: e.target.value })}
                  placeholder="1-2 righe di descrizione"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Descrizione Completa</Label>
                <Textarea
                  value={formData.longDescription}
                  onChange={(e) => setFormData({ ...formData, longDescription: e.target.value })}
                  placeholder="Descrizione dettagliata del gioco"
                  rows={3}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Stato</Label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="available">Disponibile</option>
                    <option value="coming_soon">In arrivo</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Età Consigliata</Label>
                  <Input
                    value={formData.ageRecommended}
                    onChange={(e) => setFormData({ ...formData, ageRecommended: e.target.value })}
                    placeholder="es. 3+"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Come si gioca (3 punti)</Label>
                {[0, 1, 2].map(i => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="w-6 h-6 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-sm font-bold">{i + 1}</span>
                    <Input
                      value={formData.howToPlay[i] || ''}
                      onChange={(e) => handleHowToPlayChange(i, e.target.value)}
                      placeholder={`Passo ${i + 1}`}
                    />
                  </div>
                ))}
              </div>
              
              <div className="space-y-2">
                <Label>Ordine (numero)</Label>
                <Input
                  type="number"
                  value={formData.sortOrder}
                  onChange={(e) => setFormData({ ...formData, sortOrder: parseInt(e.target.value) || 0 })}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <Button type="button" variant="outline" onClick={resetForm} className="flex-1">
                  Annulla
                </Button>
                <Button type="submit" className="flex-1 bg-purple-500 hover:bg-purple-600">
                  {editingGame ? 'Salva Modifiche' : 'Crea Gioco'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Games List */}
      <div className="space-y-4">
        {games.length === 0 ? (
          <div className="text-center py-16">
            <Gamepad2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 text-lg">Nessun gioco creato</p>
            <p className="text-gray-400">Crea il primo gioco per iniziare</p>
          </div>
        ) : (
          games.map((game) => (
            <Card key={game.id} className="border-2 hover:shadow-lg transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  {/* Thumbnail */}
                  <div className="w-24 h-24 rounded-xl overflow-hidden bg-gradient-to-br from-purple-100 to-pink-100 flex-shrink-0 relative group">
                    {game.thumbnailUrl ? (
                      <img 
                        src={`${BACKEND_URL}${game.thumbnailUrl}`}
                        alt={game.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Gamepad2 className="w-10 h-10 text-purple-300" />
                      </div>
                    )}
                    {/* Upload overlay */}
                    <label className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer flex items-center justify-center">
                      <Upload className="w-6 h-6 text-white" />
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => handleThumbnailUpload(game.id, e)}
                        disabled={uploading}
                      />
                    </label>
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="font-bold text-lg text-gray-800">{game.title}</h3>
                      {game.status === 'available' ? (
                        <Badge className="bg-green-100 text-green-700 border-green-200">
                          <Eye className="w-3 h-3 mr-1" />
                          Disponibile
                        </Badge>
                      ) : (
                        <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                          <EyeOff className="w-3 h-3 mr-1" />
                          In arrivo
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mb-1">/{game.slug}</p>
                    <p className="text-sm text-gray-600 line-clamp-1">{game.shortDescription}</p>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => handleEdit(game)}>
                      <Edit2 className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-red-500 hover:text-red-600 hover:bg-red-50"
                      onClick={() => handleDelete(game.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
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

export default AdminGames;
