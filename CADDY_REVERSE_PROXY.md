# Caddy 反向代理配置指南

## 概述

使用 Caddy 作为反向代理，让你可以直接访问 `https://3d.home.lan/` 而不需要指定端口 `:5173`。

### 访问方式对比

| 方式 | URL | 是否需要端口 |
|------|-----|------------|
| ❌ 直接访问 Vite | http://3d.home.lan:5173 | ✓ 需要 |
| ✅ 使用 Caddy 代理 | https://3d.home.lan/ | ✗ 不需要 |

---

## 快速启动（3 步）

### Step 1：安装 Caddy

在 WSL 中运行：

```bash
cd ~/projects/cortex3d
chmod +x install-caddy.sh
./install-caddy.sh
```

**预期输出**：
```
📦 使用 apt 安装 Caddy...
...
✅ Caddy 安装成功！

🚀 现在可以运行 dev.sh 了：
   3d
```

### Step 2：启动开发环境

```bash
3d
```

或者：
```bash
3d-restart
```

现在 Caddy 会自动启动！你会看到：

```
🚀 无端口访问（推荐 ⭐）：
   📱 前端：https://3d.home.lan/
   📖 文档：https://3d.home.lan:8000/docs
```

### Step 3：在浏览器中访问

```
https://3d.home.lan/
```

就这样！无需端口号 ✓

---

## 工作原理

```
┌─────────────────────────────────────────────────────────┐
│ 你的浏览器                                               │
│ https://3d.home.lan/                                    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓
        ┌─────────────────────┐
        │ Caddy 反向代理      │
        │ 80/443 端口         │
        │ (Caddyfile 配置)    │
        └─────────┬───────────┘
                  │
                  ↓
        ┌─────────────────────┐
        │ Vite 前端服务       │
        │ localhost:5173      │
        └─────────────────────┘
```

**Caddyfile 配置** (`Cortex3d/Caddyfile`)：

```
3d.home.lan {
    reverse_proxy localhost:5173
    encode gzip
}
```

含义：
- `3d.home.lan` — 监听这个域名
- `reverse_proxy localhost:5173` — 代理到 Vite
- `encode gzip` — 启用 gzip 压缩

---

## 访问列表

启动后，所有这些 URL 都可以访问：

### ✅ 推荐使用（无端口）

```
https://3d.home.lan/              ⭐ 最简洁
https://3d.home.lan:8000/docs     API 文档  
```

### 🔧 带端口（备用）

```
http://localhost:5173              本地开发
https://localhost:5173             本地 HTTPS
http://3d.home.lan:5173            旧方式（仍可用）
https://3d.home.lan:5173           旧方式 HTTPS  
```

---

## 常见问题

### Q1：Caddy 需要 sudo 吗？

**A**：是的。Caddy 需要 `sudo` 来使用 80/443 端口。`dev.sh` 会自动处理这个。

> 如果每次启动都要输入密码，可以配置 sudoers 允许 caddy 命令无密码运行（可选）

### Q2：Caddy 启动失败怎么办？

**A**：查看日志：

```bash
tail -f logs/caddy.log
```

常见原因：
- **已有进程占用 80/443 端口** — 关闭其他反向代理（nginx、Apache 等）
- **Caddy 未正确安装** — 重新运行 `install-caddy.sh`
- **权限问题** — 确保 Caddy 是以 sudo 运行的

### Q3：什么是 Caddyfile？

**A**：反向代理配置文件（`Cortex3d/Caddyfile`）：

```
3d.home.lan {
    reverse_proxy localhost:5173
    encode gzip
}
```

如果你有多个本地服务，可以扩展这个文件：

```
3d.home.lan {
    reverse_proxy localhost:5173
}

api.home.lan {
    reverse_proxy localhost:8000
}

portainer.home.lan {
    reverse_proxy localhost:9000
}
```

然后重启 Caddy 即可。

### Q4：是否需要 HTTPS 证书？

**A**：Caddy 会自动为你处理 HTTPS！

- 在试错环境中，Caddy 会生成**自签名证书**（无需手动操作）
- 证书自动更新，你无需担心过期

### Q5：如何停止 Caddy？

**A**：运行：

```bash
3d-stop
```

或者手动停止：

```bash
sudo kill $(cat .caddy.pid)
```

### Q6：iPhone 上无法访问怎么办？

**A**：确保：
1. iPhone 连接了 Tailscale
2. DNS 能解析 `3d.home.lan`
3. 从 Safari 打开 `https://3d.home.lan/`
4. 接受自签名证书警告

### Q7：多个项目可以用 Caddy 吗？

**A**：可以！编辑 `Caddyfile`：

```
3d.home.lan {
    reverse_proxy localhost:5173
}

blog.home.lan {
    reverse_proxy localhost:3000
}

admin.home.lan {
    reverse_proxy localhost:8080
}
```

然后重启 Caddy：
```bash
3d-restart
```

---

## 清除和重置

如果需要完全清除 Caddy：

```bash
# 停止 Caddy
3d-stop

# 卸载 Caddy（可选）
sudo apt-get remove caddy

# 清理日志
rm logs/caddy.log
```

---

## 更多信息

- **Caddy 官方文档**：https://caddyserver.com/docs/
- **反向代理配置**：https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- **本项目 Caddyfile**：[Cortex3d/Caddyfile](Caddyfile)

---

## 总结

✅ **最终目标实现**：
```bash
3d                          # 一键启动
# 然后访问：
https://3d.home.lan/        # 无端口访问！
```

所有设备（电脑、iPhone、iPad、Android）都可以用这个 URL 访问。
