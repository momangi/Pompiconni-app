import React, { useState } from 'react';
import { Palette, Copy, Check, Eye, EyeOff } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import { brandKit } from '../data/mock';
import { toast } from 'sonner';

const BrandKitPage = () => {
  const [copiedColor, setCopiedColor] = useState(null);
  const [showDetails, setShowDetails] = useState(true);

  const copyToClipboard = (text, colorName) => {
    navigator.clipboard.writeText(text);
    setCopiedColor(colorName);
    toast.success(`Colore ${colorName} copiato!`);
    setTimeout(() => setCopiedColor(null), 2000);
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      
      <section className="bg-gradient-to-b from-purple-50 to-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-purple-100 rounded-full mb-6">
              <Palette className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-medium text-purple-700">Brand Guidelines</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 mb-4">Brand Kit <span className="gradient-text">Pompiconni</span></h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">Linee guida per mantenere coerenza visiva in tutte le illustrazioni e materiali</p>
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Tabs defaultValue="character" className="w-full">
            <TabsList className="grid w-full max-w-md mx-auto grid-cols-3 mb-12">
              <TabsTrigger value="character">Personaggio</TabsTrigger>
              <TabsTrigger value="colors">Colori</TabsTrigger>
              <TabsTrigger value="style">Stile</TabsTrigger>
            </TabsList>
            
            <TabsContent value="character">
              <div className="grid lg:grid-cols-2 gap-12">
                <div className="flex justify-center">
                  <div className="relative">
                    <div className="w-80 h-80 bg-gradient-to-br from-pink-100 to-blue-100 rounded-3xl flex items-center justify-center shadow-xl">
                      <div className="text-center">
                        <div className="text-9xl">🦄</div>
                        <p className="mt-4 text-2xl font-bold text-gray-700">{brandKit.character.name}</p>
                      </div>
                    </div>
                    <div className="absolute -right-4 top-10 bg-white px-3 py-2 rounded-lg shadow-lg text-sm"><p className="font-semibold text-pink-500">Occhi grandi</p></div>
                    <div className="absolute -left-4 top-1/3 bg-white px-3 py-2 rounded-lg shadow-lg text-sm"><p className="font-semibold text-blue-500">Corno arcobaleno</p></div>
                    <div className="absolute -right-4 bottom-20 bg-white px-3 py-2 rounded-lg shadow-lg text-sm"><p className="font-semibold text-green-500">Guanciotte rosate</p></div>
                  </div>
                </div>
                
                <Card className="border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Caratteristiche di {brandKit.character.name}</span>
                      <Button variant="ghost" size="sm" onClick={() => setShowDetails(!showDetails)}>
                        {showDetails ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="mb-6"><p className="text-lg text-gray-600 italic">"{brandKit.character.personality}"</p></div>
                    {showDetails && (
                      <>
                        <h4 className="font-semibold text-gray-800 mb-3">Tratti distintivi:</h4>
                        <ul className="space-y-2 mb-6">
                          {brandKit.character.features.map((feature, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="w-2 h-2 bg-pink-400 rounded-full mt-2" />
                              <span className="text-gray-600">{feature}</span>
                            </li>
                          ))}
                        </ul>
                        <h4 className="font-semibold text-gray-800 mb-3">Proporzioni:</h4>
                        <div className="grid grid-cols-2 gap-4">
                          {Object.entries(brandKit.character.proportions).map(([key, value]) => (
                            <div key={key} className="bg-gray-50 rounded-lg p-3">
                              <p className="text-sm text-gray-500 capitalize">{key}</p>
                              <p className="font-medium text-gray-800">{value}</p>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="colors">
              <div className="max-w-4xl mx-auto">
                <h3 className="text-2xl font-bold text-gray-800 mb-8 text-center">Palette Colori Ufficiale</h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {brandKit.colors.map((color) => (
                    <Card key={color.name} className="border-0 shadow-lg overflow-hidden hover-lift">
                      <div className="h-32" style={{ backgroundColor: color.hex }} />
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-semibold text-gray-800">{color.name}</h4>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(color.hex, color.name)} className="h-8 px-2">
                            {copiedColor === color.name ? <Check className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
                          </Button>
                        </div>
                        <p className="text-sm font-mono text-gray-500 mb-2">{color.hex}</p>
                        <p className="text-sm text-gray-600">{color.usage}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="style">
              <div className="max-w-4xl mx-auto">
                <div className="grid md:grid-cols-2 gap-8">
                  <Card className="border-0 shadow-lg">
                    <CardHeader><CardTitle>Tipografia</CardTitle></CardHeader>
                    <CardContent>
                      <div className="space-y-6">
                        <div>
                          <p className="text-sm text-gray-500 mb-2">Font Primario</p>
                          <p className="text-3xl font-bold" style={{ fontFamily: 'Quicksand' }}>{brandKit.typography.primary}</p>
                          <p className="text-gray-600 mt-1">Per titoli e intestazioni</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-500 mb-2">Font Secondario</p>
                          <p className="text-2xl" style={{ fontFamily: 'Nunito' }}>{brandKit.typography.secondary}</p>
                          <p className="text-gray-600 mt-1">Per testi e paragrafi</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-4"><p className="text-sm text-gray-600"><strong>Stile:</strong> {brandKit.typography.style}</p></div>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card className="border-0 shadow-lg">
                    <CardHeader><CardTitle>Linee Guida Illustrazioni</CardTitle></CardHeader>
                    <CardContent>
                      <ul className="space-y-4">
                        {brandKit.styleGuidelines.map((guideline, idx) => (
                          <li key={idx} className="flex items-start gap-3">
                            <div className="w-6 h-6 bg-pink-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                              <Check className="w-4 h-4 text-pink-500" />
                            </div>
                            <span className="text-gray-600">{guideline}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </div>
                
                <div className="mt-12 grid md:grid-cols-2 gap-8">
                  <Card className="border-2 border-green-200 bg-green-50/30">
                    <CardHeader><CardTitle className="text-green-700 flex items-center gap-2"><Check className="w-5 h-5" />Da Fare</CardTitle></CardHeader>
                    <CardContent>
                      <ul className="space-y-2 text-gray-700">
                        <li>• Usare linee morbide e arrotondate</li>
                        <li>• Mantenere espressioni dolci e positive</li>
                        <li>• Rispettare le proporzioni del personaggio</li>
                        <li>• Usare la palette colori ufficiale</li>
                        <li>• Includere sempre le guanciotte rosate</li>
                      </ul>
                    </CardContent>
                  </Card>
                  
                  <Card className="border-2 border-red-200 bg-red-50/30">
                    <CardHeader><CardTitle className="text-red-700 flex items-center gap-2"><span className="text-lg">×</span>Da Evitare</CardTitle></CardHeader>
                    <CardContent>
                      <ul className="space-y-2 text-gray-700">
                        <li>• Stile realistico o dettagliato</li>
                        <li>• Espressioni tristi o aggressive</li>
                        <li>• Linee sottili difficili da colorare</li>
                        <li>• Colori troppo scuri o saturi</li>
                        <li>• Modificare le proporzioni base</li>
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default BrandKitPage;
