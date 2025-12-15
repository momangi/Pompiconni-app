import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import LandingPage from "./pages/LandingPage";
import GalleryPage from "./pages/GalleryPage";
import ThemePage from "./pages/ThemePage";
import BrandKitPage from "./pages/BrandKitPage";
import DownloadPage from "./pages/DownloadPage";
import PrivacyPage from "./pages/PrivacyPage";
import CookiePolicyPage from "./pages/CookiePolicyPage";
import TerminiCondizioniPage from "./pages/TerminiCondizioniPage";
import ContattiLegaliPage from "./pages/ContattiLegaliPage";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminIllustrations from "./pages/admin/AdminIllustrations";
import AdminGenerator from "./pages/admin/AdminGenerator";
import AdminThemes from "./pages/admin/AdminThemes";
import AdminSettings from "./pages/admin/AdminSettings";
import AdminBooks from "./pages/admin/AdminBooks";
import AdminSceneEditor from "./pages/admin/AdminSceneEditor";
import AdminLogin from "./pages/admin/AdminLogin";
import CookieBanner from "./components/CookieBanner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/galleria" element={<GalleryPage />} />
          <Route path="/galleria/:themeId" element={<ThemePage />} />
          <Route path="/brand-kit" element={<BrandKitPage />} />
          <Route path="/download" element={<DownloadPage />} />
          
          {/* Legal Pages */}
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/cookie-policy" element={<CookiePolicyPage />} />
          <Route path="/termini-condizioni" element={<TerminiCondizioniPage />} />
          <Route path="/contatti-legali" element={<ContattiLegaliPage />} />
          
          {/* Admin Routes */}
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="illustrations" element={<AdminIllustrations />} />
            <Route path="themes" element={<AdminThemes />} />
            <Route path="generator" element={<AdminGenerator />} />
            <Route path="books" element={<AdminBooks />} />
            <Route path="books/:bookId/scenes" element={<AdminSceneEditor />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
      <CookieBanner />
    </div>
  );
}

export default App;
