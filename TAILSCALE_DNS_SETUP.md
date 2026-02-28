# Tailscale + 群晖 DNS 配置指南

## 你的 Tailscale 网络设备清单

从 `tailscale status` 输出整理的可用设备：

| 主机名 | Tailscale IP | 类型 | 状态 | 建议记录 |
|--------|-------------|------|------|---------|
| **hanyz-pc (WSL)** ⭐ | `100.90.173.90` | Linux | active | `cortex3d`, `api` → 这台 |
| hanstation (群晖 NAS) | `100.100.19.19` | Linux | active | `nas`, `disk`, `synology` |
| mac-mini | `100.123.60.65` | macOS | active | `mac`, `server` |
| raspberrypi | `100.79.4.53` | Linux | active | `pi`, `rpi` |
| han-wrt (WiFi 路由器) | `100.111.0.126` | Linux | active | `router`, `wrt` |
| lok-standard-pc | `100.98.163.28` | Linux | active | `pve`, `virtualization` |
| oneplus-in2011 (手机) | `100.111.244.90` | Android | active | `phone` |

其他离线设备暂时不配置。

---

## 快速配置步骤

### 📍 Step 1：在群晖 DSM 中打开 DNS Server 套件

```
DSM 主菜单 → DNS Server → 打开
```

### 📍 Step 2：创建主区域

1. 左侧菜单 **区域** → 点击 **新增**
2. 选择 **Master 区域（正向查找）**
3. 填写 **域名**：`home.lan`
4. 点击 **确定** 创建

### 📍 Step 3：添加 A 记录

在 `home.lan` 区域下，逐个添加这些记录：

#### **前端/开发工具**
```
名称：cortex3d          类型：A    IP：100.90.173.90
名称：cortex           类型：A    IP：100.90.173.90
名称：api              类型：A    IP：100.90.173.90
```

#### **NAS 相关**
```
名称：nas              类型：A    IP：100.100.19.19
名称：synology         类型：A    IP：100.100.19.19
名称：disk             类型：A    IP：100.100.19.19
```

#### **其他服务**
```
名称：mac              类型：A    IP：100.123.60.65
名称：pi               类型：A    IP：100.79.4.53
名称：router           类型：A    IP：100.111.0.126
```

**在 DNS Server 界面的操作**：
1. 点击 `home.lan` 区域进入
2. 点击 **新增** → **A 记录**
3. 填写 **名称** 和 **IP 地址**
4. 点击 **确定**

---

### 📍 Step 4：Tailscale 端配置 Split DNS

这一步让所有 Tailscale 设备自动识别你的自定义域名。

#### 方式 A：Web 界面（推荐，最简单）

1. 打开 https://login.tailscale.com/admin/dns
2. 找到 **Nameservers** 部分
3. 点击 **Add nameserver** → **Custom...**
4. 填写：
   ```
   Nameserver：100.100.19.19
   ✓ Restrict to domain
   Domain：home.lan
   ```
5. 保存

#### 方式 B：命令行（更快）

如果你有 Tailscale 管理权限，可以在任何设备上运行：

```bash
# 添加自定义 DNS 服务器
tailscale set --accept-dns=true

# （可选）查看当前 DNS 配置
tailscale status --peers
```

---

### 📍 Step 5：测试验证

在任意 Tailscale 设备上测试（WSL、Mac、Android 手机都可以）：

```bash
# 测试 DNS 解析
nslookup cortex3d.home.lan
dig cortex3d.home.lan
ping cortex3d.home.lan

# 如果能返回 100.90.173.90，说明成功！
```

**浏览器访问**：
```
http://cortex3d.home.lan:5173      # Cortex3d 前端
http://cortex3d.home.lan:8000      # Cortex3d API
http://cortex3d.home.lan:8000/docs # FastAPI 文档
```

---

## 🚀 完成后的使用体验

启动 Cortex3d：
```bash
3d        # 一键启动，前端+后端
```

然后从任意 Tailscale 设备访问：
- **Windows 电脑**：http://cortex3d.home.lan:5173
- **Mac**：http://cortex3d.home.lan:5173
- **iPhone 12**：Safari 打开 http://cortex3d.home.lan:5173
- **Android 手机**：浏览器打开 http://cortex3d.home.lan:5173
- **iPad**：http://cortex3d.home.lan:5173

所有设备，**无需任何额外配置，开箱即用**。

---

## 💡 进阶：添加更多服务域名

你可以继续添加其他服务的域名记录，例如：

```
名称：aiproxy         类型：A    IP：100.90.173.90   (如果 AiProxy 在 WSL 上)
名称：redis          类型：A    IP：100.100.19.19   (如果 Redis 在 NAS 上)
名称：postgres       类型：A    IP：100.100.19.19   (数据库)
名称：minio          类型：A    IP：100.100.19.19   (存储)
```

然后就能用 `http://redis.home.lan`、`http://postgres.home.lan` 等访问。

---

## ❓ 常见问题

### Q1：域名解析不了？
**A**：检查：
1. `nslookup cortex3d.home.lan` 返回 100.90.173.90 吗？
2. Tailscale Split DNS 是否生效？运行 `tailscale status` 看是否有 DNS 提示
3. 群晖 DNS Server 套件是否开启？

### Q2：添加了第一个域名，后续怎么加？
**A**：同样的步骤，在 `home.lan` 区域下继续 **新增** A 记录即可。

### Q3：我想用 `cortex.home` 而不是 `cortex3d.home.lan`？
**A**：在 Step 2 创建区域时，填写 `home` 而不是 `home.lan`，然后重复上述步骤。

### Q4：iPhone 上无法访问怎么办？
**A**：确认 iPhone 已连接 Tailscale，并在 Tailscale App 内部打开 **Allow local network access**。

### Q5：WSL IP 换了，域名会失效吗？
**A**：不会。Tailscale IP 是固定的（100.90.173.90），不会因为换网络而改变。这就是用 Tailscale IP 而不是局域网 IP 的原因。

---

## 📋 相关文件

- `dev.sh` — 启动脚本，已支持显示 Tailscale IP 和域名地址
- `backend/main.py` — 已配置 CORS 允许 `cortex3d.home.lan` 域名访问

运行 `3d` 启动后，`dev.sh` 会显示所有可用的访问方式：

```
┌────────────────────────────────────────────────────────┐
│ 🖥️  本地访问：http://localhost:5173                     │
│ 🌐 局域网 IP：http://100.90.173.90:5173                │
│ 🔗 Tailscale IP：http://100.90.173.90:5173            │
│ 🌍 域名访问：http://cortex3d.home.lan:5173             │
└────────────────────────────────────────────────────────┘
```

---

## 🎯 总结

只需 **5 分钟**，你就能拥有：
- ✅ 自定义局域网域名系统
- ✅ 所有 Tailscale 设备自动生效
- ✅ 无需记住 IP，用域名访问一切服务
- ✅ 换网络、用 VPN 时，IP 不变，域名永远生效
