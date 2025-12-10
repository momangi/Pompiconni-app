import React from 'react';
import { Link } from 'react-router-dom';
import { Images, Download, Users, TrendingUp, ArrowRight, Wand2, Package } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { themes, illustrations, bundles } from '../../data/mock';

const AdminDashboard = () => {
  const totalDownloads = illustrations.reduce((acc, i) => acc + i.downloadCount, 0);
  const freeCount = illustrations.filter(i => i.isFree).length;

  const stats = [
    { label: 'Illustrazioni', value: illustrations.length, icon: Images, color: 'pink' },
    { label: 'Temi', value: themes.length, icon: Package, color: 'blue' },
    { label: 'Download Totali', value: totalDownloads.toLocaleString(), icon: Download, color: 'green' },
    { label: 'Gratuite', value: freeCount, icon: TrendingUp, color: 'yellow' },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Dashboard</h1>
        <p className="text-gray-600">Benvenuto nel pannello di amministrazione di Pompiconni</p>
      </div>

      {/* Stats Grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat, idx) => (
          <Card key={idx} className="border-0 shadow-md">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-800">{stat.value}</p>
                </div>
                <div className={`w-12 h-12 rounded-xl bg-${stat.color}-100 flex items-center justify-center`}>
                  <stat.icon className={`w-6 h-6 text-${stat.color}-500`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        <Card className="border-0 shadow-md bg-gradient-to-br from-pink-50 to-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wand2 className="w-5 h-5 text-pink-500" />
              Genera Nuove Illustrazioni
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">Usa l'AI per creare nuove bozze di Pompiconni in diverse situazioni e temi.</p>
            <Link to="/admin/generatore">
              <Button className="bg-pink-500 hover:bg-pink-600">
                Vai al Generatore
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-md bg-gradient-to-br from-blue-50 to-white">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Images className="w-5 h-5 text-blue-500" />
              Gestisci Illustrazioni
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">Carica, modifica ed organizza le illustrazioni per tema.</p>
            <Link to="/admin/illustrazioni">
              <Button variant="outline" className="border-blue-300 text-blue-600 hover:bg-blue-50">
                Vai alle Illustrazioni
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="border-0 shadow-md">
        <CardHeader>
          <CardTitle>Illustrazioni Popolari</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {illustrations
              .sort((a, b) => b.downloadCount - a.downloadCount)
              .slice(0, 5)
              .map((illustration, idx) => (
                <div key={illustration.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-4">
                    <span className="w-8 h-8 bg-pink-100 rounded-full flex items-center justify-center text-sm font-bold text-pink-500">
                      {idx + 1}
                    </span>
                    <div>
                      <p className="font-medium text-gray-800">{illustration.title}</p>
                      <p className="text-sm text-gray-500">{themes.find(t => t.id === illustration.themeId)?.name}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-gray-500">
                    <Download className="w-4 h-4" />
                    <span>{illustration.downloadCount}</span>
                  </div>
                </div>
              ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminDashboard;
