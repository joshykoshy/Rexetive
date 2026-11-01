import axios from 'axios';

// v2: the backend issues a JWT after verifying a wallet signature (or the labelled demo login).
// v1 sent an X-Wallet-Address header that the server simply trusted.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001',
  timeout: 120000, // the review panel runs several model calls
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('rex_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
