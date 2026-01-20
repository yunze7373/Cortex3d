# WSL 空间管理指南

## 问题说明

Docker 在 WSL 中会不断积累：
- 停止的容器
- 废弃的镜像层
- 构建缓存
- 未使用的卷和网络

**即使删除容器和镜像，WSL 的虚拟磁盘（.vhdx）也不会自动缩小！**

## 快速清理命令

### 1. 查看当前空间使用

```bash
# 查看 Docker 空间使用情况
make docker-space

# 查看所有镜像大小
make images-size
```

### 2. 常规清理

```bash
# 清理停止的容器
make clean-containers

# 清理未使用的镜像
make clean-images

# 清理构建缓存（最占空间）
make clean-build-cache
```

### 3. 完全清理（推荐）

```bash
# 一键清理所有（保留 Hugging Face 模型缓存）
make clean-all
```

这个命令会清理：
- ✅ 停止的容器
- ✅ 未使用的镜像
- ✅ 构建缓存
- ✅ 未使用的卷（除了 hf-cache）
- ✅ 未使用的网络
- ❌ **不会删除**: Hugging Face 模型缓存（避免重新下载 GB 级模型）

## WSL 磁盘压缩（重要！）

即使清理了 Docker 数据，**WSL 虚拟磁盘不会自动缩小**。需要手动压缩。

### 方法 1: 使用 Optimize-VHD（推荐）

在 **Windows PowerShell（管理员）** 中运行：

```powershell
# 1. 关闭 WSL
wsl --shutdown

# 2. 压缩磁盘
Optimize-VHD -Path $env:LOCALAPPDATA\Docker\wsl\data\ext4.vhdx -Mode Full

# 3. 重启 Docker Desktop
```

### 方法 2: 使用 diskpart（备选）

如果 `Optimize-VHD` 不可用：

```powershell
# 1. 关闭 WSL
wsl --shutdown

# 2. 创建脚本 compact.txt
# select vdisk file="C:\Users\你的用户名\AppData\Local\Docker\wsl\data\ext4.vhdx"
# attach vdisk readonly
# compact vdisk
# detach vdisk

# 3. 运行 diskpart
diskpart /s compact.txt
```

### 方法 3: WSL 发行版压缩

压缩特定的 WSL 发行版（如 Ubuntu）：

```powershell
# 1. 关闭 WSL
wsl --shutdown

# 2. 导出发行版
wsl --export Ubuntu ubuntu-backup.tar

# 3. 注销发行版
wsl --unregister Ubuntu

# 4. 重新导入（会创建新的 .vhdx）
wsl --import Ubuntu C:\WSL\Ubuntu ubuntu-backup.tar

# 5. 删除备份
del ubuntu-backup.tar
```

## 空间使用监控

### 查看 WSL 磁盘大小

在 **PowerShell** 中：

```powershell
# 查看 Docker WSL 磁盘
Get-ChildItem $env:LOCALAPPDATA\Docker\wsl\data -Recurse | 
    Measure-Object -Property Length -Sum | 
    Select-Object @{Name="Size(GB)";Expression={[math]::Round($_.Sum/1GB,2)}}

# 查看所有 WSL 磁盘
Get-ChildItem $env:LOCALAPPDATA\Packages\*\LocalState\*.vhdx | 
    Select-Object Name, @{Name="Size(GB)";Expression={[math]::Round($_.Length/1GB,2)}}
```

### 在 WSL 内查看磁盘使用

```bash
# 查看磁盘使用
df -h /

# 查看目录大小
du -sh /var/lib/docker/*

# 查看最大的文件夹
du -h --max-depth=1 / | sort -h
```

## 最佳实践

### 1. 定期清理（每周）

```bash
# 清理构建缓存（最占空间）
make clean-build-cache

# 查看空间
make docker-space
```

### 2. 镜像重建后清理旧镜像

```bash
# 重建镜像后
make build-trellis2

# 删除旧镜像
make clean-images
```

### 3. 保留重要的卷

项目配置已自动保护 `hf-cache` 卷（Hugging Face 模型缓存）：

```yaml
volumes:
  hf-cache:  # 永远不会被清理
```

**不要手动删除此卷！** 它包含数十 GB 的预训练模型，删除后需要重新下载。

### 4. 月度完全清理

每月一次完全清理 + WSL 压缩：

```bash
# 1. 在 WSL 中清理 Docker
make clean-all

# 2. 在 PowerShell 中压缩 WSL
wsl --shutdown
Optimize-VHD -Path $env:LOCALAPPDATA\Docker\wsl\data\ext4.vhdx -Mode Full
```

## 空间占用参考

### 典型镜像大小

| 镜像 | 大小 | 说明 |
|------|------|------|
| cortex3d-instantmesh | ~15GB | InstantMesh + 依赖 |
| cortex3d-trellis | ~18GB | TRELLIS (第一版) |
| cortex3d-trellis2 | ~20GB | TRELLIS (官方) + 所有扩展 |
| cortex3d-hunyuan3d | ~16GB | Hunyuan3D 2.0 |
| cortex3d-hunyuan3d-2.1 | ~17GB | Hunyuan3D 2.1 |
| nvidia/cuda:12.4.0 | ~6GB | 基础 CUDA 镜像 |

### 典型缓存大小

| 项目 | 大小 | 位置 |
|------|------|------|
| Hugging Face 模型 | 30-50GB | `/root/.cache/huggingface` (hf-cache 卷) |
| Docker 构建缓存 | 10-20GB | Docker 内部 |
| pip 缓存 | 2-5GB | `/root/.cache/pip` |
| 输出文件 | 变化 | `/workspace/outputs` |

### WSL 磁盘增长示例

```
初始安装:          ~30GB
添加 5 个镜像:     ~100GB
使用 1 个月:       ~150GB  (构建缓存 + 模型)
完全清理后:        ~80GB   (仅保留必要镜像和模型)
WSL 压缩后:        ~60GB   (回收未使用空间)
```

## 紧急情况：空间不足

如果 WSL 磁盘快满了（>90%）：

### 1. 立即清理

```bash
# 停止所有容器
docker stop $(docker ps -aq)

# 完全清理
make clean-all

# 手动删除构建缓存
docker builder prune -a -f

# 删除所有未使用的数据
docker system prune -a --volumes -f
```

⚠️ **警告**: 最后一条命令会删除 **所有** 卷，包括 `hf-cache`！

### 2. 压缩 WSL（Windows PowerShell）

```powershell
wsl --shutdown
Optimize-VHD -Path $env:LOCALAPPDATA\Docker\wsl\data\ext4.vhdx -Mode Full
```

### 3. 临时扩展 WSL 磁盘（如果需要）

编辑 `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=32GB
processors=8
swap=16GB
localhostForwarding=true

# 限制磁盘大小（可选）
# 默认是动态增长，最大 256GB
```

## 自动化清理脚本

创建每周清理脚本 `cleanup.sh`:

```bash
#!/bin/bash
echo "🧹 开始每周清理..."

# 清理构建缓存
docker builder prune -a -f

# 清理未使用的镜像
docker image prune -f

# 清理停止的容器
docker container prune -f

# 显示空间使用
echo "📊 清理后的空间:"
docker system df

echo "✅ 清理完成！"
```

添加到 crontab:

```bash
# 每周日凌晨 3 点运行
0 3 * * 0 /path/to/cleanup.sh
```

## 常见问题

### Q: 为什么删除了镜像，WSL 磁盘还那么大？

**A**: WSL 虚拟磁盘（.vhdx）只会增长不会缩小。需要手动运行 `Optimize-VHD` 压缩。

### Q: 可以安全删除 hf-cache 卷吗？

**A**: 可以，但不推荐。它包含 30-50GB 的预训练模型，删除后需要重新下载，非常耗时。

### Q: 构建缓存真的占那么多空间吗？

**A**: 是的！Docker 构建缓存可以轻松超过 20GB。每次修改 Dockerfile 都会创建新的层。

### Q: 如何只清理某个项目的镜像？

**A**: 
```bash
# 清理所有 cortex3d 相关镜像
docker images | grep cortex3d | awk '{print $3}' | xargs docker rmi -f
```

### Q: WSL 磁盘压缩需要多久？

**A**: 取决于磁盘大小，通常 5-30 分钟。100GB 的磁盘约需 10-15 分钟。

## 推荐清理频率

| 操作 | 频率 | 命令 |
|------|------|------|
| 查看空间 | 每天 | `make docker-space` |
| 清理构建缓存 | 每周 | `make clean-build-cache` |
| 清理未使用镜像 | 每两周 | `make clean-images` |
| 完全清理 | 每月 | `make clean-all` |
| WSL 压缩 | 每月 | `Optimize-VHD` |

## 相关资源

- [Docker 空间管理文档](https://docs.docker.com/config/pruning/)
- [WSL 磁盘管理](https://learn.microsoft.com/en-us/windows/wsl/disk-space)
- [Optimize-VHD 文档](https://learn.microsoft.com/en-us/powershell/module/hyper-v/optimize-vhd)
