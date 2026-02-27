# Cortex3d → ComfyUI 改造方案

> **文档版本**: v1.0  
> **生成日期**: 2026-02-28  
> **适用项目**: Cortex3d — AI 3D 打印手办自动化流水线

---

## 目录

1. [项目审查总结](#1-项目审查总结)
2. [改造目标与原则](#2-改造目标与原则)
3. [架构设计](#3-架构设计)
4. [节点清单与规格](#4-节点清单与规格)
5. [数据类型定义](#5-数据类型定义)
6. [工作流模板](#6-工作流模板)
7. [目录结构](#7-目录结构)
8. [实施计划（分阶段）](#8-实施计划分阶段)
9. [Docker 集成方案](#9-docker-集成方案)
10. [风险与缓解](#10-风险与缓解)
11. [与现有前端的兼容策略](#11-与现有前端的兼容策略)

---

## 1. 项目审查总结

### 1.1 项目概况

Cortex3d 是一个**端到端工业级 AI 3D 打印手办自动化流水线**，当前架构：

```
┌────────────────┐  NDJSON Stream  ┌────────────────┐  Docker/CLI  ┌─────────────────┐
│  React SPA     │ ◄──────────────► │  FastAPI 后端   │ ───────────► │  GPU 容器集群     │
│  (Vite+TS)     │                  │  (Python)      │              │  (9个Docker服务)  │
└────────────────┘                  └────────────────┘              └─────────────────┘
     前端 UI                         API 网关 + 编排                   模型推理
```

### 1.2 现有能力矩阵

| 能力域 | 功能 | 实现模块 |
|--------|------|----------|
| **图像生成** | 文生多视角、图生多视角 | `gemini_generator.py`, `aiproxy_client.py` |
| **本地图像生成** | 文生图/图生图 | `zimage_server.py` (Z-Image-Turbo 6B) |
| **图像编辑** | 语义/外观编辑 | `qwen_image_edit_server.py` (20B) |
| **图像处理** | 切割、去背景、增强 | `image_processor.py`, `image_enhancer.py` |
| **3D 重建** | 7种算法 | InstantMesh / TripoSR / TRELLIS.2 / Hunyuan3D 系列 |
| **几何精化** | 通用网格细化 | UltraShape |
| **后处理** | 水密化、缩放、减面、STL导出 | `blender_factory.py` |
| **服装编辑** | 提取、换装、合成 | Gemini API + prompt工程 |
| **风格迁移** | 9种预设风格 | 风格prompt + 多视角生成 |

### 1.3 现有不足 (ComfyUI 可解决的问题)

| 问题 | 影响 | ComfyUI 解决方式 |
|------|------|-----------------|
| **管线固定** — `reconstructor.py` 硬编码了处理顺序 | 用户无法灵活组合算法 | 节点拖拽自由组合 |
| **参数黑盒** — 质量预设隐藏了底层参数 | 无法精细调优 | 每个参数暴露为节点属性 |
| **无中间结果预览** — 全管线执行后才看到结果 | 调试困难 | 每个节点可独立预览 |
| **无分支/并行** — 一次只能走一条管线 | 无法对比不同算法 | 工作流分支 → 合并对比 |
| **前后端强耦合** — React UI 绑定特定 API | 扩展新能力需改前后端 | 节点即能力，自动生成UI |
| **无工作流持久化** — 流水线参数未保存 | 实验不可复现 | JSON 工作流保存/导入 |

---

## 2. 改造目标与原则

### 2.1 核心目标

1. **将 Cortex3d 全部能力封装为 ComfyUI 自定义节点包** (`ComfyUI-Cortex3d`)
2. **保持与现有 Docker 容器集群的兼容** — 不重写模型代码，通过 RPC/CLI 调用
3. **支持 ComfyUI WebSocket 实时预览** — 每个节点输出都可在画布预览
4. **预提供 5 个开箱即用的工作流模板**
5. **保留现有 React 前端** 作为轻量入口（可选）

### 2.2 改造原则

| 原则 | 说明 |
|------|------|
| **最小入侵** | 不修改现有 `scripts/` 代码，节点层作为 adapter 调用 |
| **单一职责** | 每个节点做一件事，通过组合实现复杂管线 |
| **类型安全** | 定义 ComfyUI 自定义类型（IMAGE, MESH, PROMPT 等） |
| **渐进式** | 分3阶段实施，每阶段独立可用 |
| **双模运行** | 支持本地直接执行和 Docker 远程调用两种模式 |

---

## 3. 架构设计

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ComfyUI Server                                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              ComfyUI-Cortex3d 节点包                          │    │
│  │                                                              │    │
│  │  ┌─────────────┐ ┌────────────┐ ┌──────────────┐           │    │
│  │  │ Prompt 节点  │ │ 图像生成   │ │ 图像处理节点  │           │    │
│  │  │  Group       │ │ 节点 Group │ │  Group       │           │    │
│  │  └──────┬──────┘ └─────┬──────┘ └──────┬───────┘           │    │
│  │         │              │               │                     │    │
│  │  ┌──────▼──────┐ ┌────▼──────┐ ┌──────▼───────┐           │    │
│  │  │ 3D重建节点   │ │ 后处理    │ │ 服装/风格     │           │    │
│  │  │  Group       │ │ 节点 Group│ │ 编辑 Group   │           │    │
│  │  └──────┬──────┘ └─────┬─────┘ └──────────────┘           │    │
│  │         │              │                                     │    │
│  │  ┌──────▼──────────────▼──────┐                             │    │
│  │  │  Docker Bridge Layer       │  ← 容器调用抽象层            │    │
│  │  │  (docker compose exec)     │                             │    │
│  │  └──────────────┬─────────────┘                             │    │
│  └─────────────────┼────────────────────────────────────────────┘    │
│                    │                                                  │
└────────────────────┼──────────────────────────────────────────────────┘
                     │
        ┌────────────▼────────────────────────┐
        │         Docker Compose 集群          │
        │  ┌──────────┐ ┌──────────┐          │
        │  │instantmesh│ │ trellis2 │ ...      │
        │  └──────────┘ └──────────┘          │
        │  ┌──────────┐ ┌──────────┐          │
        │  │hunyuan-omni│ │ultrashape│         │
        │  └──────────┘ └──────────┘          │
        └─────────────────────────────────────┘
```

### 3.2 节点通信模式

```python
# 模式 A: 本地调用 (ComfyUI 与模型在同一 GPU 服务器)
class InstantMeshNode:
    def execute(self, image, ...):
        from scripts.run_instantmesh import main as run_im
        return run_im(image, ...)  # 直接 Python 调用

# 模式 B: Docker 远程调用 (ComfyUI 在前端机, 模型在 GPU 集群)
class InstantMeshNode:
    def execute(self, image, ...):
        result = docker_bridge.exec(
            service="instantmesh",
            script="scripts/run_instantmesh.py",
            args={"input": image, ...}
        )
        return result  # 通过 Docker exec + 文件挂载
    
# 模式 C: HTTP API 调用 (已有 Flask/Gradio 服务)
class UltraShapeNode:
    def execute(self, image, mesh, ...):
        result = http_client.post(
            f"http://ultrashape:7863/api/predict",
            files={"image": image, "mesh": mesh}
        )
        return result
```

---

## 4. 节点清单与规格

### 4.1 Prompt 构建节点 (6个)

#### `Cortex3d_MultiviewPromptBuilder`
```yaml
category: "Cortex3d/Prompt"
display_name: "多视角提示词构建"
inputs:
  character_description: [STRING, multiline, "角色描述文本"]
  style: [COMBO, ["realistic", "anime", "cartoon", "3d-render", "chibi", "sketch", "watercolor", "pixel-art", "claymation"]]
  view_mode: [COMBO, ["4", "6", "8", "custom"], default: "4"]
  custom_views: [STRING, optional, "自定义视角列表 (如: front,back,left,right,top)"]
  subject_only: [BOOLEAN, default: true, "仅提取主体（去环境）"]
  with_props: [BOOLEAN, default: false, "保留道具"]
outputs:
  prompt: [STRING, "完整的多视角生成提示词"]
  view_config: [CORTEX_VIEW_CONFIG, "视角配置对象"]
mapping: config.build_multiview_prompt()
```

#### `Cortex3d_ImageRefPromptBuilder`
```yaml
category: "Cortex3d/Prompt"
display_name: "图像参考提示词构建"
inputs:
  character_description: [STRING, multiline]
  view_mode: [COMBO, ["4", "6", "8"]]
  style: [COMBO, [...同上...]]
  subject_only: [BOOLEAN, default: true]
outputs:
  prompt: [STRING]
  view_config: [CORTEX_VIEW_CONFIG]
mapping: config.build_image_reference_prompt()
```

#### `Cortex3d_StrictCopyPromptBuilder`
```yaml
category: "Cortex3d/Prompt"
display_name: "严格复制提示词构建"
inputs:
  view_mode: [COMBO, ["4", "6", "8"]]
  style: [COMBO, [...]]
  user_instruction: [STRING, optional]
outputs:
  prompt: [STRING]
mapping: config.build_strict_copy_prompt()
```

#### `Cortex3d_CompositePromptBuilder`
```yaml
category: "Cortex3d/Prompt"
display_name: "合成提示词构建"
inputs:
  instruction: [STRING, multiline, "合成指令"]
  composite_type: [COMBO, ["clothing", "accessory", "full_outfit", "general"]]
  style: [COMBO, [...]]
outputs:
  prompt: [STRING]
mapping: config.build_composite_prompt()
```

#### `Cortex3d_NegativePrompt`
```yaml
category: "Cortex3d/Prompt"
display_name: "负面提示词"
inputs:
  categories: [COMBO, ["default", "face", "body", "background", "all"], multiSelect: true]
outputs:
  negative_prompt: [STRING]
mapping: config.get_negative_prompt()
```

#### `Cortex3d_PromptPreset`
```yaml
category: "Cortex3d/Prompt"
display_name: "预设角色模板"
inputs:
  preset: [COMBO, ["apocalypse_businessman", "zombie_santa", "custom"]]
  custom_yaml: [STRING, optional]
outputs:
  character_description: [STRING]
  style: [STRING]
  view_mode: [STRING]
mapping: prompts/presets/*.yaml
```

---

### 4.2 图像生成节点 (5个)

#### `Cortex3d_GeminiGenerator`
```yaml
category: "Cortex3d/Generate"
display_name: "Gemini 多视角生成"
inputs:
  prompt: [STRING, "来自 PromptBuilder"]
  api_key: [STRING, "Gemini API Key (或从环境变量)"]
  reference_image: [IMAGE, optional, "参考图像"]
  model: [COMBO, ["gemini-3-pro-image-preview", "gemini-2.5-flash-image"]]
  resolution: [COMBO, ["1K", "2K", "4K"], default: "2K"]
  use_strict_mode: [BOOLEAN, default: false]
  view_config: [CORTEX_VIEW_CONFIG, optional]
outputs:
  multiview_image: [IMAGE, "多视角拼接图"]
  individual_views: [IMAGE_LIST, "各视角独立图像列表"]
mapping: gemini_generator.generate_character_views()
execution: 云端 API 调用 (非GPU)
```

#### `Cortex3d_AiProxyGenerator`
```yaml
category: "Cortex3d/Generate"
display_name: "AiProxy 图像生成"
inputs:
  prompt: [STRING]
  token: [STRING, "AiProxy Token"]
  reference_image: [IMAGE, optional]
  resolution: [COMBO, ["1K", "2K", "4K"]]
  negative_prompt: [STRING, optional]
outputs:
  image: [IMAGE]
mapping: aiproxy_client.generate_image_via_proxy()
execution: 云端 API 调用
```

#### `Cortex3d_ZImageGenerator`
```yaml
category: "Cortex3d/Generate"
display_name: "Z-Image 本地文生图"
inputs:
  prompt: [STRING]
  width: [INT, default: 1024, min: 256, max: 2048, step: 64]
  height: [INT, default: 1024, min: 256, max: 2048, step: 64]
  steps: [INT, default: 8, min: 1, max: 50]
  seed: [INT, default: -1, "-1 = 随机"]
  server_url: [STRING, default: "http://localhost:8199"]
outputs:
  image: [IMAGE]
mapping: zimage_client.ZImageClient.generate()
execution: Docker 容器 `zimage` (GPU)
```

#### `Cortex3d_ZImageImg2Img`
```yaml
category: "Cortex3d/Generate"
display_name: "Z-Image 本地图生图"
inputs:
  image: [IMAGE, "输入图像"]
  prompt: [STRING]
  strength: [FLOAT, default: 0.7, min: 0.0, max: 1.0, step: 0.05]
  steps: [INT, default: 8]
  server_url: [STRING, default: "http://localhost:8199"]
outputs:
  image: [IMAGE]
mapping: zimage_client.ZImageClient.img2img()
```

#### `Cortex3d_QwenImageEdit`
```yaml
category: "Cortex3d/Generate"
display_name: "Qwen 图像编辑"
inputs:
  image: [IMAGE, "输入图像"]
  prompt: [STRING, "编辑指令 (中/英文)"]
  cfg_scale: [FLOAT, default: 4.0, min: 1.0, max: 20.0]
  steps: [INT, default: 50, min: 10, max: 100]
  seed: [INT, default: -1]
  server_url: [STRING, default: "http://localhost:8200"]
outputs:
  image: [IMAGE]
mapping: qwen_image_edit_client.QwenImageEditClient.edit()
execution: Docker 容器 `qwen-image-edit` (GPU)
```

---

### 4.3 图像处理节点 (5个)

#### `Cortex3d_MultiviewCutter`
```yaml
category: "Cortex3d/Process"
display_name: "多视角图像切割"
inputs:
  multiview_image: [IMAGE, "四宫格/六宫格/八宫格图像"]
  view_mode: [COMBO, ["4", "6", "8"], default: "4"]
  remove_background: [BOOLEAN, default: true]
outputs:
  views: [IMAGE_LIST, "独立视角图像列表"]
  front_view: [IMAGE, "正面视角 (用于3D重建)"]
mapping: image_processor.py
```

#### `Cortex3d_BackgroundRemover`
```yaml
category: "Cortex3d/Process"
display_name: "背景移除"
inputs:
  image: [IMAGE]
  method: [COMBO, ["rembg-u2net", "rembg-isnet"], default: "rembg-u2net"]
  alpha_threshold: [INT, default: 127, min: 0, max: 255]
outputs:
  image: [IMAGE, "RGBA 去背景图像"]
  mask: [MASK, "背景遮罩"]
mapping: rembg
```

#### `Cortex3d_FragmentCleaner`
```yaml
category: "Cortex3d/Process"
display_name: "碎片清除"
inputs:
  image: [IMAGE, "RGBA 图像"]
  min_fragment_ratio: [FLOAT, default: 0.01, "最小碎片面积比"]
outputs:
  image: [IMAGE, "清除碎片后的图像"]
mapping: image_processor.remove_small_fragments()
```

#### `Cortex3d_ImageEnhancer`
```yaml
category: "Cortex3d/Process"
display_name: "图像增强 (超分+人脸)"
inputs:
  image: [IMAGE]
  scale: [COMBO, [2, 4], default: 2]
  target_size: [INT, default: 1024]
  use_realesrgan: [BOOLEAN, default: true]
  use_gfpgan: [BOOLEAN, default: true]
outputs:
  image: [IMAGE, "增强后的高分辨率图像"]
mapping: image_enhancer.enhance_image()
```

#### `Cortex3d_ImagePreview` (辅助节点)
```yaml
category: "Cortex3d/Process"
display_name: "图像预览"
inputs:
  images: [IMAGE_LIST, "图像列表"]
  labels: [STRING, optional, "标签列表 (逗号分隔)"]
outputs:
  (无 - 仅预览)
note: 利用 ComfyUI 内置预览能力，以网格形式显示多视角
```

---

### 4.4 3D 重建节点 (6个)

#### `Cortex3d_InstantMesh`
```yaml
category: "Cortex3d/3D Reconstruction"
display_name: "InstantMesh 3D 重建"
inputs:
  image: [IMAGE, "单张正面图像 (去背景)"]
  config: [COMBO, ["instant-mesh-hq", "instant-mesh-large"], default: "instant-mesh-hq"]
  diffusion_steps: [INT, default: 75, min: 10, max: 200]
  guidance_scale: [FLOAT, default: 7.5, min: 1.0, max: 20.0]
  seed: [INT, default: 42]
  texture_resolution: [INT, default: 1024, min: 512, max: 4096, step: 256]
  export_texture: [BOOLEAN, default: true]
outputs:
  mesh: [CORTEX_MESH, "OBJ 网格"]
  texture: [IMAGE, optional, "纹理图像"]
  preview: [IMAGE, "渲染预览"]
execution: Docker 容器 `instantmesh` (≥8GB VRAM)
mapping: run_instantmesh.py
```

#### `Cortex3d_TripoSR`
```yaml
category: "Cortex3d/3D Reconstruction"
display_name: "TripoSR 3D 重建"
inputs:
  image: [IMAGE, "单张正面图像 (去背景)"]
  mc_resolution: [INT, default: 256, min: 128, max: 512, "Marching Cubes 分辨率"]
  bake_texture: [BOOLEAN, default: true]
  texture_resolution: [INT, default: 2048, min: 512, max: 4096]
outputs:
  mesh: [CORTEX_MESH, "OBJ 网格"]
  texture: [IMAGE, optional]
  preview: [IMAGE]
execution: Docker 容器 `instantmesh` (共享, ≥8GB VRAM)
mapping: run_triposr.py
```

#### `Cortex3d_TRELLIS2`
```yaml
category: "Cortex3d/3D Reconstruction"
display_name: "TRELLIS.2 3D 重建"
inputs:
  image: [IMAGE, "单张图像"]
  model: [COMBO, ["microsoft/TRELLIS.2-4B"], default: "microsoft/TRELLIS.2-4B"]
  ss_steps: [INT, default: 12, min: 5, max: 50, "稀疏结构采样步数"]
  slat_steps: [INT, default: 12, min: 5, max: 50, "结构化潜在采样步数"]
  decimation: [INT, default: 500000, min: 100000, max: 2000000, "目标面数"]
  texture_size: [INT, default: 2048, min: 512, max: 4096]
  generate_texture: [BOOLEAN, default: true]
  seed: [INT, default: 42]
outputs:
  mesh: [CORTEX_MESH, "GLB 网格"]
  preview_video: [VIDEO, optional, "PBR 预览视频"]
  preview: [IMAGE]
execution: Docker 容器 `trellis2` (≥16GB VRAM)
mapping: run_trellis2.py
```

#### `Cortex3d_Hunyuan3D`
```yaml
category: "Cortex3d/3D Reconstruction"
display_name: "Hunyuan3D 重建"
inputs:
  image: [IMAGE]
  version: [COMBO, ["2.0", "2.1"], default: "2.1"]
  no_texture: [BOOLEAN, default: false]
  quality: [COMBO, ["balanced", "high", "ultra"], default: "balanced"]
outputs:
  mesh: [CORTEX_MESH, "GLB 网格"]
  preview: [IMAGE]
execution: Docker 容器 `hunyuan3d` 或 `hunyuan3d-2.1` (≥16GB VRAM)
mapping: run_hunyuan3d.py
```

#### `Cortex3d_Hunyuan3DOmni`
```yaml
category: "Cortex3d/3D Reconstruction"
display_name: "Hunyuan3D-Omni 多模态重建"
inputs:
  image: [IMAGE]
  control_type: [COMBO, ["none", "pose", "point", "voxel", "bbox"], default: "none"]
  control_data: [CORTEX_CONTROL, optional, "控制数据 (JSON/PLY/NPY)"]
  octree_resolution: [INT, default: 512, min: 256, max: 1024]
  guidance_scale: [FLOAT, default: 5.5, min: 1.0, max: 20.0]
  steps: [INT, default: 50, min: 10, max: 100]
  use_ema: [BOOLEAN, default: true]
  use_flashvdm: [BOOLEAN, default: false]
outputs:
  mesh: [CORTEX_MESH, "GLB 网格"]
  preview: [IMAGE]
execution: Docker 容器 `hunyuan3d-omni` (≥10GB VRAM)
mapping: run_hunyuan3d_omni.py
```

#### `Cortex3d_MultiviewReconstruction`
```yaml
category: "Cortex3d/3D Reconstruction"
display_name: "多视角 3D 重建 (InstantMesh)"
inputs:
  views: [IMAGE_LIST, "多视角图像列表 (4/6张)"]
  config: [COMBO, ["instant-mesh-hq", "instant-mesh-large"]]
  seed: [INT, default: 42]
outputs:
  mesh: [CORTEX_MESH, "OBJ 网格"]
  texture: [IMAGE, optional]
  preview: [IMAGE]
execution: Docker 容器 `instantmesh` (≥8GB VRAM)
mapping: run_instantmesh_multiview.py
```

---

### 4.5 后处理节点 (4个)

#### `Cortex3d_UltraShapeRefiner`
```yaml
category: "Cortex3d/Post-Process"
display_name: "UltraShape 几何精化"
inputs:
  image: [IMAGE, "参考图像 (用于条件引导)"]
  mesh: [CORTEX_MESH, "原始网格 (GLB/OBJ)"]
  preset: [COMBO, ["lowmem", "fast", "balanced", "high", "ultra"], default: "balanced"]
  low_vram: [BOOLEAN, default: false, "CPU offloading (VRAM < 10GB 时开启)"]
outputs:
  mesh: [CORTEX_MESH, "精化后的 GLB 网格"]
  preview: [IMAGE, "精化前后对比"]
execution: Docker 容器 `ultrashape` (5-32GB VRAM 按预设)
mapping: run_ultrashape.py
note: |
  VRAM 参考:
  - lowmem: 5GB (15步, 3072 latents, 320 octree)
  - fast:   6GB (10步, 4096 latents, 384 octree)
  - balanced: 10GB (20步, 8192 latents, 448 octree)
  - high:  24GB (50步, 32768 latents, 1024 octree)
  - ultra: 32GB (100步, 32768 latents, 2048 octree)
```

#### `Cortex3d_MeshSharpener`
```yaml
category: "Cortex3d/Post-Process"
display_name: "网格锐化"
inputs:
  mesh: [CORTEX_MESH]
  strength: [FLOAT, default: 1.0, min: 0.5, max: 2.0, step: 0.1]
outputs:
  mesh: [CORTEX_MESH]
mapping: mesh_sharpener.py
```

#### `Cortex3d_BlenderPrintPrep`
```yaml
category: "Cortex3d/Post-Process"
display_name: "Blender 3D打印预处理"
inputs:
  mesh: [CORTEX_MESH, "输入网格 (OBJ/GLB)"]
  profile: [COMBO, ["default", "resin-mini"], default: "default"]
  height_mm: [FLOAT, default: 100.0, min: 10.0, max: 500.0, "目标高度(mm)"]
  voxel_size_mm: [FLOAT, default: 0.1, min: 0.01, max: 1.0, "体素尺寸"]
  decimate_ratio: [FLOAT, default: 0.5, min: 0.1, max: 1.0, "减面比例 (1.0=不减)"]
  skip_remesh: [BOOLEAN, default: false, "跳过体素重建"]
outputs:
  mesh: [CORTEX_MESH, "STL 网格 (水密、已缩放)"]
  stats: [STRING, "顶点数/面数/尺寸信息"]
execution: 需要 Blender 4.2+ (headless)
mapping: blender_factory.py → blender/refinement.py
```

#### `Cortex3d_MeshValidator`
```yaml
category: "Cortex3d/Post-Process"
display_name: "网格质量验证"
inputs:
  mesh: [CORTEX_MESH]
  check_watertight: [BOOLEAN, default: true]
  check_min_thickness: [BOOLEAN, default: false]
  min_thickness_mm: [FLOAT, default: 0.8]
outputs:
  is_valid: [BOOLEAN]
  report: [STRING, "验证报告文本"]
  issues: [STRING, "问题列表 (如有)"]
mapping: mesh_validator.py
```

---

### 4.6 服装/风格编辑节点 (3个)

#### `Cortex3d_ClothingExtractor`
```yaml
category: "Cortex3d/Edit"
display_name: "智能服装提取"
inputs:
  image: [IMAGE, "角色图像"]
  api_key: [STRING, "Gemini API Key"]
outputs:
  clothing_items: [STRING, "JSON: 提取的服装列表"]
  clothing_images: [IMAGE_LIST, "各服装部件图像"]
  analysis: [STRING, "AI 分析文本"]
mapping: gemini_generator.smart_extract_clothing()
execution: 云端 API
```

#### `Cortex3d_WardrobeChange`
```yaml
category: "Cortex3d/Edit"
display_name: "AI 换装"
inputs:
  character_image: [IMAGE, "角色原图"]
  clothing_description: [STRING, optional, "文字换装描述"]
  clothing_image: [IMAGE, optional, "服装参考图"]
  api_key: [STRING]
outputs:
  image: [IMAGE, "换装后的角色图像"]
mapping: gemini_generator.composite_images() + prompts/wardrobe.py
```

#### `Cortex3d_StyleTransfer`
```yaml
category: "Cortex3d/Edit"
display_name: "风格迁移"
inputs:
  image: [IMAGE, "原始角色图像"]
  target_style: [COMBO, ["anime", "cartoon", "3d-render", "chibi", "sketch", "watercolor", "pixel-art", "claymation", "photorealistic"]]
  api_key: [STRING]
  strength: [FLOAT, default: 0.8, min: 0.0, max: 1.0, "风格强度"]
outputs:
  image: [IMAGE, "风格转换后的图像"]
mapping: aiproxy_client + styles.py prompt
```

---

### 4.7 基础设施节点 (4个)

#### `Cortex3d_DockerManager`
```yaml
category: "Cortex3d/Utils"
display_name: "Docker 容器管理"
inputs:
  service: [COMBO, ["instantmesh", "trellis2", "hunyuan3d", "hunyuan3d-2.1", "hunyuan3d-omni", "ultrashape", "zimage", "qwen-image-edit"]]
  action: [COMBO, ["start", "stop", "status"]]
  compose_file: [STRING, default: "compose.yml"]
outputs:
  status: [STRING, "容器状态信息"]
  is_running: [BOOLEAN]
mapping: docker compose up/down/ps
```

#### `Cortex3d_MeshLoader`
```yaml
category: "Cortex3d/Utils"
display_name: "网格文件加载"
inputs:
  file_path: [STRING, "OBJ/GLB/STL 文件路径"]
outputs:
  mesh: [CORTEX_MESH]
  info: [STRING, "网格信息 (顶点/面/格式)"]
```

#### `Cortex3d_MeshSaver`
```yaml
category: "Cortex3d/Utils"
display_name: "网格文件保存"
inputs:
  mesh: [CORTEX_MESH]
  filename: [STRING, "输出文件名"]
  format: [COMBO, ["glb", "obj", "stl"], default: "glb"]
  output_dir: [STRING, default: "outputs/"]
outputs:
  file_path: [STRING, "保存的文件路径"]
```

#### `Cortex3d_QualityPreset`
```yaml
category: "Cortex3d/Utils"
display_name: "质量预设"
inputs:
  algorithm: [COMBO, ["instantmesh", "triposr", "trellis2", "hunyuan3d", "hunyuan3d-omni"]]
  quality: [COMBO, ["fast", "balanced", "high", "ultra"], default: "balanced"]
outputs:
  config: [CORTEX_CONFIG, "算法特定的参数配置"]
note: 将 reconstructor.py 中的质量预设映射表暴露为节点
```

---

## 5. 数据类型定义

```python
# comfyui_cortex3d/types.py

class CortexMesh:
    """Cortex3d 网格数据类型"""
    def __init__(self, file_path: str, format: str, vertices: int = 0, faces: int = 0):
        self.file_path = file_path   # 网格文件绝对路径
        self.format = format         # "obj" | "glb" | "stl"
        self.vertices = vertices
        self.faces = faces
    
    def to_trimesh(self):
        """转换为 trimesh 对象用于预览"""
        import trimesh
        return trimesh.load(self.file_path)

class CortexViewConfig:
    """视角配置"""
    def __init__(self, view_mode: str, views: list[dict]):
        self.view_mode = view_mode   # "4" | "6" | "8" | "custom"
        self.views = views           # [{"name": "front", "angle": 0}, ...]

class CortexControl:
    """Hunyuan3D-Omni 控制数据"""
    def __init__(self, control_type: str, data_path: str):
        self.control_type = control_type  # "pose" | "point" | "voxel" | "bbox"
        self.data_path = data_path

class CortexConfig:
    """算法质量配置"""
    def __init__(self, algorithm: str, params: dict):
        self.algorithm = algorithm
        self.params = params

# ComfyUI 类型注册
CORTEX_TYPES = {
    "CORTEX_MESH":        ("CORTEX_MESH", CortexMesh),
    "CORTEX_VIEW_CONFIG": ("CORTEX_VIEW_CONFIG", CortexViewConfig),
    "CORTEX_CONTROL":     ("CORTEX_CONTROL", CortexControl),
    "CORTEX_CONFIG":      ("CORTEX_CONFIG", CortexConfig),
    "IMAGE_LIST":         ("IMAGE_LIST", list),  # list[torch.Tensor]
    "VIDEO":              ("VIDEO", str),         # 视频文件路径
}
```

---

## 6. 工作流模板

### 6.1 基础工作流：文字→多视角→3D

```
[MultiviewPromptBuilder] → [GeminiGenerator] → [MultiviewCutter] → [InstantMesh]
                                                                          ↓
                                                      [MeshValidator] ← [BlenderPrintPrep]
                                                                          ↓
                                                                   [MeshSaver] → STL
```

**对应 JSON 工作流**: `workflows/text_to_3d_basic.json`

### 6.2 高级工作流：对比多算法

```
                                    ┌→ [InstantMesh]  → [MeshSaver "IM"]
[PromptBuilder] → [Gemini] → [Cut] ├→ [TRELLIS.2]    → [MeshSaver "TR"]
                                    ├→ [Hunyuan3DOmni] → [MeshSaver "HY"]
                                    └→ [TripoSR]      → [MeshSaver "TS"]
```

**对应 JSON**: `workflows/multi_algorithm_compare.json`

### 6.3 精品工作流：全流水线 + UltraShape

```
[PromptBuilder] → [Gemini] → [MultiviewCutter] 
                                     ↓
                [ImageEnhancer] → [TRELLIS.2]  
                                     ↓
               [UltraShapeRefiner] → [MeshSharpener]
                                     ↓
                          [BlenderPrintPrep] → STL
```

**对应 JSON**: `workflows/premium_pipeline.json`

### 6.4 服装编辑工作流

```
[ImageUpload] → [ClothingExtractor] → [WardrobeChange] → [GeminiGenerator (多视角)]
                                                                    ↓
                                                            [MultiviewCutter]
                                                                    ↓
                                                           [Hunyuan3DOmni]
```

**对应 JSON**: `workflows/wardrobe_to_3d.json`

### 6.5 本地全离线工作流 (无Gemini API)

```
[ZImageGenerator] → [MultiviewCutter] → [BackgroundRemover]
                                                ↓
                    [QwenImageEdit (可选)] → [TRELLIS.2]
                                                ↓
                                 [UltraShapeRefiner] → [BlenderPrintPrep] → STL
```

**对应 JSON**: `workflows/offline_pipeline.json`

---

## 7. 目录结构

```
ComfyUI/
└── custom_nodes/
    └── ComfyUI-Cortex3d/
        ├── __init__.py                    # 节点注册入口
        ├── requirements.txt               # Python 依赖
        ├── install.py                     # ComfyUI 安装钩子
        ├── README.md                      # 节点包文档
        │
        ├── nodes/                         # 节点实现
        │   ├── __init__.py
        │   ├── prompt_nodes.py            # 6个 Prompt 节点
        │   ├── generation_nodes.py        # 5个图像生成节点
        │   ├── process_nodes.py           # 5个图像处理节点
        │   ├── reconstruction_nodes.py    # 6个3D重建节点
        │   ├── postprocess_nodes.py       # 4个后处理节点
        │   ├── edit_nodes.py              # 3个服装/风格编辑节点
        │   └── utility_nodes.py           # 4个基础设施节点
        │
        ├── types/                         # 自定义数据类型
        │   ├── __init__.py
        │   ├── mesh.py                    # CortexMesh
        │   ├── view_config.py             # CortexViewConfig
        │   ├── control.py                 # CortexControl
        │   └── config.py                  # CortexConfig
        │
        ├── bridge/                        # Docker/服务通信桥
        │   ├── __init__.py
        │   ├── docker_bridge.py           # Docker compose exec 封装
        │   ├── http_bridge.py             # HTTP API 客户端封装
        │   └── file_bridge.py             # 文件路径映射 (宿主↔容器)
        │
        ├── adapters/                      # 现有脚本适配层
        │   ├── __init__.py
        │   ├── gemini_adapter.py          # 封装 gemini_generator.py
        │   ├── aiproxy_adapter.py         # 封装 aiproxy_client.py
        │   ├── zimage_adapter.py          # 封装 zimage_client.py
        │   ├── qwen_adapter.py            # 封装 qwen_image_edit_client.py
        │   ├── instantmesh_adapter.py     # 封装 run_instantmesh.py
        │   ├── triposr_adapter.py         # 封装 run_triposr.py
        │   ├── trellis2_adapter.py        # 封装 run_trellis2.py
        │   ├── hunyuan3d_adapter.py       # 封装 run_hunyuan3d.py / _omni.py
        │   ├── ultrashape_adapter.py      # 封装 run_ultrashape.py
        │   ├── blender_adapter.py         # 封装 blender_factory.py
        │   ├── prompt_adapter.py          # 封装 config.py prompt 构建
        │   └── image_adapter.py           # 封装 image_processor/enhancer
        │
        ├── web/                           # ComfyUI 前端扩展
        │   ├── js/
        │   │   ├── cortex3d_widgets.js    # 自定义 UI widget
        │   │   └── mesh_preview.js        # 3D 网格 WebGL 预览
        │   └── css/
        │       └── cortex3d.css           # 节点样式
        │
        ├── workflows/                     # 预置工作流
        │   ├── text_to_3d_basic.json
        │   ├── multi_algorithm_compare.json
        │   ├── premium_pipeline.json
        │   ├── wardrobe_to_3d.json
        │   └── offline_pipeline.json
        │
        └── configs/                       # 配置文件
            ├── docker_services.yaml       # Docker 容器配置映射
            └── quality_presets.yaml        # 质量预设参数表
```

---

## 8. 实施计划（分阶段）

### Phase 1：基础框架 + Prompt 节点 + 图像生成 (2 周)

| 任务 | 工作量 | 产出 |
|------|--------|------|
| 搭建 `ComfyUI-Cortex3d` 节点包骨架 | 2d | `__init__.py`, 类型注册, 目录结构 |
| 实现自定义数据类型 | 1d | `types/` 全部 |
| 实现 Docker Bridge 层 | 2d | `bridge/` 全部 |
| 实现 6 个 Prompt 节点 | 2d | `nodes/prompt_nodes.py` |
| 实现 5 个图像生成节点 | 3d | `nodes/generation_nodes.py` + adapters |
| 实现 `text_to_3d_basic` 工作流模板 (仅图像部分) | 1d | `workflows/` |
| **阶段验证**: PromptBuilder → Gemini → 预览多视角 | 1d | 端到端运行 |

**Phase 1 交付**: 可在 ComfyUI 中通过节点生成多视角角色图像

---

### Phase 2：图像处理 + 3D 重建 + 后处理 (3 周)

| 任务 | 工作量 | 产出 |
|------|--------|------|
| 实现 5 个图像处理节点 | 2d | `nodes/process_nodes.py` |
| 实现 6 个 3D 重建节点 | 5d | `nodes/reconstruction_nodes.py` + adapters |
| 实现 4 个后处理节点 | 3d | `nodes/postprocess_nodes.py` |
| 实现 WebGL 网格预览 JS | 3d | `web/js/mesh_preview.js` |
| 实现 4 个基础设施节点 | 2d | `nodes/utility_nodes.py` |
| 完善工作流模板 2-5 | 2d | `workflows/` |
| **阶段验证**: 全管线端到端 → STL | 2d | |

**Phase 2 交付**: ComfyUI 完整替代 `reconstructor.py` CLI

---

### Phase 3：编辑能力 + 优化 + 文档 (2 周)

| 任务 | 工作量 | 产出 |
|------|--------|------|
| 实现 3 个服装/风格编辑节点 | 3d | `nodes/edit_nodes.py` |
| ComfyUI 自定义 Widget (下拉、滑块) | 2d | `web/` |
| 节点分组/颜色主题设计 | 1d | CSS/元数据 |
| 性能优化 (模型缓存、并行执行) | 2d | adapter 层缓存 |
| 编写完整文档 + 使用指南 | 2d | README.md |
| Error Handling + 日志 + 进度条 | 2d | 全局错误处理 |
| **阶段验证**: 全功能集成测试 | 2d | |

**Phase 3 交付**: 生产可用的 ComfyUI 节点包

---

### 总计: ~7 周 (35 个工作日)

```
Week 1-2:  Phase 1 — 基础框架 + 图像生成
Week 3-5:  Phase 2 — 图像处理 + 3D 重建 + 后处理  
Week 6-7:  Phase 3 — 编辑 + 优化 + 文档
```

---

## 9. Docker 集成方案

### 9.1 方案选择

| 方案 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| **A: ComfyUI 与模型同容器** | 最简单，无网络开销 | 镜像巨大 (50GB+), 依赖冲突 | 单机测试 |
| **B: ComfyUI 宿主 + 模型 Docker** ⭐ | 灵活, 已有架构不变 | 需 Docker CLI 权限 | **推荐：当前架构延续** |
| **C: 全微服务化** | 云原生，水平扩展 | 复杂度高, 需 K8s | 生产集群 |

### 9.2 推荐方案 B 实现细节

```yaml
# 新增 ComfyUI 服务到 compose.yml
services:
  comfyui:
    build:
      context: .
      dockerfile: Dockerfile.comfyui
    ports:
      - "8188:8188"       # ComfyUI Web UI
    volumes:
      - .:/workspace      # 共享工作空间
      - hf-cache:/root/.cache/huggingface
      - /var/run/docker.sock:/var/run/docker.sock  # Docker-in-Docker
      - comfyui-models:/app/ComfyUI/models
    environment:
      - CORTEX3D_WORKSPACE=/workspace
      - CORTEX3D_DOCKER_MODE=compose
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - AIPROXY_URL=${AIPROXY_URL}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - instantmesh
      - trellis2
```

### 9.3 Docker Bridge 核心逻辑

```python
# bridge/docker_bridge.py

import subprocess
import os
from pathlib import Path

class DockerBridge:
    """Docker Compose 容器调用桥"""
    
    def __init__(self, compose_file="compose.yml", workspace="/workspace"):
        self.compose_file = compose_file
        self.workspace = workspace
        self.is_in_docker = os.path.exists("/.dockerenv")
    
    def ensure_running(self, service: str) -> bool:
        """确保容器正在运行"""
        result = subprocess.run(
            ["docker", "compose", "-f", self.compose_file, "ps", "-q", service],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "up", "-d", service],
                check=True
            )
        return True
    
    def exec_script(self, service: str, script: str, 
                    args: dict, timeout: int = 600) -> dict:
        """在容器内执行 Python 脚本"""
        self.ensure_running(service)
        
        cmd = ["docker", "compose", "-f", self.compose_file, 
               "exec", "-T", service, "python3", script]
        
        for key, value in args.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key}")
            else:
                cmd.extend([f"--{key}", str(value)])
        
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              timeout=timeout)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    
    def host_to_container_path(self, host_path: str) -> str:
        """宿主路径 → 容器路径"""
        return str(Path(host_path).relative_to(
            os.environ.get("CORTEX3D_WORKSPACE", ".")
        ))
    
    def container_to_host_path(self, container_path: str) -> str:
        """容器路径 → 宿主路径"""
        workspace = os.environ.get("CORTEX3D_WORKSPACE", ".")
        return str(Path(workspace) / container_path.lstrip("/workspace/"))
```

---

## 10. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| **GPU 内存不足** — 多个模型同时加载 | 3D 重建节点 OOM | 高 | ① Docker Bridge 确保同时只运行 1 个 GPU 容器 ② 节点执行前自动检测 VRAM ③ `DockerManager` 节点手动控制启停 |
| **长时间执行** — 3D 重建 5-30 分钟 | ComfyUI 超时 / 假死 | 高 | ① 异步执行 + WebSocket 进度推送 ② Docker 超时配置 ③ 节点内部 progress callback |
| **文件路径映射** — 宿主/容器路径不同 | 找不到输入/输出文件 | 中 | `file_bridge.py` 统一路径映射，`CORTEX3D_WORKSPACE` 环境变量 |
| **依赖冲突** — ComfyUI PyTorch 版本 vs 模型需求 | import 失败 | 中 | 3D 重建全部走 Docker（隔离环境），ComfyUI 主机只装轻量依赖 |
| **Gemini API 限频** — 免费 tier 15 RPM | 批量生成中断 | 中 | ① 节点内置重试 + 退避 ② 支持切换 AiProxy ③ 本地 Z-Image 备用 |
| **网格预览性能** — GLB 可达 500K+ 面 | WebGL 卡顿 | 低 | 预览渲染时自动 LOD 降面至 50K |
| **ComfyUI 版本兼容** — API 变更 | 节点加载失败 | 低 | 锁定 ComfyUI >= 0.3.x，定期跟踪上游 |

---

## 11. 与现有前端的兼容策略

### 11.1 双轨运行 (推荐过渡期)

```
                 ┌──→ React SPA (保留) ──→ FastAPI 后端 ──→ scripts/
用户 ──选择──┤
                 └──→ ComfyUI Web UI ──→ ComfyUI-Cortex3d 节点 ──→ scripts/
```

### 11.2 React 前端集成 ComfyUI (高级)

```typescript
// 在 React 前端嵌入 ComfyUI iframe / 调用 ComfyUI API
const COMFYUI_API = "http://localhost:8188/api";

// 触发工作流执行
async function runWorkflow(workflowJson: object, inputs: Record<string, any>) {
    const prompt = buildComfyUIPrompt(workflowJson, inputs);
    const response = await fetch(`${COMFYUI_API}/prompt`, {
        method: "POST",
        body: JSON.stringify({ prompt }),
    });
    const { prompt_id } = await response.json();
    
    // WebSocket 监听进度
    const ws = new WebSocket(`ws://localhost:8188/ws?clientId=${clientId}`);
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "progress") updateProgress(data);
        if (data.type === "executed") handleResult(data);
    };
}
```

### 11.3 最终架构演进

```
Phase A (当前): React → FastAPI → scripts
Phase B (过渡): React + ComfyUI → FastAPI + ComfyUI nodes → scripts  
Phase C (最终): ComfyUI (主) + React (轻量看板) → ComfyUI-Cortex3d → Docker GPU
```

---

## 附录 A：关键实现代码参考

### 节点注册入口 `__init__.py`

```python
"""ComfyUI-Cortex3d: AI 3D 打印手办自动化流水线节点包"""

from .nodes.prompt_nodes import (
    Cortex3d_MultiviewPromptBuilder,
    Cortex3d_ImageRefPromptBuilder,
    Cortex3d_StrictCopyPromptBuilder,
    Cortex3d_CompositePromptBuilder,
    Cortex3d_NegativePrompt,
    Cortex3d_PromptPreset,
)
from .nodes.generation_nodes import (
    Cortex3d_GeminiGenerator,
    Cortex3d_AiProxyGenerator,
    Cortex3d_ZImageGenerator,
    Cortex3d_ZImageImg2Img,
    Cortex3d_QwenImageEdit,
)
from .nodes.process_nodes import (
    Cortex3d_MultiviewCutter,
    Cortex3d_BackgroundRemover,
    Cortex3d_FragmentCleaner,
    Cortex3d_ImageEnhancer,
    Cortex3d_ImagePreview,
)
from .nodes.reconstruction_nodes import (
    Cortex3d_InstantMesh,
    Cortex3d_TripoSR,
    Cortex3d_TRELLIS2,
    Cortex3d_Hunyuan3D,
    Cortex3d_Hunyuan3DOmni,
    Cortex3d_MultiviewReconstruction,
)
from .nodes.postprocess_nodes import (
    Cortex3d_UltraShapeRefiner,
    Cortex3d_MeshSharpener,
    Cortex3d_BlenderPrintPrep,
    Cortex3d_MeshValidator,
)
from .nodes.edit_nodes import (
    Cortex3d_ClothingExtractor,
    Cortex3d_WardrobeChange,
    Cortex3d_StyleTransfer,
)
from .nodes.utility_nodes import (
    Cortex3d_DockerManager,
    Cortex3d_MeshLoader,
    Cortex3d_MeshSaver,
    Cortex3d_QualityPreset,
)

NODE_CLASS_MAPPINGS = {
    # Prompt 节点
    "Cortex3d_MultiviewPromptBuilder": Cortex3d_MultiviewPromptBuilder,
    "Cortex3d_ImageRefPromptBuilder": Cortex3d_ImageRefPromptBuilder,
    "Cortex3d_StrictCopyPromptBuilder": Cortex3d_StrictCopyPromptBuilder,
    "Cortex3d_CompositePromptBuilder": Cortex3d_CompositePromptBuilder,
    "Cortex3d_NegativePrompt": Cortex3d_NegativePrompt,
    "Cortex3d_PromptPreset": Cortex3d_PromptPreset,
    # 图像生成
    "Cortex3d_GeminiGenerator": Cortex3d_GeminiGenerator,
    "Cortex3d_AiProxyGenerator": Cortex3d_AiProxyGenerator,
    "Cortex3d_ZImageGenerator": Cortex3d_ZImageGenerator,
    "Cortex3d_ZImageImg2Img": Cortex3d_ZImageImg2Img,
    "Cortex3d_QwenImageEdit": Cortex3d_QwenImageEdit,
    # 图像处理
    "Cortex3d_MultiviewCutter": Cortex3d_MultiviewCutter,
    "Cortex3d_BackgroundRemover": Cortex3d_BackgroundRemover,
    "Cortex3d_FragmentCleaner": Cortex3d_FragmentCleaner,
    "Cortex3d_ImageEnhancer": Cortex3d_ImageEnhancer,
    "Cortex3d_ImagePreview": Cortex3d_ImagePreview,
    # 3D 重建
    "Cortex3d_InstantMesh": Cortex3d_InstantMesh,
    "Cortex3d_TripoSR": Cortex3d_TripoSR,
    "Cortex3d_TRELLIS2": Cortex3d_TRELLIS2,
    "Cortex3d_Hunyuan3D": Cortex3d_Hunyuan3D,
    "Cortex3d_Hunyuan3DOmni": Cortex3d_Hunyuan3DOmni,
    "Cortex3d_MultiviewReconstruction": Cortex3d_MultiviewReconstruction,
    # 后处理
    "Cortex3d_UltraShapeRefiner": Cortex3d_UltraShapeRefiner,
    "Cortex3d_MeshSharpener": Cortex3d_MeshSharpener,
    "Cortex3d_BlenderPrintPrep": Cortex3d_BlenderPrintPrep,
    "Cortex3d_MeshValidator": Cortex3d_MeshValidator,
    # 编辑
    "Cortex3d_ClothingExtractor": Cortex3d_ClothingExtractor,
    "Cortex3d_WardrobeChange": Cortex3d_WardrobeChange,
    "Cortex3d_StyleTransfer": Cortex3d_StyleTransfer,
    # 工具
    "Cortex3d_DockerManager": Cortex3d_DockerManager,
    "Cortex3d_MeshLoader": Cortex3d_MeshLoader,
    "Cortex3d_MeshSaver": Cortex3d_MeshSaver,
    "Cortex3d_QualityPreset": Cortex3d_QualityPreset,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Cortex3d_MultiviewPromptBuilder": "🎨 多视角提示词构建",
    "Cortex3d_ImageRefPromptBuilder": "🖼️ 图像参考提示词",
    "Cortex3d_StrictCopyPromptBuilder": "📋 严格复制提示词",
    "Cortex3d_CompositePromptBuilder": "🧩 合成提示词",
    "Cortex3d_NegativePrompt": "⛔ 负面提示词",
    "Cortex3d_PromptPreset": "📦 预设角色模板",
    "Cortex3d_GeminiGenerator": "✨ Gemini 多视角生成",
    "Cortex3d_AiProxyGenerator": "🌐 AiProxy 图像生成",
    "Cortex3d_ZImageGenerator": "🏠 Z-Image 本地文生图",
    "Cortex3d_ZImageImg2Img": "🏠 Z-Image 本地图生图",
    "Cortex3d_QwenImageEdit": "✏️ Qwen 图像编辑",
    "Cortex3d_MultiviewCutter": "✂️ 多视角切割",
    "Cortex3d_BackgroundRemover": "🔲 背景移除",
    "Cortex3d_FragmentCleaner": "🧹 碎片清除",
    "Cortex3d_ImageEnhancer": "⬆️ 图像增强 (超分+人脸)",
    "Cortex3d_ImagePreview": "👁️ 图像预览",
    "Cortex3d_InstantMesh": "🔷 InstantMesh 3D",
    "Cortex3d_TripoSR": "🔷 TripoSR 3D",
    "Cortex3d_TRELLIS2": "🔷 TRELLIS.2 3D",
    "Cortex3d_Hunyuan3D": "🔷 Hunyuan3D",
    "Cortex3d_Hunyuan3DOmni": "🔷 Hunyuan3D-Omni",
    "Cortex3d_MultiviewReconstruction": "🔷 多视角重建",
    "Cortex3d_UltraShapeRefiner": "💎 UltraShape 精化",
    "Cortex3d_MeshSharpener": "🔪 网格锐化",
    "Cortex3d_BlenderPrintPrep": "🖨️ Blender 打印预处理",
    "Cortex3d_MeshValidator": "✅ 网格验证",
    "Cortex3d_ClothingExtractor": "👗 智能服装提取",
    "Cortex3d_WardrobeChange": "👔 AI 换装",
    "Cortex3d_StyleTransfer": "🎭 风格迁移",
    "Cortex3d_DockerManager": "🐳 Docker 容器管理",
    "Cortex3d_MeshLoader": "📂 网格加载",
    "Cortex3d_MeshSaver": "💾 网格保存",
    "Cortex3d_QualityPreset": "⚙️ 质量预设",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

### 示例节点实现 — InstantMesh

```python
# nodes/reconstruction_nodes.py (部分)

import torch
import numpy as np
from PIL import Image
from pathlib import Path

class Cortex3d_InstantMesh:
    """InstantMesh 单张图像 → 3D 网格重建"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "config": (["instant-mesh-hq", "instant-mesh-large"],
                          {"default": "instant-mesh-hq"}),
                "diffusion_steps": ("INT", {
                    "default": 75, "min": 10, "max": 200, "step": 5
                }),
                "guidance_scale": ("FLOAT", {
                    "default": 7.5, "min": 1.0, "max": 20.0, "step": 0.5
                }),
                "seed": ("INT", {"default": 42, "min": 0, "max": 0xffffffff}),
            },
            "optional": {
                "texture_resolution": ("INT", {
                    "default": 1024, "min": 512, "max": 4096, "step": 256
                }),
                "export_texture": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("CORTEX_MESH", "IMAGE", "IMAGE")
    RETURN_NAMES = ("mesh", "texture", "preview")
    FUNCTION = "execute"
    CATEGORY = "Cortex3d/3D Reconstruction"
    
    def execute(self, image, config, diffusion_steps, guidance_scale, seed,
                texture_resolution=1024, export_texture=True):
        from ..bridge.docker_bridge import DockerBridge
        from ..types.mesh import CortexMesh
        
        bridge = DockerBridge()
        
        # 1. 将 ComfyUI IMAGE tensor 保存为临时 PNG
        img_array = (image[0].cpu().numpy() * 255).astype(np.uint8)
        img_pil = Image.fromarray(img_array)
        tmp_input = Path("outputs/comfyui_tmp/input.png")
        tmp_input.parent.mkdir(parents=True, exist_ok=True)
        img_pil.save(tmp_input)
        
        # 2. 通过 Docker Bridge 执行
        result = bridge.exec_script(
            service="instantmesh",
            script="/workspace/scripts/run_instantmesh.py",
            args={
                "config": f"/workspace/configs/{config}.yaml",
                "input": f"/workspace/{tmp_input}",
                "output_path": "/workspace/outputs/comfyui_instantmesh",
                "diffusion_steps": diffusion_steps,
                "guidance_scale": guidance_scale,
                "seed": seed,
                "texture_resolution": texture_resolution,
                "export_texmap": export_texture,
            },
            timeout=600  # 10 分钟
        )
        
        if not result["success"]:
            raise RuntimeError(f"InstantMesh 失败: {result['stderr']}")
        
        # 3. 收集输出
        output_dir = Path(f"outputs/comfyui_instantmesh/{config}/meshes")
        obj_files = list(output_dir.glob("*.obj"))
        if not obj_files:
            raise FileNotFoundError("未生成网格文件")
        
        mesh = CortexMesh(
            file_path=str(obj_files[0]),
            format="obj"
        )
        
        # 4. 生成预览 (渲染一张缩略图)
        preview = self._render_preview(mesh)
        
        # 5. 读取纹理
        texture = self._load_texture(output_dir) if export_texture else None
        
        return (mesh, texture, preview)
    
    def _render_preview(self, mesh):
        """用 trimesh 渲染简单预览"""
        import trimesh
        scene = trimesh.load(mesh.file_path)
        png = scene.save_image(resolution=(512, 512))
        img = Image.open(io.BytesIO(png))
        return torch.from_numpy(np.array(img)).float() / 255.0
    
    def _load_texture(self, output_dir):
        tex_files = list(output_dir.glob("*_texture*"))
        if tex_files:
            img = Image.open(tex_files[0]).convert("RGB")
            return torch.from_numpy(np.array(img)).float() / 255.0
        return None
```

---

## 附录 B：Dockerfile.comfyui 参考

```dockerfile
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 基础工具
RUN apt-get update && apt-get install -y \
    python3.11 python3-pip git wget \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# 安装 ComfyUI
WORKDIR /app
RUN git clone https://github.com/comfyanonymous/ComfyUI.git
WORKDIR /app/ComfyUI
RUN pip3 install -r requirements.txt

# 安装 Cortex3d 节点包依赖 (轻量 — 无模型依赖)
COPY custom_nodes/ComfyUI-Cortex3d/requirements.txt /tmp/cortex3d_req.txt
RUN pip3 install -r /tmp/cortex3d_req.txt

# 复制节点包
COPY custom_nodes/ComfyUI-Cortex3d /app/ComfyUI/custom_nodes/ComfyUI-Cortex3d

# 预置工作流
COPY custom_nodes/ComfyUI-Cortex3d/workflows /app/ComfyUI/user/default/workflows/cortex3d

EXPOSE 8188

CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
```

---

## 附录 C：ComfyUI-Cortex3d 依赖 (轻量)

```txt
# requirements.txt — ComfyUI 主机端 (不含模型依赖)
Pillow>=10.0
numpy>=1.24
trimesh>=4.0
requests>=2.28
pyyaml>=6.0
python-dotenv>=1.0
google-generativeai>=0.8   # Gemini API (仅 REST)
rembg>=2.0                 # 背景移除 (U2Net 轻量)
```

> **注意**: 3D 重建模型 (PyTorch/diffusers/trellis2 等) 全部通过 Docker 容器运行，ComfyUI 主机无需安装重型依赖。

---

*文档生成完毕 — 本方案将 Cortex3d 的 35+ 个脚本拆分为 33 个 ComfyUI 节点，支持灵活组合、实时预览、多算法对比，全面替代原有固定管线。*
