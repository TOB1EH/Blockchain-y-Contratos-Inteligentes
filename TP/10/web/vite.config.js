import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// Configurar plugins de Vue y devtools
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],

  // Configurar alias @ para importar desde src/
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },

  // Proxy de /api hacia el servidor Flask
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },

  // Configurar entorno de pruebas con vitest y jsdom
  test: {
    environment: 'jsdom',
    globals: true
  }
})