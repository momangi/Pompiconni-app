import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Heart, Mail, Instagram } from 'lucide-react';
import { getSiteSettings } from '../../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// TikTok icon component
const TikTokIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
);

const Footer = () => {
  const [siteSettings, setSiteSettings] = useState({});

  useEffect(() => {
    getSiteSettings().then(setSiteSettings).catch(() => {});
  }, []);

  return (
    <footer className="bg-gradient-to-b from-white to-pink-50 border-t border-pink-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-pink-200 to-blue-200 flex items-center justify-center overflow-hidden">
                {siteSettings.hasBrandLogo ? (
                  <img 
                    src={`${BACKEND_URL}${siteSettings.brandLogoUrl}`} 
                    alt="Poppiconni" 
                    className="w-full h-full object-cover"
                  />
                ) : null}
              </div>
              <span className="text-xl font-bold text-gray-800 font-['Quicksand']">Poppiconni</span>
            </div>
            <p className="text-gray-600 mb-4 max-w-sm">
              Libri da colorare per bambini con il nostro adorabile unicorno Poppiconni. 
              Dolce, simpatico e leggermente impacciato!
            </p>
            <div className="flex gap-4">
              <a href="mailto:pompiconni@gmail.com" className="text-gray-400 hover:text-pink-500 transition-colors">
                <Mail className="w-5 h-5" />
              </a>
              {siteSettings.instagramUrl && (
                <a 
                  href={siteSettings.instagramUrl} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-gray-400 hover:text-pink-500 transition-colors"
                >
                  <Instagram className="w-5 h-5" />
                </a>
              )}
              {siteSettings.tiktokUrl && (
                <a 
                  href={siteSettings.tiktokUrl} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-gray-400 hover:text-gray-800 transition-colors"
                >
                  <TikTokIcon className="w-5 h-5" />
                </a>
              )}
            </div>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-semibold text-gray-800 mb-4">Navigazione</h4>
            <ul className="space-y-2">
              <li><Link to="/" className="text-gray-600 hover:text-pink-500 transition-colors">Home</Link></li>
              <li><Link to="/galleria" className="text-gray-600 hover:text-pink-500 transition-colors">Galleria</Link></li>
              <li><Link to="/poster" className="text-gray-600 hover:text-pink-500 transition-colors">Poster</Link></li>
              <li><Link to="/libri" className="text-gray-600 hover:text-pink-500 transition-colors">Libri</Link></li>
              <li><Link to="/giochi" className="text-gray-600 hover:text-pink-500 transition-colors">Giochi</Link></li>
              <li><Link to="/download" className="text-gray-600 hover:text-pink-500 transition-colors">Download</Link></li>
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
              <li><Link to="/galleria/sport" className="text-gray-600 hover:text-pink-500 transition-colors">Lo Sport</Link></li>
              <li><Link to="/galleria/vita-quotidiana" className="text-gray-600 hover:text-pink-500 transition-colors">Vita Quotidiana</Link></li>
            </ul>
          </div>
        </div>

        {/* Legal Links */}
        <div className="mt-8 pt-8 border-t border-pink-100">
          <div className="flex flex-wrap justify-center gap-6 text-sm">
            <Link to="/privacy" className="text-gray-500 hover:text-pink-500 transition-colors">Privacy Policy</Link>
            <Link to="/cookie-policy" className="text-gray-500 hover:text-pink-500 transition-colors">Cookie Policy</Link>
            <Link to="/termini-condizioni" className="text-gray-500 hover:text-pink-500 transition-colors">Termini e Condizioni</Link>
            <Link to="/contatti-legali" className="text-gray-500 hover:text-pink-500 transition-colors">Contatti Legali</Link>
          </div>
        </div>

        {/* Bottom */}
        <div className="mt-8 pt-8 border-t border-pink-100 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-gray-500 text-sm">
            © {new Date().getFullYear()} Poppiconni. Tutti i diritti riservati.
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
