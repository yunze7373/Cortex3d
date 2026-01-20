# 🧹 快速清理参考卡

## 日常使用命令

```bash
# 查看 Docker 空间使用
make docker-space

# 查看所有镜像大小
make images-size
```

## 快速清理（推荐）

```bash
# 清理构建缓存（最占空间，每周运行）
make clean-build-cache

# 完全清理（保留模型，每月运行）
make clean-all
```

## 交互式清理

```bash
# 运行交互式清理工具
bash scripts/cleanup.sh
```

## WSL 磁盘压缩

### 在 Windows PowerShell (管理员) 中运行：

```powershell
# 方法1: 使用自动化脚本（推荐）
.\scripts\wsl-compact.ps1

# 方法2: 手动执行
wsl --shutdown
Optimize-VHD -Path $env:LOCALAPPDATA\Docker\wsl\data\ext4.vhdx -Mode Full
```

## 典型清理流程

### 每周维护（5分钟）

```bash
# 1. 查看空间
make docker-space

# 2. 清理构建缓存
make clean-build-cache

# 3. 清理旧容器
make clean-containers
```

### 月度深度清理（30分钟）

```bash
# 1. WSL 中完全清理
make clean-all

# 2. PowerShell 中压缩磁盘
.\scripts\wsl-compact.ps1

# 3. 重启 Docker Desktop
```

## 空间节省预期

| 操作 | 预期节省 | 时间 |
|------|---------|------|
| `clean-build-cache` | 10-20GB | 1分钟 |
| `clean-images` | 5-15GB | 2分钟 |
| `clean-all` | 15-30GB | 5分钟 |
| WSL 压缩 | 20-50GB | 10-30分钟 |

## ⚠️ 重要提示

1. **不要删除 `hf-cache` 卷** - 包含 30-50GB 预训练模型
2. **定期压缩 WSL 磁盘** - 否则磁盘只增不减
3. **清理前确认没有重要数据** - 输出文件在 `outputs/` 目录

## 紧急情况：磁盘快满了

```bash
# 1. 立即停止所有容器
docker stop $(docker ps -aq)

# 2. 快速清理（1分钟）
make clean-build-cache

# 3. 完全清理（5分钟）
make clean-all

# 4. WSL 压缩（30分钟）
# 在 PowerShell 中运行
.\scripts\wsl-compact.ps1
```

## 查看详细文档

- [完整 WSL 空间管理指南](./WSL_SPACE_MANAGEMENT.md)
- [TRELLIS 配置说明](./TRELLIS_SETUP.md)

---

💡 **技巧**: 将 `make docker-space` 添加到你的日常工作流，随时了解空间使用情况！
