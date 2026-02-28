# 🚀 Cortex3d WebUI 快速启动指南

## 一次性配置 (首次使用)

### 步骤 1️⃣ - 进入 WSL 并运行配置脚本

```bash
wsl
cd ~/projects/cortex3d
bash setup-dev.sh
```

这个脚本会自动：
- ✅ 创建 Python 虚拟环境
- ✅ 安装后端依赖
- ✅ 安装前端依赖 (npm)
- ✅ 配置 bash 别名
- ✅ 创建日志目录

### 步骤 2️⃣ - 激活别名配置

```bash
source ~/.bashrc
```

---

## ✨ 日常使用

### 启动所有服务 (前端 + 后端)

```bash
3d
```

**输出示例：**
```
🚀 启动后端服务...
   ✅ 后端已启动 (PID: 12345)
🚀 启动前端服务...
   ✅ 前端已启动 (PID: 12346)

╔════════════════════════════════════════════════════════════╗
║          🎉 Cortex3d 开发环境已启动                        ║
╠════════════════════════════════════════════════════════════╣
║ 🖥️  本地访问：
║    📱 前端：http://localhost:5173
║    🔌 API：http://localhost:8000
║    📖 文档：http://localhost:8000/docs
╠════════════════════════════════════════════════════════════╣
║ 🌐 局域网访问（其他设备）：
║    📱 前端：http://172.28.124.41:5173
║    🔌 API：http://172.28.124.41:8000
║    📖 文档：http://172.28.124.41:8000/docs
```

### 其他命令

```bash
3d-stop      # 停止所有服务
3d-restart   # 重启所有服务
3d-status    # 查看服务状态
```

---

## 📱 访问应用

### 本地访问 (WSL 内)
- **前端**: http://localhost:5173
- **API 文档**: http://localhost:8000/docs

### 局域网访问 (其他电脑/手机)
- **前端**: http://172.28.124.41:5173
- **API 文档**: http://172.28.124.41:8000/docs

> 注意: `172.28.124.41` 是示例 IP，实际 IP 会在启动时显示

---

## 🔍 查看日志

```bash
# 后端日志
tail -f ~/projects/cortex3d/logs/backend.log

# 前端日志
tail -f ~/projects/cortex3d/logs/frontend.log

# 实时跟踪所有日志
tail -f ~/projects/cortex3d/logs/*.log
```

---

## 🛠️ 常见问题

### Q: 进入 WSL 后自动启动服务？

编辑 `~/.bashrc`，在最后添加：

```bash
# 自动进入项目并启动服务
if [ -f "$HOME/projects/cortex3d/dev.sh" ]; then
    cd ~/projects/cortex3d
    source .venv/bin/activate 2>/dev/null
fi
```

### Q: 忘记虚拟环境在哪里激活？

```bash
cd ~/projects/cortex3d
source .venv/bin/activate
```

### Q: 前端无法连接后端？

1. 检查后端是否在运行:
   ```bash
   3d-status
   ```

2. 检查防火墙是否阻止 8000 端口 (Windows)
3. 如果使用局域网访问，确保 `frontend/.env.local` 配置正确：
   ```
   VITE_API_BASE_URL=http://172.28.124.41:8000
   ```

### Q: 修改代码后服务没有自动热重载？

服务已配置热重载，但需要确保文件保存。如果长时间没有反应，手动重启：

```bash
3d-restart
```

---

## 📋 项目结构

```
~/projects/cortex3d/
├── dev.sh              ← 启动脚本（自动启动前端+后端）
├── setup-dev.sh        ← 首次配置脚本
├── .venv/              ← Python 虚拟环境
├── backend/            ← FastAPI 后端
│   ├── main.py
│   └── requirements.txt
├── frontend/           ← React 前端
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.local      ← 环境变量配置
├── logs/               ← 日志文件（运行时生成）
│   ├── backend.log
│   └── frontend.log
└── ...
```

---

## 🎯 完整工作流

```bash
# 1. 进入 WSL
wsl

# 2. 进入项目目录
cd ~/projects/cortex3d

# 3. 启动所有服务
3d

# 4. 浏览器打开
# http://localhost:5173 (本地)
# 或
# http://172.28.124.41:5173 (其他设备)

# 5. 开发... 修改代码会自动热重载

# 6. 完成后停止服务
3d-stop
```

---

## 需要帮助？

- 📖 查看日志: `tail -f logs/backend.log`
- 🔄 重启服务: `3d-restart`
- ❓ 查看状态: `3d-status`

Happy coding! 🚀
