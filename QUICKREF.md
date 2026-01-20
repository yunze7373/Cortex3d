# 🚀 Cortex3d 快速命令参考

## 📦 构建容器

```bash
make build-instantmesh        # InstantMesh（快速）
make build-trellis2           # TRELLIS.2（高质量）
make build-hunyuan3d-omni     # Hunyuan3D-Omni（全能）
make build-ultrashape         # UltraShape（细化器）⭐ NEW
```

## 🎨 单步生成

```bash
# InstantMesh（快速，~2分钟）
make reconstruct IMAGE=test.png

# TRELLIS.2（高质量，~5分钟）
make reconstruct-trellis2 IMAGE=test.png

# Hunyuan3D-Omni（平衡，~3分钟）
make reconstruct-hunyuan3d-omni IMAGE=test.png

# TripoSR（锐度高，~1分钟）
make test-triposr IMAGE=test.png
```

## ✨ UltraShape 细化（NEW）

```bash
# 快速细化（30秒，8GB VRAM）
make refine-fast IMAGE=ref.png MESH=outputs/xxx/mesh.glb

# 标准细化（2分钟，16GB VRAM）⭐ 推荐
make refine-mesh IMAGE=ref.png MESH=outputs/xxx/mesh.glb

# 高质量细化（5分钟，24GB VRAM）
make refine-high IMAGE=ref.png MESH=outputs/xxx/mesh.glb
```

## 🔄 完整流水线（生成 + 细化）

```bash
# InstantMesh + UltraShape（快速流程）
make pipeline-instantmesh-refined IMAGE=test.png

# Hunyuan3D + UltraShape（推荐）⭐
make pipeline-hunyuan-refined IMAGE=test.png

# TRELLIS.2 + UltraShape（最高质量）
make pipeline-trellis2-refined IMAGE=test.png

# TripoSR + UltraShape（锐度优先）
make pipeline-triposr-refined IMAGE=test.png
```

## 📊 质量 vs 速度对比

| 流程 | 总时间 | 显存 | 几何质量 | 适用场景 |
|------|--------|------|---------|---------|
| InstantMesh only | ~2min | 8GB | ⭐⭐⭐ | 快速预览 |
| InstantMesh + UltraShape | ~4min | 16GB | ⭐⭐⭐⭐ | 通用生产 |
| Hunyuan + UltraShape | ~8min | 24GB | ⭐⭐⭐⭐⭐ | 手办制作 |
| TRELLIS.2 + UltraShape | ~10min | 24GB | ⭐⭐⭐⭐⭐ | 极致质量 |

## 🎯 推荐工作流

### 快速迭代
```bash
make pipeline-instantmesh-refined IMAGE=draft.png
# ✓ 4分钟完成
# ✓ 适合概念验证
```

### 生产流程
```bash
make pipeline-hunyuan-refined IMAGE=final.png
# ✓ 8分钟完成
# ✓ 带纹理 + 高质量几何
# ✓ 适合 3D 打印
```

### 极致质量
```bash
make pipeline-trellis2-refined IMAGE=final.png
# ✓ 10分钟完成
# ✓ 最高几何精度
# ✓ 适合复杂模型
```

## 🔧 批量处理

```bash
# 批量细化目录下所有网格
make refine-existing DIR=hunyuan3d_omni IMAGE=ref.png PRESET=fast

# 批量生成多个图片
for img in test_images/*.png; do
    make reconstruct IMAGE=$(basename $img)
done
```

## 🖥️ 交互式 UI

```bash
# 启动 UltraShape Gradio UI
make run-ultrashape-ui
# 访问 http://localhost:7863
```

## 🧹 清理空间

```bash
make clean-containers    # 清理容器
make clean-images        # 清理镜像
make clean-all          # 完全清理
make wsl-compact        # 压缩 WSL（Windows）
```

## 📖 获取帮助

```bash
# 查看完整文档
cat docs/ULTRASHAPE_USAGE.md        # UltraShape 使用指南
cat docs/ULTRASHAPE_RESEARCH.md     # 技术细节
cat docs/TRELLIS2_SETUP.md          # TRELLIS.2 配置

# 查看主 README
cat README.md
```

---

**快速记忆口诀**:
- 🏃 快速用 **InstantMesh**
- 🎯 生产用 **Hunyuan + UltraShape**
- 💎 极致用 **TRELLIS.2 + UltraShape**
- ✨ 所有模型都可用 **UltraShape 细化**！
