import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',        // 监听所有网络接口
    port: 5173,
    strictPort: false,       // 端口占用时自动尝试下一个
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // 本地开发时代理到 localhost:8000
        changeOrigin: true,
      },
      '/outputs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
    middlewareMode: false,
  },
})

