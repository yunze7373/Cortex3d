import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',        // 监听所有网络接口，支持局域网访问
    port: 5173,
    strictPort: false,       // 端口占用时自动尝试下一个
    proxy: {
      '/api': {
        target: 'http://172.28.124.41:8000',
        changeOrigin: true,
      },
      '/outputs': {
        target: 'http://172.28.124.41:8000',
        changeOrigin: true,
      },
    },
    hmr: {
      host: 'localhost',     // 开发时使用 localhost
      port: 5173,
    }
  },
})
