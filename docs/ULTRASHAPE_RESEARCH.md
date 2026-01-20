# UltraShape 1.0 集成研究报告

## 📌 项目概览

### 基本信息
- **仓库**: [PKU-YuanGroup/UltraShape-1.0](https://github.com/PKU-YuanGroup/UltraShape-1.0)
- **开发团队**: 北京大学袁粒团队（PKU-YuanGroup）
- **发布日期**: 2025年12月25日
- **GitHub Stars**: 519 ⭐
- **论文**: [arXiv:2512.21185](https://arxiv.org/pdf/2512.21185)
- **预训练模型**: [Hugging Face - infinith/UltraShape](https://huggingface.co/infinith/UltraShape)

### 核心定位
**"High-Fidelity 3D Shape Generation via Scalable Geometric Refinement"**  
高保真 3D 形状生成 - 通过可扩展的几何细化技术

---

## 🎯 核心技术亮点

### 1. 两阶段生成流水线
UltraShape 采用**粗糙→精细**的两阶段架构：

```
Stage 1: 粗糙网格生成
  └─ 使用 Hunyuan3D-2.1 生成全局结构 (.glb/.obj)
  
Stage 2: 几何细化（UltraShape 核心）
  └─ 基于体素的扩散细化 → 高保真网格输出
```

**关键创新**: 
- **解耦空间定位与几何细节合成**
- 使用固定空间位置进行体素级细化
- 通过 RoPE 编码提供显式位置锚点

### 2. 技术架构

#### 核心组件
```python
# ultrashape/pipelines.py
class UltraShapePipeline(DiTPipeline):
    """
    主流水线类 - 基于 DiT (Diffusion Transformer)
    """
    def __call__(
        self,
        image: Union[str, Image.Image, torch.Tensor],  # 输入图像
        voxel_cond: torch.Tensor = None,               # 体素条件（来自粗糙网格）
        num_inference_steps: int = 50,                 # 推理步数（可降至12加速）
        guidance_scale: float = 5.0,                   # CFG引导强度
        octree_resolution: int = 384,                  # 八叉树分辨率
        num_chunks: int = 8000,                        # 批处理块大小
        **kwargs
    ) -> List[trimesh.Trimesh]:
        ...
```

#### 模型架构
```
ShapeVAE (变分自编码器)
├── VectsetVAE 基类
├── 编码器: 8 层 Transformer
├── 解码器: 24 层 Transformer
├── num_latents: 最多 32768 个潜在 token
└── 体素分辨率查询

RefineDiT (细化扩散 Transformer)
├── DiTBlock: 24 层
├── Flash Attention 支持
├── RoPE 3D 位置编码
├── 引导条件投影
└── 交叉注意力处理器

DualImageEncoder (双图像编码器)
├── CLIP Vision Encoder
├── DINOv2 Encoder
└── 特征融合
```

### 3. 数据处理流水线

UltraShape 的核心优势之一在于其**高质量数据处理**：

- **水密处理（Watertight Processing）**: 修复孔洞、加厚薄结构
- **质量过滤**: 移除低质量样本
- **保留细节**: 同时保持精细几何特征
- **点云采样**: 
  - 均匀采样: 30万点（前300k）
  - 尖锐边缘: 30万点（后300k）
  - 总计: 60万点/模型

---

## 🔍 与 Cortex3d 现有模型对比

| 特性 | UltraShape 1.0 | TRELLIS.2 | Hunyuan3D-2.1 | InstantMesh |
|------|----------------|-----------|---------------|-------------|
| **定位** | 几何细化器 | 端到端生成 | 端到端生成 | 快速重建 |
| **输入** | 图像 + 粗糙网格 | 单图像 | 单/多视图图像 | 多视图图像 |
| **输出** | 高保真网格 | 稀疏体素网格 | 网格 + 贴图 | 网格 + 贴图 |
| **推理步数** | 12-50 步 | ~15 步 | 10-30 步 | 1 步（前向） |
| **显存需求** | 中等（可优化） | 高（24GB shm） | 高 | 低-中 |
| **细节精度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **拓扑质量** | 高（水密） | 高（任意拓扑）| 高 | 中 |

### 核心区别

1. **UltraShape 是后处理器**，不是端到端生成器
2. **需要粗糙网格输入** - 与 Hunyuan3D-2.1 配合最佳
3. **专注几何细化** - 不处理纹理/材质
4. **可扩展架构** - 支持多种分辨率和质量权衡

---

## 🏗️ 集成方案设计

### 方案 A: 独立服务模式（推荐）

```yaml
# compose.yml 添加
services:
  ultrashape:
    build:
      context: .
      dockerfile: Dockerfile.ultrashape
    image: cortex3d-ultrashape:latest
    container_name: cortex3d-ultrashape
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    volumes:
      - ./outputs:/workspace/outputs
      - ./test_images:/workspace/test_images
      - ./models/ultrashape:/workspace/checkpoints:ro
    shm_size: 16gb
    ports:
      - "7863:7860"  # Gradio UI
    working_dir: /workspace
    command: python scripts/gradio_app.py --ckpt /workspace/checkpoints/ultrashape_v1.pt
```

**优势**: 
- 独立部署，不影响现有流水线
- 可选择性使用（高质量需求时启用）
- 易于调试和版本控制

### 方案 B: 后处理链模式

```python
# scripts/pipeline_with_refinement.py
from scripts.run_hunyuan3d import run as hunyuan_generate
from scripts.run_ultrashape import refine_mesh

def generate_refined_model(image_path: str, output_dir: str):
    """完整流水线：图像 → 粗糙网格 → 精细化"""
    
    # Stage 1: 生成粗糙网格（使用 Hunyuan3D-2.1）
    coarse_mesh = hunyuan_generate(
        image_path=image_path,
        output_dir=f"{output_dir}/coarse"
    )
    
    # Stage 2: UltraShape 细化（可选）
    if use_refinement:
        refined_mesh = refine_mesh(
            image=image_path,
            mesh=coarse_mesh,
            output_dir=f"{output_dir}/refined",
            steps=50,  # 或 12 快速模式
            octree_res=1024,
            num_latents=32768  # 或 8192 低显存
        )
        return refined_mesh
    
    return coarse_mesh
```

### 方案 C: 3DAIGC-API 集成模式

参考 [FishWoWater/3DAIGC-API](https://github.com/FishWoWater/3DAIGC-API)，该项目已实现：
- UltraShape 作为后端之一
- 统一 API 接口
- 多模型协同工作

---

## 🚀 实施路线图

### Phase 1: 基础集成（1-2周）
- [ ] 创建 `Dockerfile.ultrashape`
- [ ] 下载预训练模型到 `models/ultrashape/`
- [ ] 添加 `scripts/run_ultrashape.py` 脚本
- [ ] Docker Compose 配置和测试
- [ ] 基础文档（README 更新）

### Phase 2: 流水线整合（1周）
- [ ] 实现 Hunyuan3D → UltraShape 自动流水线
- [ ] Makefile 命令封装
- [ ] 参数优化和性能调优
- [ ] 质量 vs 速度 benchmark

### Phase 3: 高级特性（1-2周）
- [ ] 低显存优化（8GB VRAM 支持）
- [ ] 批量处理脚本
- [ ] Gradio UI 集成到主界面
- [ ] 多分辨率输出支持

### Phase 4: 生产优化（持续）
- [ ] 缓存机制（避免重复细化）
- [ ] 错误处理和回退逻辑
- [ ] 性能监控和日志
- [ ] 用户文档完善

---

## 💻 技术实现细节

### Dockerfile 设计

```dockerfile
# Dockerfile.ultrashape
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04

# 基础环境
RUN apt-get update && apt-get install -y \
    git python3.10 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ultrashape

# 克隆仓库
RUN git clone https://github.com/PKU-YuanGroup/UltraShape-1.0.git . \
    && pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121 \
    && pip install -r requirements.txt \
    && pip install git+https://github.com/ashawkey/cubvh --no-build-isolation

# 可选：训练依赖
# RUN pip install --no-build-isolation "git+https://github.com/facebookresearch/pytorch3d.git@stable"

EXPOSE 7860
CMD ["python", "scripts/gradio_app.py"]
```

### Python 脚本封装

```python
# scripts/run_ultrashape.py
"""
UltraShape 细化脚本 - 与 Cortex3d 集成
"""
import os
import sys
import torch
from PIL import Image
from omegaconf import OmegaConf

# 添加 UltraShape 到路径
ULTRASHAPE_ROOT = "/opt/ultrashape"
sys.path.insert(0, ULTRASHAPE_ROOT)

from ultrashape.pipelines import UltraShapePipeline
from ultrashape.surface_loaders import SharpEdgeSurfaceLoader
from ultrashape.utils.misc import instantiate_from_config
from ultrashape.utils import voxelize_from_point

def refine_mesh(
    image: str,
    mesh: str,
    output_dir: str = "outputs/ultrashape",
    ckpt: str = "checkpoints/ultrashape_v1.pt",
    steps: int = 50,
    scale: float = 0.99,
    octree_res: int = 1024,
    num_latents: int = 32768,
    chunk_size: int = 8000,
    seed: int = 42,
    low_vram: bool = False
):
    """细化粗糙网格到高保真输出"""
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config = OmegaConf.load("configs/infer_dit_refine.yaml")
    
    # 加载模型组件
    vae = instantiate_from_config(config.model.params.vae_config).to(device)
    dit = instantiate_from_config(config.model.params.dit_config).to(device)
    # ... (完整实现参考 scripts/infer_dit_refine.py)
    
    # 创建流水线
    pipeline = UltraShapePipeline(
        vae=vae, model=dit, scheduler=scheduler,
        conditioner=conditioner, image_processor=image_processor
    )
    
    if low_vram:
        pipeline.enable_model_cpu_offload()
    
    # 加载输入
    surface_loader = SharpEdgeSurfaceLoader(
        num_sharp_points=204800,
        num_uniform_points=204800
    )
    surface_pcd = surface_loader(mesh)  # 加载粗糙网格
    
    # 体素化条件
    voxel_cond = voxelize_from_point(
        surface_pcd,
        voxel_resolution=config.model.params.vae_config.params.voxel_query_res,
        num_latents=num_latents
    )
    
    # 运行细化
    torch.manual_seed(seed)
    outputs = pipeline(
        image=Image.open(image),
        voxel_cond=voxel_cond,
        num_inference_steps=steps,
        guidance_scale=5.0,
        octree_resolution=octree_res,
        num_chunks=chunk_size,
        output_type="trimesh"
    )
    
    # 保存结果
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "refined_mesh.glb")
    outputs[0].export(output_path)
    
    print(f"✅ 细化完成: {output_path}")
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--output", default="outputs/ultrashape")
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--low_vram", action="store_true")
    args = parser.parse_args()
    
    refine_mesh(
        image=args.image,
        mesh=args.mesh,
        output_dir=args.output,
        steps=args.steps,
        low_vram=args.low_vram
    )
```

### Makefile 命令

```makefile
# 添加到现有 Makefile

# UltraShape 容器构建
.PHONY: build-ultrashape
build-ultrashape:
	docker compose build ultrashape

# 启动 Gradio UI
.PHONY: run-ultrashape-ui
run-ultrashape-ui:
	docker compose up ultrashape

# 完整流水线（Hunyuan → UltraShape）
.PHONY: generate-refined
generate-refined:
	@echo "🎨 Stage 1: 生成粗糙网格（Hunyuan3D-2.1）..."
	$(MAKE) reconstruct-hunyuan3d-omni IMAGE=$(IMAGE)
	@echo "✨ Stage 2: 几何细化（UltraShape）..."
	docker compose run --rm ultrashape python scripts/run_ultrashape.py \
		--image /workspace/test_images/$(IMAGE) \
		--mesh /workspace/outputs/hunyuan3d_omni/coarse_mesh.glb \
		--output /workspace/outputs/refined \
		--steps 50

# 快速细化（12步）
.PHONY: refine-fast
refine-fast:
	docker compose run --rm ultrashape python scripts/run_ultrashape.py \
		--image $(IMAGE) \
		--mesh $(MESH) \
		--steps 12 \
		--low_vram
```

---

## 📊 性能优化建议

### 显存优化策略

| 配置 | 显存需求 | 质量 | 速度 | 适用场景 |
|------|---------|------|------|---------|
| **高质量** | ~24GB | ⭐⭐⭐⭐⭐ | 慢 | 最终产品 |
| `num_latents=32768`<br>`octree_res=1024`<br>`chunk_size=8000` | | | |
| **标准** | ~16GB | ⭐⭐⭐⭐ | 中 | 通用场景 |
| `num_latents=16384`<br>`octree_res=768`<br>`chunk_size=4000` | | | |
| **低显存** | ~8GB | ⭐⭐⭐ | 快 | 预览/测试 |
| `num_latents=8192`<br>`octree_res=512`<br>`chunk_size=2048`<br>`--low_vram` | | | |

### 速度 vs 质量权衡

```python
# 快速预览（~30秒）
refine_mesh(steps=12, num_latents=8192, octree_res=512)

# 标准质量（~2分钟）
refine_mesh(steps=30, num_latents=16384, octree_res=768)

# 高质量（~5分钟）
refine_mesh(steps=50, num_latents=32768, octree_res=1024)
```

---

## ⚠️ 集成注意事项

### 1. 依赖关系
```
UltraShape 1.0
├── 基于 Hunyuan3D 2.x 代码库
├── PyTorch 2.5.1 + CUDA 12.1
├── Flash Attention 2.x
├── cubvh（MC 加速）
├── pytorch3d（可选，训练用）
└── torch_cluster（可选，训练用）
```

**兼容性问题**: 
- TRELLIS.2 使用 PyTorch 2.6.0
- 需要隔离 Python 环境或容器化部署

### 2. 许可证
UltraShape 继承 **TENCENT HUNYUAN NON-COMMERCIAL LICENSE**:
- ✅ 研究和个人使用
- ✅ 教育用途
- ❌ 商业用途需额外授权
- ⚠️ 第三方组件遵循各自许可证

**建议**: Cortex3d 需明确标注商业使用限制

### 3. 模型权重
需手动下载（约 4-6GB）:
```bash
# 从 Hugging Face 下载
git lfs clone https://huggingface.co/infinith/UltraShape
cp -r UltraShape/* models/ultrashape/
```

---

## 🎓 使用示例

### 基础细化流程

```bash
# 1. 使用 Hunyuan3D 生成粗糙网格
make reconstruct-hunyuan3d-omni IMAGE=character.png

# 2. 使用 UltraShape 细化
make refine-fast MESH=outputs/hunyuan3d_omni/mesh.glb IMAGE=test_images/character.png

# 结果：outputs/refined/refined_mesh.glb
```

### 高质量流水线

```bash
# 完整流水线（自动两阶段）
make generate-refined IMAGE=character.png

# 输出对比：
# - outputs/hunyuan3d_omni/mesh.glb (粗糙)
# - outputs/refined/refined_mesh.glb (细化)
```

---

## 📈 预期效果

### 质量提升
- **几何细节**: 尖锐边缘、薄结构、复杂拓扑
- **表面平滑度**: 移除阶梯效应
- **水密性**: 修复孔洞和非流形几何
- **分辨率**: 支持 512-2048 体素分辨率

### 适用场景
1. **角色手办制作** - 需要高精度几何（Cortex3d 核心需求 ✅）
2. **建筑可视化** - 保持尖锐边缘
3. **产品设计** - 工业级表面质量
4. **3D 打印** - 水密网格准备

### 不适用场景
- 实时应用（推理时间 > 30秒）
- 纹理生成（仅处理几何）
- 低精度快速原型（可用 InstantMesh）

---

## 🔮 未来扩展方向

1. **多模型组合**
   ```
   图像 → TRELLIS.2 → UltraShape → Blender 后处理
   图像 → Hunyuan3D → UltraShape → 材质投影
   ```

2. **自适应细化**
   - 根据粗糙网格质量自动选择参数
   - 局部细化（仅细化关键区域）

3. **批量优化**
   - 并行处理多个网格
   - 共享模型权重减少显存

4. **Web UI 集成**
   - 将 Gradio UI 整合到 Cortex3d 主界面
   - 质量 vs 速度滑块

---

## 📚 参考资源

### 官方资源
- **GitHub**: https://github.com/PKU-YuanGroup/UltraShape-1.0
- **论文**: https://arxiv.org/pdf/2512.21185
- **项目页面**: https://pku-yuangroup.github.io/UltraShape-1.0/
- **模型**: https://huggingface.co/infinith/UltraShape

### 相关项目
- **Hunyuan3D-2.1**: https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
- **LATTICE**: https://arxiv.org/abs/2512.03052
- **3DAIGC-API**: https://github.com/FishWoWater/3DAIGC-API

### 社区集成
- **ComfyUI 节点**: https://github.com/Hahihula/comfyui-ultrashape
- **HUNYUAN+UltraShape 桥**: https://github.com/rethink-studios/hunyuan-ultrashape-bridge

---

## ✅ 结论与建议

### 集成价值
UltraShape 1.0 对 Cortex3d 项目有**高度价值**：

1. ✅ **补充现有流水线**: 作为后处理步骤提升质量
2. ✅ **与 Hunyuan3D 天然配对**: 都基于腾讯技术栈
3. ✅ **满足手办制作需求**: 高精度几何是核心诉求
4. ✅ **技术先进性**: 最新（2025-12）开源方案

### 实施建议
- **优先级**: 中-高（在 TRELLIS.2 稳定后集成）
- **实施方式**: 方案 A（独立服务）+ 方案 B（流水线整合）
- **时间预估**: 2-3 周完整集成
- **风险**: 低（成熟代码库 + Docker 隔离）

### 下一步行动
1. 创建 `Dockerfile.ultrashape` 和测试
2. 下载预训练权重到 `models/ultrashape/`
3. 实现 `scripts/run_ultrashape.py`
4. 编写集成文档（中文用户指南）
5. 性能 benchmark（不同配置对比）

---

**报告生成时间**: 2025-01-XX  
**负责人**: Cortex3d 开发团队  
**状态**: 待评审
