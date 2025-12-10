import React from 'react';
import { Link } from 'react-router-dom';
import { Heart, Mail, Instagram } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="bg-gradient-to-b from-white to-pink-50 border-t border-pink-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-pink-200 to-blue-200 flex items-center justify-center">
                <span className="text-xl">🦄</span>
              </div>
              <span className="text-xl font-bold text-gray-800 font-['Quicksand']">Pompiconni</span>
            </div>
            <p className="text-gray-600 mb-4 max-w-sm">
              Libri da colorare per bambini con il nostro adorabile unicorno Pompiconni. 
              Dolce, simpatico e leggermente impacciato!
            </p>
            <div className="flex gap-4">
              <a href="mailto:info@pompiconni.it" className="text-gray-400 hover:text-pink-500 transition-colors">
                <Mail className="w-5 h-5" />
              </a>
              <a href="#" className="text-gray-400 hover:text-pink-500 transition-colors">
                <Instagram className="w-5 h-5" />
              </a>
            </div>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-semibold text-gray-800 mb-4">Navigazione</h4>
            <ul className="space-y-2">
              <li><Link to="/" className="text-gray-600 hover:text-pink-500 transition-colors">Home</Link></li>
              <li><Link to="/galleria" className="text-gray-600 hover:text-pink-500 transition-colors">Galleria</Link></li>
              <li><Link to="/download" className="text-gray-600 hover:text-pink-500 transition-colors">Download</Link></li>
              <li><Link to="/brand-kit" className="text-gray-600 hover:text-pink-500 transition-colors">Brand Kit</Link></li>
            </ul>
          </div>

          {/* Temi */}
          <div>
            <h4 className="font-semibold text-gray-800 mb-4">Temi</h4>
            <ul className="space-y-2">
              <li><Link to="/galleria/mestieri" className="text-gray-600 hover:text-pink-500 transition-colors">I Mestieri</Link></li>
              <li><Link to="/galleria/fattoria" className="text-gray-600 hover:text-pink-500 transition-colors">La Fattoria</Link></li>
              <li><Link to="/galleria/zoo" className="text-gray-600 hover:text-pink-500 transition-colors">Lo Zoo</Link></li>
              <li><Link to="/galleria/stagioni" className="text-gray-600 hover:text-pink-500 transition-colors">Le Stagioni</Link></li>
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="mt-12 pt-8 border-t border-pink-100 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-gray-500 text-sm">
            © {new Date().getFullYear()} Pompiconni. Tutti i diritti riservati.
          </p>
          <p className="text-gray-500 text-sm flex items-center gap-1">
            Fatto con <Heart className="w-4 h-4 text-pink-500 fill-pink-500" /> per i piccoli artisti
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
