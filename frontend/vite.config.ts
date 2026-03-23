import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'
import path from 'node:path'

const isElectron = process.env.ELECTRON !== 'false'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    ...(isElectron
      ? [
          electron([
            {
              entry: 'electron/main.ts',
              onstart: ({ startup }) => {
                const env = { ...process.env }
                delete env.ELECTRON_RUN_AS_NODE
                return startup(['.', '--no-sandbox'], { env })
              },
              vite: {
                build: {
                  outDir: 'dist-electron',
                },
              },
            },
            {
              entry: 'electron/preload.ts',
              onstart: ({ reload }) => reload(),
              vite: {
                build: { outDir: 'dist-electron' },
              },
            },
          ]),
          renderer(),
        ]
      : []),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 3030,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
