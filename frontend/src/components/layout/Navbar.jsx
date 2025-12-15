import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Palette, Download, Images, Home, Lock, BookOpen } from 'lucide-react';
import { Button } from '../ui/button';
import { Sheet, SheetContent, SheetTrigger } from '../ui/sheet';

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const navLinks = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/galleria', label: 'Galleria', icon: Images },
    { href: '/libri', label: 'Libri', icon: BookOpen },
    { href: '/download', label: 'Download', icon: Download },
    { href: '/brand-kit', label: 'Brand Kit', icon: Palette },
  ];

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-pink-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-pink-200 to-blue-200 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
              <span className="text-xl">🦄</span>
            </div>
            <span className="text-xl font-bold text-gray-800 font-['Quicksand']">
              Poppiconni
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6">
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
