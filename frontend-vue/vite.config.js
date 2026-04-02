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
    // Sin sourcemaps en producción — el código fuente nunca llega al cliente
    sourcemap: false,
    // Terser: elimina console.log, debugger, y ofusca nombres de variables
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,      // Elimina todo console.log/warn/info
        drop_debugger: true,     // Elimina statements debugger
        pure_funcs: ['console.log', 'console.info', 'console.debug', 'console.warn', 'console.error'],
        passes: 3,               // Múltiples pasadas de compresión
        unsafe: true,
        unsafe_arrows: true
      },
      mangle: {
        toplevel: true,          // Renombra variables del top-level (offusca más)
        properties: false        // No renombra propiedades (rompe frameworks)
      },
      format: {
        comments: false          // Elimina todos los comentarios del bundle
      }
    },
    rollupOptions: {
      output: {
        // Nombres hasheados: el atacante no sabe qué archivo es qué módulo
        chunkFileNames: 'assets/[hash].js',
        entryFileNames: 'assets/[hash].js',
        assetFileNames: 'assets/[hash].[ext]',
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
