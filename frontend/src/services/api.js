import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Create axios instance
const api = axios.create({
  baseURL: API,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('pompiconni_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============== PUBLIC API ==============

export const getThemes = async () => {
  const response = await api.get('/themes');
  return response.data;
};

export const getTheme = async (themeId) => {
  const response = await api.get(`/themes/${themeId}`);
  return response.data;
};

export const getIllustrations = async (themeId = null, isFree = null) => {
  const params = {};
  if (themeId) params.themeId = themeId;
  if (isFree !== null) params.isFree = isFree;
  const response = await api.get('/illustrations', { params });
  return response.data;
};

export const getIllustration = async (illustrationId) => {
  const response = await api.get(`/illustrations/${illustrationId}`);
  return response.data;
};

export const downloadIllustration = async (illustrationId) => {
  // This triggers a real file download
  const response = await api.post(`/illustrations/${illustrationId}/download`, {}, {
    responseType: 'blob'
  });
  return response;
};

export const checkDownloadStatus = async (illustrationId) => {
  const response = await api.get(`/illustrations/${illustrationId}/download-status`);
  return response.data;
};

export const searchIllustrations = async (q, limit = 48) => {
  const response = await api.get(`/search/illustrations`, { params: { q, limit } });
  return response.data;
};

export const getBundles = async () => {
  const response = await api.get('/bundles');
  return response.data;
};

export const getReviews = async () => {
  const response = await api.get('/reviews');
  return response.data;
};

export const getBrandKit = async () => {
  const response = await api.get('/brand-kit');
  return response.data;
};

export const getSiteSettings = async () => {
  const response = await api.get('/site-settings');
  return response.data;
};

// ============== ADMIN API ==============

export const adminLogin = async (email, password) => {
  const response = await api.post('/admin/login', { email, password });
  if (response.data.token) {
    localStorage.setItem('pompiconni_token', response.data.token);
    localStorage.setItem('pompiconni_admin', 'true');
  }
  return response.data;
};

export const adminLogout = () => {
  localStorage.removeItem('pompiconni_token');
  localStorage.removeItem('pompiconni_admin');
};

export const isAuthenticated = () => {
  return !!localStorage.getItem('pompiconni_token');
};

export const getDashboard = async () => {
  const response = await api.get('/admin/dashboard');
  return response.data;
};

// Brand Logo
export const getBrandLogoStatus = async () => {
  const response = await api.get('/admin/brand-logo-status');
  return response.data;
};

export const uploadBrandLogo = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/admin/upload-brand-logo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const deleteBrandLogo = async () => {
  const response = await api.delete('/admin/brand-logo');
  return response.data;
};

// Social Links
export const updateSocialLinks = async (instagramUrl, tiktokUrl) => {
  const response = await api.put(`/admin/social-links?instagramUrl=${encodeURIComponent(instagramUrl)}&tiktokUrl=${encodeURIComponent(tiktokUrl)}`);
  return response.data;
};

// Theme CRUD
export const createTheme = async (theme) => {
  const response = await api.post('/admin/themes', theme);
  return response.data;
};

export const updateTheme = async (themeId, theme) => {
  const response = await api.put(`/admin/themes/${themeId}`, theme);
  return response.data;
};

// Illustration CRUD
export const createIllustration = async (illustration) => {
  const response = await api.post('/admin/illustrations', illustration);
  return response.data;
};

export const updateIllustration = async (illustrationId, illustration) => {
  const response = await api.put(`/admin/illustrations/${illustrationId}`, illustration);
  return response.data;
};

export const deleteIllustration = async (illustrationId) => {
  const response = await api.delete(`/admin/illustrations/${illustrationId}`);
  return response.data;
};

// Bundle CRUD
export const getAdminBundles = async () => {
  const response = await api.get('/admin/bundles');
  return response.data;
};

export const createBundle = async (bundle) => {
  const response = await api.post('/admin/bundles', bundle);
  return response.data;
};

export const updateBundle = async (bundleId, bundle) => {
  const response = await api.put(`/admin/bundles/${bundleId}`, bundle);
  return response.data;
};

export const deleteBundle = async (bundleId) => {
  const response = await api.delete(`/admin/bundles/${bundleId}`);
  return response.data;
};

export const uploadBundleBackground = async (bundleId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/bundles/${bundleId}/upload-background`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const uploadBundlePdf = async (bundleId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/bundles/${bundleId}/upload-pdf`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// File Upload
export const uploadFile = async (file, fileType = 'image') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('file_type', fileType);
  
  const response = await api.post('/admin/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Attach PDF to illustration
export const attachPdfToIllustration = async (illustrationId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post(`/admin/illustrations/${illustrationId}/attach-pdf`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Attach Image to illustration
export const attachImageToIllustration = async (illustrationId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post(`/admin/illustrations/${illustrationId}/attach-image`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Get image status
export const getImageStatus = async (illustrationId) => {
  const response = await api.get(`/illustrations/${illustrationId}/image-status`);
  return response.data;
};

// AI Generation
export const generateIllustration = async (prompt, themeId = null, style = 'lineart') => {
  const response = await api.post('/admin/generate-illustration', {
    prompt,
    themeId,
    style,
  });
  return response.data;
};

// ============== ADMIN REVIEWS ==============

export const getAdminReviews = async () => {
  const response = await api.get('/admin/reviews');
  return response.data;
};

export const updateReview = async (reviewId, isApproved) => {
  const response = await api.put(`/admin/reviews/${reviewId}`, { is_approved: isApproved });
  return response.data;
};

export const deleteReview = async (reviewId) => {
  const response = await api.delete(`/admin/reviews/${reviewId}`);
  return response.data;
};

// ============== ADMIN SETTINGS ==============

export const getAdminSettings = async () => {
  const response = await api.get('/admin/settings');
  return response.data;
};

export const updateAdminSettings = async (settings) => {
  const response = await api.put('/admin/settings', settings);
  return response.data;
};

export const getDownloadStats = async () => {
  const response = await api.get('/admin/download-stats');
  return response.data;
};

// ============== HERO IMAGE ==============

export const getHeroStatus = async () => {
  const response = await api.get('/site/hero-status');
  return response.data;
};

export const uploadHeroImage = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post('/admin/site/hero-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const deleteHeroImage = async () => {
  const response = await api.delete('/admin/site/hero-image');
  return response.data;
};

// ============== THEME COLORS ==============

export const getThemeColorPalette = async () => {
  const response = await api.get('/theme-colors');
  return response.data;
};

// ============== ENHANCED THEME CRUD ==============

export const checkThemeDelete = async (themeId) => {
  const response = await api.get(`/admin/themes/check-delete/${themeId}`);
  return response.data;
};

export const deleteTheme = async (themeId, force = false) => {
  const response = await api.delete(`/admin/themes/${themeId}?force=${force}`);
  return response.data;
};

export const changeIllustrationTheme = async (illustrationId, themeId) => {
  const response = await api.put(`/admin/illustrations/${illustrationId}/theme`, null, {
    params: { theme_id: themeId }
  });
  return response.data;
};

// ============== BOOKS API ==============

// Public
export const getBooks = async () => {
  const response = await api.get('/books');
  return response.data;
};

export const getBook = async (bookId) => {
  const response = await api.get(`/books/${bookId}`);
  return response.data;
};

export const getReadingProgress = async (bookId, visitorId) => {
  const response = await api.get(`/books/${bookId}/progress/${visitorId}`);
  return response.data;
};

export const saveReadingProgress = async (bookId, visitorId, scene) => {
  const response = await api.post(`/books/${bookId}/progress/${visitorId}?scene=${scene}`);
  return response.data;
};

// Admin Books
export const getAdminBooks = async () => {
  const response = await api.get('/admin/books');
  return response.data;
};

export const createBook = async (book) => {
  const response = await api.post('/admin/books', book);
  return response.data;
};

export const updateBook = async (bookId, book) => {
  const response = await api.put(`/admin/books/${bookId}`, book);
  return response.data;
};

export const deleteBook = async (bookId) => {
  const response = await api.delete(`/admin/books/${bookId}`);
  return response.data;
};

export const uploadBookCover = async (bookId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/books/${bookId}/cover`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// Admin Scenes
export const getBookScenes = async (bookId) => {
  const response = await api.get(`/admin/books/${bookId}/scenes`);
  return response.data;
};

export const createScene = async (bookId, scene) => {
  const response = await api.post(`/admin/books/${bookId}/scenes`, scene);
  return response.data;
};

export const updateScene = async (bookId, sceneId, text) => {
  const response = await api.put(`/admin/books/${bookId}/scenes/${sceneId}`, text);
  return response.data;
};

export const deleteScene = async (bookId, sceneId) => {
  const response = await api.delete(`/admin/books/${bookId}/scenes/${sceneId}`);
  return response.data;
};

export const uploadSceneColoredImage = async (bookId, sceneId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/books/${bookId}/scenes/${sceneId}/colored-image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const uploadSceneLineartImage = async (bookId, sceneId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/books/${bookId}/scenes/${sceneId}/lineart-image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// ============== POPPICONNI MULTI-AI PIPELINE ==============

// Generation Styles (Reference Image Library)
export const getGenerationStyles = async () => {
  const response = await api.get('/admin/styles');
  return response.data;
};

export const createGenerationStyle = async (style) => {
  const response = await api.post('/admin/styles', style);
  return response.data;
};

export const deleteGenerationStyle = async (styleId) => {
  const response = await api.delete(`/admin/styles/${styleId}`);
  return response.data;
};

export const uploadStyleReference = async (styleId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/styles/${styleId}/upload-reference`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

// Multi-AI Pipeline Generation
export const generatePoppiconni = async (userRequest, options = {}) => {
  const response = await api.post('/admin/generate-poppiconni', {
    user_request: userRequest,
    style_id: options.styleId || null,
    style_lock: options.styleLock || false,
    save_to_gallery: options.saveToGallery !== false,
    theme_id: options.themeId || null,
    reference_image_base64: options.referenceImageBase64 || null // Direct reference image
  });
  return response.data;
};

export const getPipelineStatus = async (generationId) => {
  const response = await api.get(`/admin/pipeline-status/${generationId}`);
  return response.data;
};

// ============== POSTER API ==============

// Public Poster API
export const getPublicPosters = async () => {
  const response = await api.get('/posters');
  return response.data;
};

export const getPublicPoster = async (posterId) => {
  const response = await api.get(`/posters/${posterId}`);
  return response.data;
};

// Admin Poster API
export const getAdminPosters = async () => {
  const response = await api.get('/admin/posters');
  return response.data;
};

export const getAdminPoster = async (posterId) => {
  const response = await api.get(`/admin/posters/${posterId}`);
  return response.data;
};

export const createPoster = async (poster) => {
  const response = await api.post('/admin/posters', poster);
  return response.data;
};

export const updatePoster = async (posterId, data) => {
  const response = await api.put(`/admin/posters/${posterId}`, data);
  return response.data;
};

export const deletePoster = async (posterId) => {
  const response = await api.delete(`/admin/posters/${posterId}`);
  return response.data;
};

export const uploadPosterImage = async (posterId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/posters/${posterId}/upload-image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const uploadPosterPdf = async (posterId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/posters/${posterId}/upload-pdf`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const getPosterStats = async () => {
  const response = await api.get('/admin/posters/stats/summary');
  return response.data;
};

// ============== CHARACTER IMAGES API ==============

export const getCharacterImages = async () => {
  const response = await api.get('/character-images');
  return response.data;
};

export const getAdminCharacterImages = async () => {
  const response = await api.get('/admin/character-images');
  return response.data;
};

export const uploadCharacterImage = async (trait, file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post(`/admin/character-images/${trait}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const deleteCharacterImage = async (trait) => {
  const response = await api.delete(`/admin/character-images/${trait}`);
  return response.data;
};

export const updateCharacterText = async (trait, data) => {
  const response = await api.put(`/admin/character-images/${trait}/text`, data);
  return response.data;
};

export default api;
