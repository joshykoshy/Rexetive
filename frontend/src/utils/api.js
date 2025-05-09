import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 40000,
});

// Add request interceptor to include wallet address in header
api.interceptors.request.use(
  (config) => {
    const walletAddress = localStorage.getItem('wallet_address');
    if (walletAddress) {
      config.headers['X-Wallet-Address'] = walletAddress;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;