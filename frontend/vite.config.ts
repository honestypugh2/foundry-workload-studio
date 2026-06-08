import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite dev server proxies the gateway running on :8000 so the React app can
// call /api/* without CORS friction in development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/healthz': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
