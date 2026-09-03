import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import tailwindcss from 'tailwindcss'
import autoprefixer from 'autoprefixer'

// Tailwind runs at build time (PostCSS) — config is inline so the Docker build
// (which copies only index.html/vite.config.js/public/src) needs no extra files.
const tailwindConfig = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#1F3864', light: '#2E75B6' },
        moss: '#548235',
      },
    },
  },
}

// In dev, proxy /api to the backend so cookies stay same-origin.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['style.css', 'icons/icon-192.png', 'icons/icon-512.png'],
      manifest: {
        name: 'Onni Staff Registration',
        short_name: 'Onni',
        description: 'Onni employee registration & payroll',
        start_url: '/register',
        display: 'standalone',
        background_color: '#f1f5f9',
        theme_color: '#1F3864',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          { // registration form metadata usable offline
            urlPattern: /\/api\/register\/meta$/,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'api-meta' },
          },
        ],
      },
    }),
  ],
  css: {
    postcss: { plugins: [tailwindcss(tailwindConfig), autoprefixer()] },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
