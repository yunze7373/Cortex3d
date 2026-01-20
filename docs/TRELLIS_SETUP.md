# TRELLIS 配置说明

## 重要说明

**虽然项目中使用 `trellis2` 作为容器名和脚本名，但实际使用的是 Microsoft 官方的 TRELLIS 仓库。**

- GitHub 仓库: `microsoft/TRELLIS` (不是 `TRELLIS.2`)
- 官方文档: https://github.com/microsoft/TRELLIS
- Hugging Face 模型: `microsoft/TRELLIS-image-large`

## 架构概述

TRELLIS (TRi-perspective view encoding for REconstructing 3D from a singLe Image in Seconds) 是微软开发的高质量图像到3D转换系统。

### 核心特性
- **Structured Latent (SLatent)** 表示 - 统一的3D表示方法
- **多格式输出** - Mesh、Gaussian Splatting、Radiance Field
- **高质量几何** - 保持细节和结构
- **快速生成** - 在秒级完成推理

## Docker 配置

### Dockerfile.trellis2

```dockerfile
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04
```

**关键依赖:**
- PyTorch 2.6.0 + CUDA 12.4
- flash-attn 2.7.3 (可选，提高性能)
- nvdiffrast v0.4.0 (微分渲染)
- nvdiffrec (带渲染工具)
- CuMesh (网格处理)
- FlexGEMM (GEMM优化)
- spconv (稀疏卷积)

**环境变量:**
```bash
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
OPENCV_IO_ENABLE_OPENEXR=1
TORCH_CUDA_ARCH_LIST=8.6;8.9;9.0
ATTN_BACKEND=flash-attn
SPCONV_ALGO=native
```

### Docker Compose

```yaml
trellis2:
  build:
    dockerfile: Dockerfile.trellis2
  shm_size: "24gb"  # 增加到24GB以支持高分辨率
  environment:
    - PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    - OPENCV_IO_ENABLE_OPENEXR=1
    - TORCH_CUDA_ARCH_LIST=8.6;8.9;9.0
    - CUDA_VISIBLE_DEVICES=0
    - ATTN_BACKEND=flash-attn
    - SPCONV_ALGO=native
```

## Python API 使用

### 导入

```python
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import render_utils, postprocessing_utils
from trellis.representations import Gaussian, MeshExtractResult
```

### 加载模型

```python
# 从 Hugging Face 加载
pipeline = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
pipeline.cuda()

# 或从本地路径
pipeline = TrellisImageTo3DPipeline.from_pretrained("/path/to/TRELLIS-image-large")
```

### 生成3D模型

```python
from PIL import Image

# 加载图像
image = Image.open("input.png")

# 运行生成
outputs = pipeline.run(
    image,
    seed=42,
    formats=['mesh', 'gaussian'],  # 可选: 'radiance_field'
    preprocess_image=True,  # 自动去背景
    sparse_structure_sampler_params={
        "steps": 12,
        "cfg_strength": 7.5,
    },
    slat_sampler_params={
        "steps": 12,
        "cfg_strength": 3,
    }
)

# 访问结果
mesh = outputs['mesh'][0]
gaussian = outputs['gaussian'][0]
```

### 导出模型

```python
# 使用 TRELLIS 的后处理工具
glb = postprocessing_utils.to_glb(
    gaussian,
    mesh,
    simplify=500000,      # 目标面数
    texture_size=2048,    # 纹理分辨率
    verbose=True
)
glb.export("output.glb")
```

### 渲染预览

```python
import imageio
import numpy as np

# 渲染网格和高斯
video_mesh = render_utils.render_video(mesh)['normal']
video_gs = render_utils.render_video(gaussian)['color']

# 合并并保存
video = [np.concatenate([frame_mesh, frame_gs], axis=1) 
         for frame_mesh, frame_gs in zip(video_mesh, video_gs)]
imageio.mimsave("preview.mp4", video, fps=30)
```

## 使用方法

### 通过 Makefile

```bash
# 构建容器
make build-trellis2

# 启动容器
make up-trellis2

# 运行生成
make reconstruct-trellis2

# 完整流程（生成 + Blender后处理）
make pipeline-trellis2
```

### 直接运行脚本

```bash
# 在容器内
docker compose exec trellis2 python3 /workspace/scripts/run_trellis2.py \
    /workspace/test_images/input.png \
    --output /workspace/outputs/trellis2 \
    --model microsoft/TRELLIS-image-large \
    --seed 42 \
    --decimation 500000 \
    --texture-size 2048
```

### 通过 reconstructor.py

```bash
python scripts/reconstructor.py \
    test_images/input.png \
    --algo trellis2 \
    --quality high \
    --output-dir outputs
```

## 质量预设

| 预设 | 简化面数 | 纹理分辨率 | 生成时间 | 内存需求 |
|------|---------|-----------|---------|---------|
| balanced | 500,000 | 2048 | ~30s | ~16GB |
| high | 1,000,000 | 4096 | ~60s | ~24GB |
| ultra | 2,000,000 | 4096 | ~90s | ~32GB |

## 可用模型

### Image-to-3D
- `microsoft/TRELLIS-image-large` - 大型图像到3D模型（推荐）
- `microsoft/TRELLIS-image-small` - 小型快速模型

### Text-to-3D（可选）
- `microsoft/TRELLIS-text-xlarge` - 文本到3D模型

## 常见问题

### 1. 导入错误

**错误**: `ModuleNotFoundError: No module named 'trellis2'`

**解决**: 确保使用正确的导入路径 `from trellis.pipelines import ...`

### 2. GPU内存不足

**错误**: `CUDA out of memory`

**解决方案**:
- 降低质量预设 (使用 `balanced` 而不是 `ultra`)
- 增加 `shm_size` 到 24-32GB
- 设置环境变量 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`

### 3. flash-attn 安装失败

**说明**: flash-attn 是可选的，失败不影响功能

**解决**: Dockerfile 已配置为可选安装，会自动回退到 xformers 或默认实现

### 4. 模型下载慢

**解决方案**:
- 使用 Hugging Face 镜像
- 预先下载模型到本地并使用本地路径
- 配置代理

## 性能优化

### 1. 注意力机制
```bash
# 使用 flash-attn (最快)
export ATTN_BACKEND=flash-attn

# 使用 xformers (备选)
export ATTN_BACKEND=xformers
```

### 2. 稀疏卷积
```bash
# 首次运行设置为 native 避免基准测试
export SPCONV_ALGO=native

# 多次运行可设置为 auto 自动优化
export SPCONV_ALGO=auto
```

### 3. CUDA 架构
```bash
# 为特定GPU架构编译（更快）
export TORCH_CUDA_ARCH_LIST="8.9"  # RTX 4090
export TORCH_CUDA_ARCH_LIST="8.6"  # RTX 3090
```

## 技术细节

### Structured Latent (SLatent)

TRELLIS 使用 SLatent 作为统一的3D表示：
- **稀疏结构** - 首先生成稀疏的3D结构
- **属性填充** - 然后填充每个体素的属性（颜色、法线等）
- **多格式解码** - 可以解码为不同的3D表示形式

### 两阶段生成

1. **稀疏结构采样** (`sparse_structure_sampler`)
   - 生成3D对象的粗略结构
   - 使用 Flow Matching

2. **SLatent 采样** (`slat_sampler`)
   - 填充详细属性
   - 生成高质量纹理和几何

## 参考资源

- **GitHub**: https://github.com/microsoft/TRELLIS
- **论文**: [即将发布]
- **Hugging Face**: https://huggingface.co/microsoft/TRELLIS-image-large
- **项目主页**: https://trellis3d.github.io/

## 更新日志

### 2026-01-20
- ✅ 修正仓库 URL (microsoft/TRELLIS)
- ✅ 更新导入路径
- ✅ 修正模型 ID
- ✅ 增加环境变量配置
- ✅ 添加 Makefile 命令
- ✅ 增加 shm_size 到 24GB
- ✅ 完善文档说明
