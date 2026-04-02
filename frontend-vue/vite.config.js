import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      // En desarrollo local, proxy hacia el backend FastAPI
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    // Cloudflare Pages espera el output en dist/
    rollupOptions: {
      output: {
        // Code splitting por ruta para carga más rápida
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia']
        }
      }
    }
  },
  // Variable de entorno: VITE_API_URL se define en Cloudflare Pages
  define: {
    __APP_VERSION__: JSON.stringify('1.0.0')
  }
})
