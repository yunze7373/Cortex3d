# TRELLIS.2 Setup and Configuration Guide

## Critical Information

**The Cortex3d project now uses Microsoft's TRELLIS.2 (second generation) repository.**

- **GitHub Repository**: `microsoft/TRELLIS.2` ⚠️ **Note the dot!**
- **Official Documentation**: https://github.com/microsoft/TRELLIS.2
- **Hugging Face Model**: `microsoft/TRELLIS.2-4B`
- **Python Module**: `trellis2` (not `trellis`)

## TRELLIS vs TRELLIS.2 Comparison

### Two Separate Projects

Microsoft has **TWO** distinct TRELLIS projects:

| Aspect | TRELLIS (v1) | TRELLIS.2 (v2) |
|--------|--------------|----------------|
| **Repository** | microsoft/TRELLIS | microsoft/TRELLIS.2 ⭐ |
| **Python Package** | `trellis` | `trellis2` ⭐ |
| **Release Date** | Dec 2024 | Dec 2024 (newer) |
| **Paper** | "Structured 3D Latents..." | "Native and Compact..." |
| **Model Size** | 340M - 2.0B (multiple) | 4B (single unified) |
| **Core Innovation** | Structured Latent (SLat) | O-Voxel + SLat |
| **Materials** | Basic textures | Full PBR (BCRMA) |
| **Topology Support** | Manifold surfaces | Any topology |
| **Max Resolution** | Standard | 1536³ |
| **Generation Speed** | Standard | 3-60s (512-1536³) |

### TRELLIS.2 Key Innovations

#### 1. **O-Voxel Representation**
- **Field-free sparse voxel structure** - no implicit fields
- Handles arbitrary topology:
  - ✅ Open surfaces (clothing, leaves)
  - ✅ Non-manifold geometry
  - ✅ Internal enclosed structures
- Fast conversion: <10s mesh → O-Voxel, <100ms O-Voxel → mesh

#### 2. **Full PBR Materials**
Surface attributes beyond basic color:
- **Base Color** - RGB albedo
- **Roughness** - surface roughness [0-1]
- **Metallic** - metallic property [0-1]
- **Opacity/Alpha** - transparency support

#### 3. **High Resolution**
- 512³: ~3 seconds (H100 GPU)
- 1024³: ~17 seconds
- 1536³: ~60 seconds

#### 4. **Related Packages**
- **O-Voxel**: Core mesh ↔ voxel conversion
- **FlexGEMM**: Triton-based sparse convolution
- **CuMesh**: CUDA mesh utilities (remesh, decimate, UV unwrap)

## Architecture Overview

### Pipeline Modes

TRELLIS.2 supports multiple resolution pipelines:

```python
# 512³ resolution (fastest)
pipeline.run(image, pipeline_type='512')

# 1024³ resolution (recommended)
pipeline.run(image, pipeline_type='1024')

# 1024³ cascade (higher quality)
pipeline.run(image, pipeline_type='1024_cascade')

# 1536³ cascade (maximum quality)
pipeline.run(image, pipeline_type='1536_cascade')
```

### Generation Process

```
Input Image 
    ↓
[DINOv2 Feature Extraction]
    ↓
[Sparse Structure Flow Model]  ← 64³ grid
    ↓
[Shape SLat Flow Model]        ← 512³/1024³ latent
    ↓
[Texture SLat Flow Model]      ← PBR attributes
    ↓
[O-Voxel Decoder]
    ↓
Output: MeshWithVoxel (vertices, faces, PBR attrs)
```

## Docker Configuration

### Dockerfile.trellis2

**Base Image:**
```dockerfile
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04
```

**Critical Dependencies:**
- PyTorch 2.6.0 + CUDA 12.4
- flash-attn 2.7.3 (optional performance boost)
- nvdiffrast (differentiable rendering)
- nvdiffrec (PBR split-sum renderer)
- CuMesh (CUDA mesh processing)
- FlexGEMM (efficient sparse conv)
- o-voxel (O-Voxel core library)

**Environment Variables:**
```bash
# Memory optimization
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# OpenEXR support for HDRI
OPENCV_IO_ENABLE_OPENEXR=1

# CUDA architecture targets
TORCH_CUDA_ARCH_LIST=8.6;8.9;9.0

# Attention backend (flash-attn or xformers)
ATTN_BACKEND=flash_attn

# Sparse convolution algorithm
SPCONV_ALGO=native
```

### Docker Compose Service

```yaml
trellis2:
  build:
    context: .
    dockerfile: Dockerfile.trellis2
  image: cortex3d-trellis2:latest
  container_name: cortex3d-trellis2
  
  runtime: nvidia
  
  environment:
    - NVIDIA_VISIBLE_DEVICES=all
    - PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    - OPENCV_IO_ENABLE_OPENEXR=1
    - TORCH_CUDA_ARCH_LIST=8.6;8.9;9.0
    - CUDA_VISIBLE_DEVICES=0
    - ATTN_BACKEND=flash_attn
    - SPCONV_ALGO=native
  
  shm_size: "24gb"  # Critical for high-res generation!
  
  volumes:
    - ./outputs:/workspace/outputs
    - ./test_images:/workspace/test_images
    - ./scripts:/workspace/scripts
    - hf-cache:/root/.cache/huggingface
  
  working_dir: /workspace
  stdin_open: true
  tty: true
```

**Key Configuration Notes:**

1. **shm_size: 24GB** - Required for 1024³+ resolution
2. **ATTN_BACKEND** - Use `flash_attn` (default) or `xformers` for older GPUs
3. **SPCONV_ALGO** - `native` for single-run, `auto` for repeated use
4. **hf-cache volume** - Shared across services for model caching

## Python API Usage

### Basic Usage

```python
import os
os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import cv2
import torch
from PIL import Image
from trellis2.pipelines import Trellis2ImageTo3DPipeline
from trellis2.utils import render_utils
from trellis2.renderers import EnvMap
import o_voxel

# 1. Setup Environment Map (for PBR rendering)
envmap = EnvMap(torch.tensor(
    cv2.cvtColor(cv2.imread('assets/hdri/forest.exr', cv2.IMREAD_UNCHANGED), 
                 cv2.COLOR_BGR2RGB),
    dtype=torch.float32, device='cuda'
))

# 2. Load Pipeline
pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
pipeline.cuda()

# 3. Generate 3D
image = Image.open("input.png")
mesh = pipeline.run(image)[0]  # Returns MeshWithVoxel

# 4. Simplify (nvdiffrast limit)
mesh.simplify(16777216)

# 5. Export to GLB
glb = o_voxel.postprocess.to_glb(
    vertices=mesh.vertices,
    faces=mesh.faces,
    attr_volume=mesh.attrs,
    coords=mesh.coords,
    attr_layout=mesh.layout,
    voxel_size=mesh.voxel_size,
    aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
    decimation_target=1000000,
    texture_size=4096,
    remesh=True,
    verbose=True
)
glb.export("output.glb", extension_webp=True)
```

### Advanced Parameters

```python
mesh = pipeline.run(
    image,
    seed=42,
    pipeline_type='1024_cascade',  # '512', '1024', '1024_cascade', '1536_cascade'
    sparse_structure_sampler_params={
        'steps': 12,
        'cfg_strength': 7.5,
    },
    shape_slat_sampler_params={
        'steps': 12,
        'cfg_strength': 3.0,
    },
    tex_slat_sampler_params={
        'steps': 12,
        'cfg_strength': 3.0,
    },
)[0]
```

## Makefile Commands

### Build and Run

```bash
# Build TRELLIS.2 container
make build-trellis2

# Start TRELLIS.2 service
make up-trellis2

# Run reconstruction
make reconstruct-trellis2 IMAGE=test_images/input.png

# Full pipeline (clean → build → up → test)
make pipeline-trellis2

# Stage 4 high-quality reconstruction
make stage4 IMAGE=test_images/input.png
```

### Command Details

#### `make build-trellis2`
Builds Docker image with all TRELLIS.2 dependencies:
- Clones microsoft/TRELLIS.2
- Installs PyTorch 2.6.0 + CUDA 12.4
- Compiles nvdiffrast, nvdiffrec, CuMesh, FlexGEMM, o-voxel

#### `make reconstruct-trellis2`
Runs image-to-3D generation:
```bash
make reconstruct-trellis2 IMAGE=myimage.png
# → outputs/trellis2/myimage.glb
```

#### `make stage4`
High-quality workflow using TRELLIS.2:
```bash
make stage4 IMAGE=character.png
# Uses scripts/stage3_details.py with TRELLIS.2 backend
```

## Troubleshooting

### Common Issues

#### 1. Import Error: `No module named 'trellis2'`

**Problem**: Using old TRELLIS v1 imports
```python
from trellis.pipelines import TrellisImageTo3DPipeline  # ❌ Wrong!
```

**Solution**: Update to TRELLIS.2
```python
from trellis2.pipelines import Trellis2ImageTo3DPipeline  # ✅ Correct
```

#### 2. Model Not Found

**Problem**: Using old model ID
```python
pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")  # ❌
```

**Solution**: Use TRELLIS.2 model
```python
pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")  # ✅
```

#### 3. CUDA Out of Memory (OOM)

**Solutions:**
- Increase `shm_size` to 24GB in docker-compose.yml
- Use lower resolution: `pipeline_type='512'`
- Enable memory optimization: `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
- Reduce texture size: `texture_size=2048` in `to_glb()`

#### 4. Wrong Repository Cloned

**Problem**: Dockerfile clones `microsoft/TRELLIS` instead of `microsoft/TRELLIS.2`

**Solution**: Update Dockerfile line 68:
```dockerfile
RUN git clone --recursive -b main https://github.com/microsoft/TRELLIS.2.git /opt/trellis2
```

#### 5. Flash Attention Installation Fails

**For older GPUs (V100, etc):**
```bash
# Set environment variable
export ATTN_BACKEND=xformers

# Install xformers
pip install xformers
```

## Performance Benchmarks

### Generation Time (H100 GPU)

| Resolution | Time | Quality | Use Case |
|-----------|------|---------|----------|
| 512³ | ~3s | Good | Fast iteration |
| 1024³ | ~17s | Better | Production |
| 1536³ | ~60s | Best | Final quality |

### Memory Requirements

| Pipeline | VRAM | shm_size |
|----------|------|----------|
| 512³ | ~8GB | 16GB |
| 1024³ | ~16GB | 24GB |
| 1536³ | ~24GB | 32GB |

## References

### Official Resources

- **Paper**: [arXiv:2512.14692](https://arxiv.org/abs/2512.14692) - "Native and Compact Structured Latents for 3D Generation"
- **GitHub**: https://github.com/microsoft/TRELLIS.2
- **Hugging Face**: https://huggingface.co/microsoft/TRELLIS.2-4B
- **Project Page**: https://microsoft.github.io/TRELLIS.2
- **Demo**: https://huggingface.co/spaces/microsoft/TRELLIS.2

### Related Packages

- **O-Voxel**: https://github.com/microsoft/TRELLIS.2/tree/main/o-voxel
- **FlexGEMM**: https://github.com/JeffreyXiang/FlexGEMM
- **CuMesh**: https://github.com/JeffreyXiang/CuMesh

### License

MIT License - https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE

## Migration from TRELLIS v1

If migrating from old TRELLIS setup:

1. **Update Dockerfile**:
   ```dockerfile
   # Old
   RUN git clone https://github.com/microsoft/TRELLIS.git
   
   # New
   RUN git clone https://github.com/microsoft/TRELLIS.2.git
   ```

2. **Update Python imports**:
   ```python
   # Old
   from trellis.pipelines import TrellisImageTo3DPipeline
   
   # New
   from trellis2.pipelines import Trellis2ImageTo3DPipeline
   ```

3. **Update model ID**:
   ```python
   # Old
   pipeline = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
   
   # New
   pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
   ```

4. **Update API calls**:
   ```python
   # Old
   outputs = pipeline.run(image, formats=['mesh', 'gaussian'])
   mesh = outputs['mesh'][0]
   
   # New
   mesh = pipeline.run(image)[0]  # Returns MeshWithVoxel directly
   ```

5. **Update GLB export**:
   ```python
   # Old
   from trellis.utils import postprocessing_utils
   glb = postprocessing_utils.to_glb(outputs['gaussian'][0], outputs['mesh'][0])
   
   # New
   import o_voxel
   glb = o_voxel.postprocess.to_glb(
       vertices=mesh.vertices,
       faces=mesh.faces,
       attr_volume=mesh.attrs,
       coords=mesh.coords,
       attr_layout=mesh.layout,
       voxel_size=mesh.voxel_size,
       aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
       decimation_target=1000000,
       texture_size=4096
   )
   ```

---

**Last Updated**: 2026-01-21  
**Version**: Cortex3d TRELLIS.2 Integration v1.0
