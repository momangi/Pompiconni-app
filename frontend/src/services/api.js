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

export const incrementDownload = async (illustrationId) => {
  const response = await api.post(`/illustrations/${illustrationId}/download`);
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

// Theme CRUD
export const createTheme = async (theme) => {
  const response = await api.post('/admin/themes', theme);
  return response.data;
};

export const updateTheme = async (themeId, theme) => {
  const response = await api.put(`/admin/themes/${themeId}`, theme);
  return response.data;
};

export const deleteTheme = async (themeId) => {
  const response = await api.delete(`/admin/themes/${themeId}`);
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

// AI Generation
export const generateIllustration = async (prompt, themeId = null, style = 'lineart') => {
  const response = await api.post('/admin/generate-illustration', {
    prompt,
    themeId,
    style,
  });
  return response.data;
};

export default api;
