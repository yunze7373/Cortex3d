# 🔧 WebUI 访问故障排查指南

## ❌ 问题 1: 无法通过局域网 IP 访问前端

**症状**: 
- 本地访问 `http://localhost:5173` ✅ 可以
- 局域网访问 `http://172.28.124.41:5173` ❌ 无法连接

### 解决方案

#### 步骤 1: 确认前端已启动

```bash
# 查看进程
ps aux | grep "npm run dev"

# 或查看状态
3d-status
```

#### 步骤 2: 检查日志

```bash
# 查看前端日志（最后 20 行）
tail -20 ~/projects/cortex3d/logs/frontend.log

# 实时查看日志
tail -f ~/projects/cortex3d/logs/frontend.log
```

**应该看到类似的输出**:
```
➜  frontend   Git Ignored: node_modules
➜  Local:     http://localhost:5173/
➜  press h + enter to show help
```

#### 步骤 3: 直接访问前端端口

从任何设备运行：
```bash
# 测试是否能连接到 WSL 的 5173 端口
curl -I http://172.28.124.41:5173

# 应该返回 200 或 302，而不是 "Connection refused"
```

#### 步骤 4: 检查 Windows 防火墙

**如果连接被拒绝**，需要允许 Node 进程通过防火墙：

在 Windows PowerShell (管理员) 中运行：
```powershell
# 查看是否已有规则
Get-NetFirewallRule -DisplayName "Node.js" -ErrorAction SilentlyContinue

# 如果没有，添加规则（替换 node.exe 的实际路径）
$nodePath = "C:\Program Files\nodejs\node.exe"
New-NetFirewallRule -DisplayName "Node.js Dev Server" -Direction Inbound -Action Allow -Program $nodePath -Protocol TCP -LocalPort 5173

# Python 后端也需要类似规则
New-NetFirewallRule -DisplayName "Python Backend" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

---

## ❌ 问题 2: 前端加载了但无法连接到 API

**症状**:
- 前端 UI 显示正常 ✅
- 但功能不工作，控制台显示 API 错误 ❌
- 错误类似：`Failed to fetch from http://localhost:8000` 或 CORS 错误

### 解决方案

#### 步骤 1: 打开浏览器开发者工具

```
F12 或右键 → 检查 → Console 标签
```

#### 步骤 2: 查看具体错误

**错误示例 1**: `Failed to fetch http://localhost:8000/api/...`
- 表示前端试图连接到 `localhost:8000`
- 但从其他设备访问时，`localhost` 指向该设备自己，而非 WSL
- **解决**: 编辑 `frontend/.env.local` 手动指定 WSL IP

```env
# 改为 WSL 实际 IP
VITE_API_BASE_URL=http://172.28.124.41:8000
```

然后重启前端：
```bash
3d-restart
```

**错误示例 2**: `CORS error: No 'Access-Control-Allow-Origin' header`
- 表示后端没有正确配置 CORS
- **检查**: 后端是否在运行

```bash
curl -I http://172.28.124.41:8000/api/health
```

应该返回：
```
200 OK
Access-Control-Allow-Origin: *
```

#### 步骤 3: 检查后端是否运行

```bash
# 查看后端进程
ps aux | grep "uvicorn"

# 测试后端是否响应
curl http://localhost:8000/api/health

# 应该返回类似：{"status": "ok"}
```

#### 步骤 4: 检查后端日志

```bash
tail -50 ~/projects/cortex3d/logs/backend.log
```

---

## ❌ 问题 3: 前端或后端启动失败

**症状**:
- 运行 `3d` 后显示 ✅ 已启动，但实际没启动
- 或显示 `./dev.sh: line XX: command not found`

### 解决方案

#### 步骤 1: 检查日志

```bash
tail -100 ~/projects/cortex3d/logs/backend.log
tail -100 ~/projects/cortex3d/logs/frontend.log
```

#### 步骤 2: 手动启动进行调试

**后端**:
```bash
cd ~/projects/cortex3d/backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**前端**:
```bash
cd ~/projects/cortex3d/frontend
npm run dev
```

#### 步骤 3: 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: No module named 'fastapi'` | 后端依赖未安装 | `pip install -r requirements.txt` |
| `npm: command not found` | Node.js 未安装 | 安装 Node.js v18+ |
| `port 5173 is already in use` | 端口被占用 | `kill $(lsof -t -i:5173)` 或修改端口 |
| `port 8000 is already in use` | 端口被占用 | `kill $(lsof -t -i:8000)` |

---

## ❌ 问题 4: 前端一直在加载或显示空白

**症状**:
- 打开 `http://172.28.124.41:5173` 后一直加载
- 或显示完全空白

### 解决方案

#### 步骤 1: 清除浏览器缓存

- 按 `F12` 打开开发者工具
- 按 `Ctrl+Shift+Delete` 打开清除缓存窗口
- 勾选 "全部" 并清除

#### 步骤 2: 检查前端是否真的启动了

```bash
# 直接访问前端资源
curl -s http://172.28.124.41:5173 | head -20

# 应该返回 HTML 内容，而不是 Connection refused
```

#### 步骤 3: 检查是否有 JavaScript 错误

按 F12 打开开发者工具 → Console 标签，查看是否有红色错误

#### 步骤 4: 重新启动

```bash
3d-stop
sleep 2
3d
```

---

## ✅ 完整诊断命令

一键运行所有检查：

```bash
#!/bin/bash

echo "=== Cortex3d 诊断报告 ==="
echo ""

echo "1. 进程状态："
ps aux | grep -E "(uvicorn|npm run dev)" | grep -v grep
echo ""

echo "2. 端口监听："
netstat -tlnp 2>/dev/null | grep -E "(5173|8000)" || echo "未发现监听的端口"
echo ""

echo "3. 后端测试："
curl -s http://localhost:8000/api/health || echo "❌ 无法连接后端"
echo ""

echo "4. 前端测试："
curl -s -I http://localhost:5173 | head -1 || echo "❌ 无法连接前端"
echo ""

echo "5. WSL IP："
hostname -I
echo ""

echo "6. 日志中的最近错误："
echo "--- 后端日志最后 5 行 ---"
tail -5 ~/projects/cortex3d/logs/backend.log 2>/dev/null || echo "未找到后端日志"
echo ""
echo "--- 前端日志最后 5 行 ---"
tail -5 ~/projects/cortex3d/logs/frontend.log 2>/dev/null || echo "未找到前端日志"
```

保存为 `diagnose.sh`，运行：
```bash
chmod +x diagnose.sh
./diagnose.sh
```

---

## 🆘 还是无法解决？

请收集以下信息并告诉我：

1. 运行 `3d-status` 的输出
2. 前端日志最后 30 行
3. 后端日志最后 30 行  
4. `curl -I http://172.28.124.41:5173` 的输出
5. `curl -I http://172.28.124.41:8000/api/health` 的输出
6. 的浏览器开发者工具 Network 标签的截图（显示失败的请求）

命令：
```bash
# 收集诊断信息到文件
{
  echo "=== 服务状态 ==="
  3d-status
  echo ""
  echo "=== 前端日志 ==="
  tail -50 ~/projects/cortex3d/logs/frontend.log
  echo ""
  echo "=== 后端日志 ==="
  tail -50 ~/projects/cortex3d/logs/backend.log
  echo ""
  echo "=== 前端连接测试 ==="
  curl -v http://172.28.124.41:5173 2>&1 | head -20
  echo ""
  echo "=== 后端连接测试 ==="
  curl -v http://172.28.124.41:8000/api/health 2>&1 | head -20
} > ~/cortex3d-diagnostics.txt && cat ~/cortex3d-diagnostics.txt
```

然后分享 `~/cortex3d-diagnostics.txt` 的内容。

Good luck! 🚀
