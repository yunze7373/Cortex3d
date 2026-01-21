# Cortex3d - AI 驱动的 3D 手办自动化流水线

> **最新更新 (2026-01-21)**: 🎉 集成 **UltraShape 1.0** 通用几何细化器！可提升所有模型输出质量

## 📖 项目简介

Cortex3d 是一个工业级 AI 3D 打印手办自动化流水线，整合了多个最先进的图像到 3D 模型生成技术。

### 🎯 核心能力

- **多模型支持**: InstantMesh、TripoSR、TRELLIS.2、Hunyuan3D 系列
- **✨ 通用细化**: UltraShape 1.0 可细化任何模型的输出
- **高质量输出**: 支持 2K-4K 纹理、高分辨率几何（最高 2048 体素）
- **完整流水线**: 从图像输入到打印就绪 STL
- **Docker 化部署**: 一键启动，开箱即用

---

## 🚀 快速开始

### 前置要求

- Docker Desktop / WSL2 + Docker
- NVIDIA GPU（CUDA 12.1+）
- 16GB+ VRAM（推荐 24GB 用于高质量输出）

### 基础使用

```bash
# 1. 克隆仓库（含子模块）
git clone --recursive https://github.com/yunze7373/Cortex3d.git
cd Cortex3d

# 2. 构建 Docker 容器（选择你需要的模型）
make build-instantmesh    # InstantMesh（快速）
make build-trellis2       # TRELLIS.2（高质量）
make build-hunyuan3d-omni # Hunyuan3D-Omni（全能）
make build-ultrashape     # UltraShape（细化器）

# 3. 运行重建
make reconstruct IMAGE=your_image.png

# 4. 细化输出（可选）
make refine-mesh IMAGE=your_image.png MESH=outputs/latest.obj
```

### 一键完整流水线

```bash
# InstantMesh + UltraShape 细化
make pipeline-instantmesh-refined IMAGE=character.png

# Hunyuan3D-Omni + UltraShape 细化（推荐）
make pipeline-hunyuan-refined IMAGE=character.png

# TRELLIS.2 + UltraShape 细化（最高质量）
make pipeline-trellis2-refined IMAGE=character.png
```

---

## 🏗️ 支持的模型

| 模型 | 速度 | 质量 | 纹理 | 拓扑 | 特点 |
|------|------|------|------|------|------|
| **InstantMesh** | ⚡⚡⚡ | ⭐⭐⭐ | ✅ | 流形 | 快速原型 |
| **TripoSR** | ⚡⚡ | ⭐⭐⭐⭐ | ✅ | 流形 | 锐利边缘 |
| **TRELLIS.2** | ⚡ | ⭐⭐⭐⭐⭐ | ❌ | 任意 | O-Voxel 技术 |
| **Hunyuan3D-Omni** | ⚡⚡ | ⭐⭐⭐⭐ | ✅ | 流形 | 视频输入支持 |
| **UltraShape** | - | +⭐⭐ | ❌ | 水密 | 后处理细化器 |

### 模型选择建议

- **快速预览**: InstantMesh
- **手办制作**: Hunyuan3D-Omni + UltraShape
- **高精度几何**: TRELLIS.2 + UltraShape
- **平衡选择**: TripoSR + UltraShape

---

## ✨ UltraShape 通用细化

UltraShape 是 Cortex3d 的**通用后处理器**，可以显著提升任何 3D 模型的几何质量。

### 核心优势

- ✅ **通用兼容**: 支持所有模型输出（.glb / .obj）
- ✅ **高保真几何**: 保留尖锐边缘、薄结构、复杂拓扑
- ✅ **自动修复**: 水密处理、孔洞修复
- ✅ **灵活配置**: 4 档质量预设（fast/balanced/high/ultra）

### 使用方法

```bash
# 快速细化（30秒，8GB VRAM）
make refine-fast IMAGE=test.png MESH=outputs/mesh.glb

# 标准细化（2分钟，16GB VRAM）
make refine-mesh IMAGE=test.png MESH=outputs/mesh.glb

# 高质量细化（5分钟，24GB VRAM）
make refine-high IMAGE=test.png MESH=outputs/mesh.glb
```

### 批量细化

```bash
# 细化某个目录下所有网格
make refine-existing DIR=hunyuan3d_omni IMAGE=ref.png PRESET=balanced
```

📚 **完整文档**: [docs/ULTRASHAPE_USAGE.md](docs/ULTRASHAPE_USAGE.md)  
🔬 **技术细节**: [docs/ULTRASHAPE_RESEARCH.md](docs/ULTRASHAPE_RESEARCH.md)

---

## 📋 完整流水线示例

### 示例 1: 高质量手办制作

```bash
# 1. Hunyuan3D-Omni 生成（带纹理）
make reconstruct-hunyuan3d-omni IMAGE=character.png

# 2. UltraShape 几何细化
make refine-high IMAGE=character.png \
    MESH=outputs/hunyuan3d_omni/character.glb

# 3. Blender 后处理（可选）
make stage4 MESH=outputs/ultrashape/character_refined.glb

# 输出: 
# - outputs/hunyuan3d_omni/character.glb (原始)
# - outputs/ultrashape/character_refined.glb (细化)
# - outputs/final_print.stl (打印就绪)
```

### 示例 2: 快速迭代流程

```bash
# 使用 InstantMesh 快速生成 + 快速细化
make pipeline-instantmesh-refined IMAGE=draft.png

# 约 2-3 分钟完成
```

### 示例 3: 极致质量流程

```bash
# TRELLIS.2 高质量生成 + Ultra 细化
make reconstruct-trellis2 IMAGE=final.png

docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
    --image /workspace/test_images/final.png \
    --mesh /workspace/outputs/trellis2/final.glb \
    --preset ultra \
    --octree-res 2048

# 约 15-20 分钟完成，最高质量
```

---

## 🛠️ Makefile 命令参考

### 重建命令

```bash
# InstantMesh（快速）
make reconstruct IMAGE=test.png

# TRELLIS.2（高质量）
make reconstruct-trellis2 IMAGE=test.png

# Hunyuan3D-Omni（全能）
make reconstruct-hunyuan3d-omni IMAGE=test.png

# TripoSR（锐度高）
make test-triposr IMAGE=test.png
```

### UltraShape 细化

```bash
# 基础细化
make refine-mesh IMAGE=ref.png MESH=outputs/xxx/mesh.glb

# 预设选择
make refine-fast  # 快速（30s）
make refine-mesh  # 标准（2min）
make refine-high  # 高质量（5min）

# 完整流水线
make pipeline-instantmesh-refined IMAGE=test.png
make pipeline-trellis2-refined IMAGE=test.png
make pipeline-hunyuan-refined IMAGE=test.png
```

### Docker 管理

```bash
# 构建
make build-ultrashape
make build-trellis2

# 查看日志
make logs SVC=ultrashape

# 清理空间
make clean-all
make wsl-compact
```

---

## 📂 项目结构

```
Cortex3d/
├── scripts/
│   ├── run_ultrashape.py       # UltraShape 细化脚本
│   ├── run_trellis2.py         # TRELLIS.2 生成脚本
│   ├── run_hunyuan3d_omni.py   # Hunyuan3D-Omni 脚本
│   └── reconstructor.py        # 统一重建接口
├── docs/
│   ├── ULTRASHAPE_USAGE.md     # UltraShape 使用指南
│   ├── ULTRASHAPE_RESEARCH.md  # UltraShape 技术报告
│   ├── TRELLIS2_SETUP.md       # TRELLIS.2 配置文档
│   └── WSL_SPACE_MANAGEMENT.md # WSL 空间管理
├── outputs/                     # 输出目录
│   ├── instantmesh/
│   ├── trellis2/
│   ├── hunyuan3d_omni/
│   └── ultrashape/             # 细化输出
├── models/
│   └── ultrashape/             # UltraShape 权重
│       └── ultrashape_v1.pt    # 需手动下载
├── Dockerfile.ultrashape       # UltraShape 容器
├── compose.yml                 # Docker Compose 配置
└── Makefile                    # 统一命令入口
```

---

## 📥 模型权重下载

### UltraShape 权重（必需）

```bash
# 方法 1: Git LFS
git lfs clone https://huggingface.co/infinith/UltraShape models/ultrashape

# 方法 2: 手动下载
# 访问 https://huggingface.co/infinith/UltraShape/tree/main
# 下载 ultrashape_v1.pt (约 4-6GB) 到 models/ultrashape/
```

### 其他模型（自动下载）

其他模型权重会在首次运行时自动从 Hugging Face 下载到 Docker 卷 `hf-cache`。

---

## ⚙️ 高级配置

### 显存优化

| 显存 | 推荐配置 |
|------|---------|
| 8GB  | `make refine-fast --low-vram` |
| 16GB | `make refine-mesh` (balanced) |
| 24GB | `make refine-high` |
| 32GB+ | Ultra 预设或自定义参数 |

### 自定义参数示例

```bash
docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
  --image /workspace/test_images/test.png \
  --mesh /workspace/outputs/mesh.glb \
  --steps 100 \
  --num-latents 32768 \
  --octree-res 2048 \
  --guidance-scale 7.5 \
  --output /workspace/outputs/custom
```

---

## 🐛 故障排除

### UltraShape 权重未找到

```bash
# 检查
ls models/ultrashape/ultrashape_v1.pt

# 重新下载
git lfs clone https://huggingface.co/infinith/UltraShape models/ultrashape
```

### 显存不足（OOM）

```bash
# 方案 1: 降低质量预设
make refine-fast IMAGE=test.png MESH=mesh.glb

# 方案 2: 启用低显存模式
--low-vram --num-latents 4096 --chunk-size 1024
```

### Docker 空间不足

```bash
# 清理 Docker
make clean-all

# 压缩 WSL 磁盘（Windows）
make wsl-compact
```

更多问题参考：[docs/ULTRASHAPE_USAGE.md](docs/ULTRASHAPE_USAGE.md) 常见问题章节

---

## 📚 文档索引

### 🚀 快速开始
- **迭代 360° 生成指南**: [docs/ITERATIVE_360_GUIDE_V2.md](docs/ITERATIVE_360_GUIDE_V2.md) ⭐ *Gemini 官方最佳实践*
- **图像编辑快速开始**: [docs/IMAGE_EDITING_QUICKSTART.md](docs/IMAGE_EDITING_QUICKSTART.md) 🎨 *使用 Gemini 编辑/修复角色图像*
- **Gemini 图像编辑集成**: [docs/GEMINI_IMAGE_EDITING_INTEGRATION.md](docs/GEMINI_IMAGE_EDITING_INTEGRATION.md) 📖 *完整设计文档*
- **图像编辑速查表**: [docs/GEMINI_IMAGE_EDITING_CHEATSHEET.md](docs/GEMINI_IMAGE_EDITING_CHEATSHEET.md) 📋 *快速参考*
- **快速参考**: [docs/QUICKREF.md](docs/QUICKREF.md)

### 🔧 模型配置
- **UltraShape 使用指南**: [docs/ULTRASHAPE_USAGE.md](docs/ULTRASHAPE_USAGE.md)
- **UltraShape 技术研究**: [docs/ULTRASHAPE_RESEARCH.md](docs/ULTRASHAPE_RESEARCH.md)
- **TRELLIS.2 配置**: [docs/TRELLIS2_SETUP.md](docs/TRELLIS2_SETUP.md)
- **TRELLIS.2 安装**: [docs/TRELLIS_SETUP.md](docs/TRELLIS_SETUP.md)
- **WSL 空间管理**: [docs/WSL_SPACE_MANAGEMENT.md](docs/WSL_SPACE_MANAGEMENT.md)
- **清理参考**: [docs/CLEANUP_QUICK_REFERENCE.md](docs/CLEANUP_QUICK_REFERENCE.md)

### 📋 项目规划
- **项目规范**: [docs/开发平台介绍.md](docs/开发平台介绍.md)
- **需求文档**: [docs/需求.md](docs/需求.md)
- **v2.0 方案**: [docs/AI%203D%20打印手办自动化流水线%20v2.0%20(工业级增强版).md](docs/AI%203D%20打印手办自动化流水线%20v2.0%20(工业级增强版).md)
- **v2.0 增强**: [docs/AI%203D%20打印手办自动化流水线%20v2.0：工业级增强方案.md](docs/AI%203D%20打印手办自动化流水线%20v2.0：工业级增强方案.md)
- **v2.1 功能**: [docs/AI%203D%20打印手办自动化流水线%20v2.1.md](docs/AI%203D%20打印手办自动化流水线%20v2.1.md)

---

## 🔗 相关资源

### 子项目

- **InstantMesh**: https://github.com/TencentARC/InstantMesh
- **TripoSR**: https://github.com/VAST-AI-Research/TripoSR
- **TRELLIS.2**: https://github.com/microsoft/TRELLIS.2
- **Hunyuan3D**: https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
- **UltraShape**: https://github.com/PKU-YuanGroup/UltraShape-1.0

### 论文

- **UltraShape 1.0**: [arXiv:2512.21185](https://arxiv.org/pdf/2512.21185)
- **TRELLIS.2**: Microsoft Research
- **InstantMesh**: Tencent ARC Lab

---

## 📄 许可证

- **Cortex3d**: MIT License
- **UltraShape**: TENCENT HUNYUAN NON-COMMERCIAL LICENSE（非商业使用）
- **其他子模块**: 遵循各自许可证

⚠️ **商业使用注意**: UltraShape 和部分子模块仅限非商业使用，商业场景需获取额外授权。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📞 联系方式

- **Issues**: https://github.com/yunze7373/Cortex3d/issues
- **Discussions**: https://github.com/yunze7373/Cortex3d/discussions

---

**最后更新**: 2026-01-21  
**版本**: v2.1 (集成 UltraShape)
