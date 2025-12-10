import React, { useState } from 'react';
import { Plus, Search, Edit2, Trash2, Upload, X, Filter } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { themes, illustrations as mockIllustrations } from '../../data/mock';
import { toast } from 'sonner';

const AdminIllustrations = () => {
  const [illustrations, setIllustrations] = useState(mockIllustrations);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTheme, setFilterTheme] = useState('all');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingIllustration, setEditingIllustration] = useState(null);
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    themeId: '',
    isFree: true
  });

  const filteredIllustrations = illustrations.filter(i => {
    const matchesSearch = i.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTheme = filterTheme === 'all' || i.themeId === filterTheme;
    return matchesSearch && matchesTheme;
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (editingIllustration) {
      setIllustrations(prev => prev.map(i => 
        i.id === editingIllustration.id ? { ...i, ...formData } : i
      ));
      toast.success('Illustrazione aggiornata!');
    } else {
      const newIllustration = {
        id: Date.now(),
        ...formData,
        downloadCount: 0
      };
      setIllustrations(prev => [...prev, newIllustration]);
      toast.success('Illustrazione aggiunta!');
    }
    resetForm();
  };

  const handleDelete = (id) => {
    setIllustrations(prev => prev.filter(i => i.id !== id));
    toast.success('Illustrazione eliminata!');
  };

  const handleEdit = (illustration) => {
    setEditingIllustration(illustration);
    setFormData({
      title: illustration.title,
      description: illustration.description,
      themeId: illustration.themeId,
      isFree: illustration.isFree
    });
    setIsAddOpen(true);
  };

  const resetForm = () => {
    setFormData({ title: '', description: '', themeId: '', isFree: true });
    setEditingIllustration(null);
    setIsAddOpen(false);
  };

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
              <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center">
                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                <p className="text-sm text-gray-500">Carica file (PNG, PDF)</p>
                <p className="text-xs text-gray-400 mt-1">Funzionalità in arrivo</p>
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
              <div className="h-32 bg-gray-100 rounded-lg flex items-center justify-center mb-3">
                <span className="text-4xl opacity-30">🦄</span>
              </div>
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-800 truncate">{illustration.title}</h3>
                  <p className="text-xs text-gray-500">{themes.find(t => t.id === illustration.themeId)?.name}</p>
                </div>
                <Badge className={illustration.isFree ? 'bg-green-100 text-green-700' : 'bg-pink-100 text-pink-700'}>
                  {illustration.isFree ? 'Gratis' : 'Premium'}
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
