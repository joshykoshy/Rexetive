// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/submit_submission': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/get_submission': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/get_all_submissions': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
});