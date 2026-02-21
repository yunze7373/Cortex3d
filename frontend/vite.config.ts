import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // 改成WSL的IP地址，例如 172.xx.xx.xx
        target: 'http://192.168.3.9:8000',
        changeOrigin: true,
      },
    },
  },
})
