import React from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import LandingPage from "./pages/LandingPage";
import GalleryPage from "./pages/GalleryPage";
import ThemePage from "./pages/ThemePage";
import BrandKitPage from "./pages/BrandKitPage";
import DownloadPage from "./pages/DownloadPage";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminIllustrations from "./pages/admin/AdminIllustrations";
import AdminGenerator from "./pages/admin/AdminGenerator";
import AdminLogin from "./pages/admin/AdminLogin";

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
          
          {/* Admin Routes */}
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboard />} />
            <Route path="illustrazioni" element={<AdminIllustrations />} />
            <Route path="generatore" element={<AdminGenerator />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
