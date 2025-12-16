import React, { useState, useEffect, useRef } from 'react';
import { 
  Wand2, Download, RefreshCw, Sparkles, Image as ImageIcon, Save, 
  Plus, Trash2, Upload, CheckCircle, XCircle, AlertTriangle, 
  Layers, Eye, Palette, Settings2, Clock, ChevronDown, ChevronUp
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Input } from '../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Switch } from '../../components/ui/switch';
import { 
  getThemes, 
  getGenerationStyles, 
  createGenerationStyle, 
  deleteGenerationStyle, 
  uploadStyleReference,
  generatePoppiconni,
  getPipelineStatus
} from '../../services/api';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Pipeline status badge component
const StatusBadge = ({ status }) => {
  const statusConfig = {
    pending: { color: 'bg-gray-100 text-gray-600', icon: Clock, text: 'In attesa' },
    phase1_prompt: { color: 'bg-blue-100 text-blue-600', icon: Sparkles, text: 'Fase 1: Prompt' },
    phase2_generation: { color: 'bg-purple-100 text-purple-600', icon: Wand2, text: 'Fase 2: Generazione' },
    phase3_qc: { color: 'bg-yellow-100 text-yellow-600', icon: Eye, text: 'Fase 3: Quality Check' },
    phase4_postprod: { color: 'bg-orange-100 text-orange-600', icon: Palette, text: 'Fase 4: Post-produzione' },
    completed: { color: 'bg-green-100 text-green-600', icon: CheckCircle, text: 'Completato' },
    low_confidence: { color: 'bg-amber-100 text-amber-600', icon: AlertTriangle, text: 'Bassa Confidenza' },
    failed: { color: 'bg-red-100 text-red-600', icon: XCircle, text: 'Fallito' },
    async_retry: { color: 'bg-indigo-100 text-indigo-600', icon: RefreshCw, text: 'Retry Asincrono' }
  };

  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.text}
    </span>
  );
};

// QC Report Component
const QCReport = ({ report }) => {
  if (!report) return null;

  const checks = [
    { key: 'popcorn_bucket_present', label: 'Barattolo Popcorn', passed: report.popcorn_bucket_present },
    { key: 'poppiconni_text_readable', label: 'Scritta "POPPICONNI" Leggibile', passed: report.poppiconni_text_readable },
    { key: 'lineart_style_ok', label: 'Stile Line-art', passed: report.lineart_style_ok },
    { key: 'colorability_ok', label: 'Colorabilità', passed: report.colorability_ok },
    { key: 'no_forbidden_content', label: 'Nessun Contenuto Vietato', passed: report.no_forbidden_content }
  ];

  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">Quality Check</span>
        <span className="text-sm text-gray-500">
          Confidenza: {(report.confidence_score * 100).toFixed(0)}%
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {checks.map(check => (
          <div key={check.key} className="flex items-center gap-1.5 text-xs">
            {check.passed ? (
              <CheckCircle className="w-3.5 h-3.5 text-green-500" />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-red-500" />
            )}
            <span className={check.passed ? 'text-green-700' : 'text-red-700'}>
              {check.label}
            </span>
          </div>
        ))}
      </div>
      {report.issues && report.issues.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <span className="text-xs font-medium text-gray-600">Problemi:</span>
          <ul className="mt-1 text-xs text-red-600 list-disc list-inside">
            {report.issues.map((issue, idx) => (
              <li key={idx}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// Style Library Card Component
const StyleCard = ({ style, onDelete, onUpload }) => {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await onUpload(style.id, file);
      toast.success('Immagine di riferimento caricata');
    } catch (error) {
      toast.error('Errore nel caricamento');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="border rounded-lg p-3 bg-white hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-medium text-sm text-gray-800">{style.styleName}</h4>
          {style.description && (
            <p className="text-xs text-gray-500 line-clamp-1">{style.description}</p>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={() => onDelete(style.id)}>
          <Trash2 className="w-4 h-4 text-red-500" />
        </Button>
      </div>
      
      <div className="h-24 bg-gray-100 rounded overflow-hidden mb-2">
        {style.referenceImageUrl ? (
          <img 
            src={`${BACKEND_URL}${style.referenceImageUrl}`} 
            alt={style.styleName}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <ImageIcon className="w-8 h-8" />
          </div>
        )}
      </div>
      
      <input
        ref={fileInputRef}
        type="file"
        accept=".jpg,.jpeg,.png"
        onChange={handleUpload}
        className="hidden"
      />
      <Button 
        variant="outline" 
        size="sm" 
        className="w-full"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
      >
        {uploading ? (
          <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
        ) : (
          <Upload className="w-4 h-4 mr-1" />
        )}
        {style.referenceImageUrl ? 'Cambia Immagine' : 'Carica Riferimento'}
      </Button>
    </div>
  );
};

const AdminGenerator = () => {
  // Form state
  const [userRequest, setUserRequest] = useState('');
  const [selectedTheme, setSelectedTheme] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('');
  const [styleLock, setStyleLock] = useState(false);
  const [saveToGallery, setSaveToGallery] = useState(true);
  
  // Data state
  const [themes, setThemes] = useState([]);
  const [styles, setStyles] = useState([]);
  const [stylesLimit, setStylesLimit] = useState(20);
  
  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedResults, setGeneratedResults] = useState([]);
  
  // UI state
  const [showStyleLibrary, setShowStyleLibrary] = useState(false);
  const [newStyleName, setNewStyleName] = useState('');
  const [newStyleDesc, setNewStyleDesc] = useState('');

  // Load themes and styles
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [themesData, stylesData] = await Promise.all([
          getThemes(),
          getGenerationStyles()
        ]);
        setThemes(themesData);
        setStyles(stylesData.styles || []);
        setStylesLimit(stylesData.limit || 20);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };
    fetchData();
  }, []);

  const promptTemplates = [
    'Poppiconni come pompiere che salva un gattino',
    'Poppiconni in fattoria che accarezza una pecora',
    'Poppiconni allo zoo che guarda le giraffe',
    'Poppiconni che gioca a calcio nel parco',
    'Poppiconni d\'inverno che costruisce un pupazzo di neve',
    'Poppiconni a scuola che legge un libro',
    'Poppiconni cuoco che prepara una torta',
    'Poppiconni astronauta sulla luna'
  ];

  const handleCreateStyle = async () => {
    if (!newStyleName.trim()) {
      toast.error('Inserisci un nome per lo stile');
      return;
    }

    try {
      const result = await createGenerationStyle({
        styleName: newStyleName,
        description: newStyleDesc,
        isActive: true
      });
      setStyles(prev => [...prev, result.style]);
      setNewStyleName('');
      setNewStyleDesc('');
      toast.success('Stile creato! Ora carica un\'immagine di riferimento.');
    } catch (error) {
      toast.error('Errore nella creazione dello stile');
    }
  };

  const handleDeleteStyle = async (styleId) => {
    if (!window.confirm('Eliminare questo stile?')) return;
    
    try {
      await deleteGenerationStyle(styleId);
      setStyles(prev => prev.filter(s => s.id !== styleId));
      if (selectedStyle === styleId) setSelectedStyle('');
      toast.success('Stile eliminato');
    } catch (error) {
      toast.error('Errore nell\'eliminazione');
    }
  };

  const handleUploadReference = async (styleId, file) => {
    await uploadStyleReference(styleId, file);
    // Refresh styles
    const stylesData = await getGenerationStyles();
    setStyles(stylesData.styles || []);
  };

  const handleGenerate = async () => {
    if (!userRequest.trim()) {
      toast.error('Descrivi la scena che vuoi creare');
      return;
    }

    setIsGenerating(true);
    toast.info('Pipeline Multi-AI avviata... può richiedere 1-2 minuti');

    try {
      const result = await generatePoppiconni(userRequest, {
        styleId: selectedStyle || null,
        styleLock: styleLock,
        saveToGallery: saveToGallery,
        themeId: selectedTheme && selectedTheme !== 'none' ? selectedTheme : null
      });

      const newResult = {
        id: result.generation_id,
        userRequest: userRequest,
        timestamp: new Date().toISOString(),
        ...result
      };

      setGeneratedResults(prev => [newResult, ...prev]);
      
      if (result.success) {
        if (result.qc_passed) {
          toast.success('🎉 Illustrazione generata con successo! QC superato!');
        } else {
          toast.warning('⚠️ Illustrazione generata, ma QC non completamente superato. Retry in corso...');
        }
      } else {
        toast.error('Generazione fallita: ' + result.message);
      }
    } catch (error) {
      console.error('Generation error:', error);
      toast.error('Errore: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = (result) => {
    if (result.thumbnail_base64) {
      const link = document.createElement('a');
      link.href = `data:image/png;base64,${result.thumbnail_base64}`;
      link.download = `poppiconni_${result.generation_id?.slice(0, 8) || Date.now()}.png`;
      link.click();
      toast.success('Anteprima scaricata!');
    } else if (result.illustration_id) {
      window.open(`${BACKEND_URL}/api/illustrations/${result.illustration_id}/image`, '_blank');
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
          <Wand2 className="w-8 h-8 text-pink-500" />
          Generatore Multi-AI Poppiconni
        </h1>
        <p className="text-gray-600">
          Pipeline automatica a 4 fasi: Prompt Engineering → Generazione → Quality Check → Post-Produzione
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Generator Form */}
        <div className="lg:col-span-1 space-y-6">
          {/* Main Generation Card */}
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-pink-500" />
                Nuova Generazione
              </CardTitle>
              <CardDescription>
                Descrivi la scena in linguaggio naturale. La pipeline AI ottimizzerà il prompt.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Descrivi la Scena</Label>
                <Textarea
                  value={userRequest}
                  onChange={(e) => setUserRequest(e.target.value)}
                  placeholder="Es: Poppiconni come astronauta che esplora la luna con il suo amico robot..."
                  rows={4}
                  className="resize-none"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-gray-500">Template Rapidi</Label>
                <div className="flex flex-wrap gap-1.5">
                  {promptTemplates.slice(0, 4).map((template, idx) => (
                    <button
                      key={idx}
                      onClick={() => setUserRequest(template)}
                      className="text-xs px-2.5 py-1 bg-gray-100 hover:bg-pink-100 text-gray-600 hover:text-pink-600 rounded-full transition-colors"
                    >
                      {template.slice(0, 25)}...
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label>Tema (per organizzazione galleria)</Label>
                <Select value={selectedTheme} onValueChange={setSelectedTheme}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleziona un tema" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Nessun tema</SelectItem>
                    {themes.map(theme => (
                      <SelectItem key={theme.id} value={theme.id}>{theme.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {styles.length > 0 && (
                <div className="space-y-2">
                  <Label>Stile di Riferimento</Label>
                  <Select value={selectedStyle || "none"} onValueChange={(val) => setSelectedStyle(val === "none" ? "" : val)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Nessuno stile" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Nessuno stile</SelectItem>
                      {styles.filter(s => s.referenceImageFileId).map(style => (
                        <SelectItem key={style.id} value={style.id}>{style.styleName}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {selectedStyle && (
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Settings2 className="w-4 h-4 text-gray-500" />
                    <span className="text-sm text-gray-700">Style Lock</span>
                  </div>
                  <Switch checked={styleLock} onCheckedChange={setStyleLock} />
                </div>
              )}

              <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <Save className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-700">Salva in Galleria</span>
                </div>
                <Switch checked={saveToGallery} onCheckedChange={setSaveToGallery} />
              </div>

              <Button 
                className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600"
                onClick={handleGenerate}
                disabled={isGenerating}
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Pipeline in corso...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4 mr-2" />
                    Genera con Pipeline Multi-AI
                  </>
                )}
              </Button>

              <div className="text-xs text-gray-500 text-center">
                4 fasi AI: GPT-4o (prompt) → gpt-image-1 → GPT-4o Vision (QC) → Pillow (300 DPI)
              </div>
            </CardContent>
          </Card>

          {/* Style Library Collapsible */}
          <Card className="border-0 shadow-lg">
            <CardHeader 
              className="cursor-pointer"
              onClick={() => setShowStyleLibrary(!showStyleLibrary)}
            >
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Layers className="w-5 h-5 text-purple-500" />
                  Libreria Stili ({styles.length}/{stylesLimit})
                </span>
                {showStyleLibrary ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </CardTitle>
            </CardHeader>
            
            {showStyleLibrary && (
              <CardContent className="space-y-4">
                {/* Add New Style */}
                <div className="p-3 border border-dashed rounded-lg space-y-2">
                  <Input
                    placeholder="Nome stile..."
                    value={newStyleName}
                    onChange={(e) => setNewStyleName(e.target.value)}
                  />
                  <Input
                    placeholder="Descrizione (opzionale)..."
                    value={newStyleDesc}
                    onChange={(e) => setNewStyleDesc(e.target.value)}
                  />
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full"
                    onClick={handleCreateStyle}
                    disabled={styles.length >= stylesLimit}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Aggiungi Stile
                  </Button>
                </div>

                {/* Style Cards */}
                <div className="grid gap-3">
                  {styles.map(style => (
                    <StyleCard
                      key={style.id}
                      style={style}
                      onDelete={handleDeleteStyle}
                      onUpload={handleUploadReference}
                    />
                  ))}
                </div>

                {styles.length === 0 && (
                  <p className="text-sm text-gray-500 text-center py-4">
                    Nessuno stile salvato. Crea il tuo primo stile!
                  </p>
                )}
              </CardContent>
            )}
          </Card>
        </div>

        {/* Generated Results */}
        <div className="lg:col-span-2">
          <h2 className="text-xl font-bold text-gray-800 mb-4">Risultati Pipeline</h2>
          
          {generatedResults.length === 0 ? (
            <Card className="border-2 border-dashed border-gray-200">
              <CardContent className="py-16 text-center">
                <ImageIcon className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-500 mb-2">Nessuna generazione ancora</p>
                <p className="text-sm text-gray-400">
                  Usa il form a sinistra per avviare la pipeline Multi-AI
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {generatedResults.map((result) => (
                <Card key={result.id} className="border-0 shadow-lg overflow-hidden">
                  {/* Image Preview */}
                  <div className="h-56 bg-gradient-to-br from-pink-50 to-blue-50 flex items-center justify-center relative">
                    {result.thumbnail_base64 ? (
                      <img 
                        src={`data:image/png;base64,${result.thumbnail_base64}`} 
                        alt="Generated" 
                        className="w-full h-full object-contain"
                      />
                    ) : result.illustration_id ? (
                      <img 
                        src={`${BACKEND_URL}/api/illustrations/${result.illustration_id}/image`} 
                        alt="Generated" 
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="text-center">
                        <div className="text-6xl mb-2">🦄</div>
                        <p className="text-xs text-gray-400">In elaborazione...</p>
                      </div>
                    )}
                    
                    {/* Status Badge Overlay */}
                    <div className="absolute top-2 right-2">
                      <StatusBadge status={result.status} />
                    </div>
                  </div>
                  
                  <CardContent className="p-4">
                    {/* Request */}
                    <p className="text-sm text-gray-700 mb-2 line-clamp-2">
                      {result.userRequest}
                    </p>
                    
                    {/* Optimized Prompt (collapsible) */}
                    {result.optimized_prompt && (
                      <details className="mb-2">
                        <summary className="text-xs text-purple-600 cursor-pointer hover:text-purple-800">
                          Prompt ottimizzato
                        </summary>
                        <p className="text-xs text-gray-500 mt-1 bg-gray-50 p-2 rounded">
                          {result.optimized_prompt.slice(0, 200)}...
                        </p>
                      </details>
                    )}
                    
                    {/* Info Row */}
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-3">
                      <span>Tentativi: {result.retry_count}</span>
                      <span>{new Date(result.timestamp).toLocaleTimeString()}</span>
                    </div>
                    
                    {/* QC Report */}
                    {result.qc_report && <QCReport report={result.qc_report} />}
                    
                    {/* Saved Notice */}
                    {result.illustration_id && (
                      <p className="text-xs text-green-600 mt-3">
                        <Save className="w-3 h-3 inline mr-1" />
                        Salvato in galleria (ID: {result.illustration_id.slice(0, 8)}...)
                      </p>
                    )}
                    
                    {/* Actions */}
                    <div className="flex gap-2 mt-3">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1" 
                        onClick={() => handleDownload(result)}
                        disabled={!result.has_final_image && !result.thumbnail_base64}
                      >
                        <Download className="w-4 h-4 mr-1" />
                        Scarica
                      </Button>
                      {result.illustration_id && (
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => window.open(`${BACKEND_URL}/api/illustrations/${result.illustration_id}/download`, '_blank')}
                        >
                          PDF
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminGenerator;
