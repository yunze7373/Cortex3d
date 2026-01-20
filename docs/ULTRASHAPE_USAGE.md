# UltraShape 集成使用指南

## 🎯 概述

UltraShape 是 Cortex3d 的**通用几何细化模块**，可以提升任何 3D 重建模型的输出质量：

- ✅ **InstantMesh** 输出细化
- ✅ **TripoSR** 输出细化
- ✅ **TRELLIS.2** 输出细化
- ✅ **Hunyuan3D** 系列输出细化
- ✅ **任意 GLB/OBJ 网格**细化

---

## 🚀 快速开始

### 1. 准备模型权重

```bash
# 下载 UltraShape 预训练权重
# 方法 1: 从 Hugging Face 下载
git lfs clone https://huggingface.co/infinith/UltraShape models/ultrashape

# 方法 2: 手动下载
# 访问 https://huggingface.co/infinith/UltraShape/tree/main
# 下载 ultrashape_v1.pt 到 models/ultrashape/ultrashape_v1.pt
```

### 2. 构建 Docker 容器

```bash
make build-ultrashape
```

### 3. 基础使用

```bash
# 细化任意网格文件
make refine-mesh IMAGE=character.png MESH=outputs/xxx/mesh.glb

# 快速预览（30秒，8GB显存）
make refine-fast IMAGE=character.png MESH=outputs/xxx/mesh.glb

# 高质量细化（5分钟，24GB显存）
make refine-high IMAGE=character.png MESH=outputs/xxx/mesh.glb
```

---

## 📋 完整流水线使用

### InstantMesh + UltraShape

```bash
# 一键执行：生成 + 细化
make pipeline-instantmesh-refined IMAGE=character.png

# 分步执行
make reconstruct IMAGE=character.png           # 生成粗糙网格
make refine-mesh IMAGE=character.png MESH=outputs/latest.obj
```

**输出对比**:
- `outputs/latest.obj` - InstantMesh 原始输出
- `outputs/ultrashape/latest_refined.glb` - UltraShape 细化后

### TRELLIS.2 + UltraShape

```bash
# 一键执行
make pipeline-trellis2-refined IMAGE=character.png

# 分步执行
make reconstruct-trellis2 IMAGE=character.png  # TRELLIS.2 生成
make refine-mesh IMAGE=character.png MESH=outputs/trellis2/*.glb
```

### Hunyuan3D-Omni + UltraShape

```bash
# 一键执行
make pipeline-hunyuan-refined IMAGE=character.png

# 分步执行
make reconstruct-hunyuan3d-omni IMAGE=character.png
make refine-mesh IMAGE=character.png MESH=outputs/hunyuan3d_omni/*.glb
```

### TripoSR + UltraShape

```bash
# 一键执行
make pipeline-triposr-refined IMAGE=character.png

# 分步执行
make test-triposr IMAGE=character.png
make refine-mesh IMAGE=character.png MESH=outputs/triposr/*.obj
```

---

## ⚙️ 质量预设详解

| 预设 | 时间 | 显存 | 质量 | 适用场景 |
|------|------|------|------|---------|
| `fast` | ~30秒 | 8GB | ⭐⭐⭐ | 快速预览、测试 |
| `balanced` | ~2分钟 | 16GB | ⭐⭐⭐⭐ | 通用生产（默认）|
| `high` | ~5分钟 | 24GB | ⭐⭐⭐⭐⭐ | 高质量输出 |
| `ultra` | ~10分钟 | 32GB | ⭐⭐⭐⭐⭐ | 极致质量 |

### 自定义参数

```bash
# 直接调用 Python 脚本
docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
  --image /workspace/test_images/character.png \
  --mesh /workspace/outputs/xxx/mesh.glb \
  --output /workspace/outputs/custom \
  --steps 100 \
  --num-latents 32768 \
  --octree-res 2048 \
  --guidance-scale 7.5
```

---

## 🎨 交互式 UI 使用

### 启动 Gradio 界面

```bash
make run-ultrashape-ui
```

访问 http://localhost:7863

### UI 功能

1. **上传输入**
   - 图像：参考图（可选自动去背景）
   - 网格：粗糙网格（.glb / .obj）

2. **调整参数**
   - Inference Steps: 推理步数（12-200）
   - Octree Resolution: 分辨率（64-2048）
   - Num Latents: Token 数量（1024-32768）

3. **点击运行**
   - 实时显示细化进度
   - 3D 预览细化结果

---

## 📁 批量处理

### 细化某个目录下所有网格

```bash
# 细化 InstantMesh 所有输出
make refine-existing DIR=instantmesh IMAGE=character.png PRESET=fast

# 细化 TRELLIS.2 所有输出
make refine-existing DIR=trellis2 IMAGE=character.png PRESET=balanced
```

### 自定义批量脚本

```bash
# 遍历所有模型输出并细化
for model_dir in outputs/*/; do
    for mesh in "$model_dir"*.glb "$model_dir"*.obj; do
        if [ -f "$mesh" ]; then
            make refine-mesh IMAGE=character.png MESH="$mesh" PRESET=fast
        fi
    done
done
```

---

## 🔧 高级用法

### 低显存优化

```bash
# 8GB 显存配置
docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
  --image /workspace/test_images/test.png \
  --mesh /workspace/outputs/mesh.glb \
  --preset fast \
  --low-vram  # 启用 CPU offloading
```

### 仅对已有网格细化（无需重新生成）

```bash
# 场景：你已经有了多个粗糙网格，想批量细化
ls outputs/*/mesh.glb | while read mesh; do
    make refine-mesh IMAGE=original.png MESH="$mesh" PRESET=balanced
done
```

### 参数优化建议

| 显存 | 推荐配置 |
|------|---------|
| 8GB  | `--preset fast --low-vram` |
| 16GB | `--preset balanced` |
| 24GB | `--preset high` |
| 32GB+ | `--preset ultra` 或自定义 `--octree-res 2048` |

---

## 📊 输出对比

### 质量提升维度

1. **几何细节** ⬆️
   - 尖锐边缘保留
   - 薄结构稳定性
   - 复杂拓扑支持

2. **表面质量** ⬆️
   - 移除阶梯效应
   - 平滑过渡区域
   - 减少噪声

3. **拓扑完整性** ⬆️
   - 自动修复孔洞
   - 水密性保证
   - 非流形几何处理

### 典型改进示例

```
Before (InstantMesh):          After (UltraShape):
- 顶点: 50K                    - 顶点: 200K+
- 面数: 100K                   - 面数: 400K+
- 孔洞: 可能存在               - 孔洞: 已修复
- 边缘: 模糊                   - 边缘: 锐利
```

---

## 🐛 常见问题

### Q1: 提示权重文件不存在？

```bash
# 检查路径
ls models/ultrashape/ultrashape_v1.pt

# 如果不存在，重新下载
git lfs clone https://huggingface.co/infinith/UltraShape models/ultrashape
```

### Q2: 显存不足（OOM）？

```bash
# 方案 1: 使用低显存模式
make refine-fast IMAGE=test.png MESH=mesh.glb

# 方案 2: 降低参数
docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
  --image test.png --mesh mesh.glb \
  --num-latents 4096 \  # 减少 token
  --chunk-size 1024 \   # 减小块大小
  --low-vram
```

### Q3: 细化时间太长？

```bash
# 减少推理步数（质量略降）
--steps 12  # 最快（30秒）
--steps 30  # 平衡（2分钟）
--steps 50  # 高质量（5分钟）
```

### Q4: 如何选择合适的模型组合？

| 场景 | 推荐组合 | 原因 |
|------|---------|------|
| **快速原型** | InstantMesh + UltraShape (fast) | 速度最快 |
| **高质量手办** | Hunyuan3D-Omni + UltraShape (high) | 几何+纹理双优 |
| **复杂拓扑** | TRELLIS.2 + UltraShape (balanced) | 拓扑自由度高 |
| **平衡选择** | TripoSR + UltraShape (balanced) | 锐度好 |

---

## 📚 技术细节

### UltraShape 工作原理

```
输入图像 ────┐
             ├─→ Dual Encoder (CLIP + DINOv2)
粗糙网格 ────┤
             ├─→ 表面采样（60万点）
             │
             ├─→ 体素化（固定空间锚点）
             │
             ├─→ DiT 细化（50步扩散）
             │
             └─→ Marching Cubes（高分辨率）
                    ↓
              高保真网格输出
```

### 关键技术

1. **两阶段架构**: 解耦空间定位与细节合成
2. **体素条件**: 使用粗糙网格作为空间锚点
3. **RoPE 编码**: 3D 位置嵌入
4. **水密处理**: 自动修复几何缺陷

---

## 🔗 相关链接

- **UltraShape 论文**: https://arxiv.org/pdf/2512.21185
- **GitHub**: https://github.com/PKU-YuanGroup/UltraShape-1.0
- **Hugging Face**: https://huggingface.co/infinith/UltraShape
- **项目主页**: https://pku-yuangroup.github.io/UltraShape-1.0/
- **完整研究报告**: [docs/ULTRASHAPE_RESEARCH.md](ULTRASHAPE_RESEARCH.md)

---

## 💡 最佳实践

1. **质量优先流程**
   ```bash
   # 1. 使用最佳模型生成
   make reconstruct-hunyuan3d-omni IMAGE=model.png
   
   # 2. 高质量细化
   make refine-high IMAGE=model.png MESH=outputs/hunyuan3d_omni/*.glb
   ```

2. **速度优先流程**
   ```bash
   # 1. 快速生成
   make reconstruct IMAGE=model.png
   
   # 2. 快速细化
   make refine-fast IMAGE=model.png MESH=outputs/latest.obj
   ```

3. **批量生产流程**
   ```bash
   # 1. 批量生成粗糙网格
   for img in test_images/*.png; do
       make reconstruct-hunyuan3d-omni IMAGE=$(basename $img)
   done
   
   # 2. 批量细化
   make refine-existing DIR=hunyuan3d_omni IMAGE=default.png PRESET=balanced
   ```

---

**更新日期**: 2026-01-21  
**维护者**: Cortex3d 开发团队
