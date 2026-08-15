import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

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
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          { // Tailwind CDN — needed for the app shell to render offline
            urlPattern: /^https:\/\/cdn\.tailwindcss\.com\/.*/i,
            handler: 'CacheFirst',
            options: { cacheName: 'cdn', expiration: { maxEntries: 4, maxAgeSeconds: 60 * 60 * 24 * 90 } },
          },
          { // registration form metadata usable offline
            urlPattern: /\/api\/register\/meta$/,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'api-meta' },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
