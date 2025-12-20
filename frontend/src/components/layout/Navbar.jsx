import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, Palette, Download, Images, Home, Lock, BookOpen, Search, Image as ImageIcon, Gamepad2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Sheet, SheetContent, SheetTrigger } from '../ui/sheet';
import { getSiteSettings } from '../../services/api';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [siteSettings, setSiteSettings] = useState({});
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    getSiteSettings().then(setSiteSettings).catch(() => {});
  }, []);

  const navLinks = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/galleria', label: 'Galleria', icon: Images },
    { href: '/poster', label: 'Poster', icon: ImageIcon },
    { href: '/libri', label: 'Libri', icon: BookOpen },
    { href: '/giochi', label: 'Giochi', icon: Gamepad2 },
    { href: '/download', label: 'Download', icon: Download },
  ];

  const isActive = (path) => location.pathname === path;

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/cerca?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
      setIsOpen(false);
    }
  };

  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-pink-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 md:w-10 md:h-10 rounded-full bg-gradient-to-br from-pink-200 to-blue-200 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 overflow-hidden">
              {siteSettings.hasBrandLogo ? (
                <img 
                  src={`${BACKEND_URL}${siteSettings.brandLogoUrl}`} 
                  alt="Poppiconni" 
                  className="w-full h-full object-cover"
                />
              ) : null}
            </div>
            <span className="text-xl font-bold text-gray-800 font-['Quicksand']">
              Poppiconni
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-4">
            {/* Search Bar */}
            <form onSubmit={handleSearch} className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Cerca illustrazioni..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 w-48 lg:w-64 h-9 text-sm border-pink-200 focus:border-pink-400 focus:ring-pink-200"
              />
            </form>

            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-300 ${
                  isActive(link.href)
                    ? 'bg-pink-100 text-pink-600'
                    : 'text-gray-600 hover:text-pink-500 hover:bg-pink-50'
                }`}
              >
                <link.icon className="w-4 h-4" />
                <span className="font-medium">{link.label}</span>
              </Link>
            ))}
            <Link to="/admin/login">
              <Button variant="outline" size="sm" className="border-pink-200 text-pink-600 hover:bg-pink-50">
                <Lock className="w-4 h-4 mr-2" />
                Admin
              </Button>
            </Link>
          </div>

          {/* Mobile Menu */}
          <div className="md:hidden">
            <Sheet open={isOpen} onOpenChange={setIsOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Menu className="w-6 h-6 text-gray-600" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-72 bg-white">
                <div className="flex flex-col gap-4 mt-8">
                  {/* Mobile Search */}
                  <form onSubmit={handleSearch} className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      type="text"
                      placeholder="Cerca illustrazioni..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 pr-4 w-full h-10 text-sm border-pink-200 focus:border-pink-400"
                    />
                  </form>

                  {navLinks.map((link) => (
                    <Link
                      key={link.href}
                      to={link.href}
                      onClick={() => setIsOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 ${
                        isActive(link.href)
                          ? 'bg-pink-100 text-pink-600'
                          : 'text-gray-600 hover:text-pink-500 hover:bg-pink-50'
                      }`}
                    >
                      <link.icon className="w-5 h-5" />
                      <span className="font-medium text-lg">{link.label}</span>
                    </Link>
                  ))}
                  <Link to="/admin/login" onClick={() => setIsOpen(false)}>
                    <Button className="w-full mt-4 bg-pink-500 hover:bg-pink-600">
                      <Lock className="w-4 h-4 mr-2" />
                      Area Admin
                    </Button>
                  </Link>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
