import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'fs'
import path from 'path'

// Check if SSL certs exist (for dev server)
const certsExist = fs.existsSync(path.resolve(__dirname, '../certs/key.pem'))

// https://vite.dev/config/
export default defineConfig({
  // Base path for GitHub Pages deployment
  base: process.env.GITHUB_PAGES ? '/NiftiDicom2gif/' : '/',
  plugins: [react(), tailwindcss()],
  server: {
    port: 8801,
    host: '0.0.0.0',
    ...(certsExist && {
      https: {
        key: fs.readFileSync(path.resolve(__dirname, '../certs/key.pem')),
        cert: fs.readFileSync(path.resolve(__dirname, '../certs/cert.pem')),
      },
    }),
    proxy: {
      '/api': {
        target: 'https://localhost:8802',
        changeOrigin: true,
        secure: false, // Allow self-signed certificates
      },
    },
  },
})
