import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds for video processing
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('arsl_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Clear stale token on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('arsl_token');
    }
    return Promise.reject(error);
  }
);

export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const predictVideo = async (file, topK = 5, model = 'karsl_mediapipe') => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post(`/predict/video?top_k=${topK}&model=${model}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const predictFrames = async (frames, topK = 5, model = 'karsl_mediapipe') => {
  const response = await api.post('/predict/frames', {
    frames,
    top_k: topK,
    model,
  });

  return response.data;
};

export const getHistory = async (page = 1, pageSize = 20) => {
  const response = await api.get(`/auth/history?page=${page}&page_size=${pageSize}`);
  return response.data;
};

export const changePassword = async (currentPassword, newPassword) => {
  const response = await api.post('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
};

export const forgotPassword = async (email) => {
  const response = await api.post('/auth/forgot-password', { email });
  return response.data;
};

export const resetPassword = async (token, newPassword) => {
  const response = await api.post('/auth/reset-password', {
    token,
    new_password: newPassword,
  });
  return response.data;
};

export default api;
