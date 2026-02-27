# ComfyUI-Cortex3d

> **Cortex3d AI 3D 打印手办流水线** 的 ComfyUI 自定义节点包  
> 将 35+ 个工业级 Python 脚本封装为 **33 个可拖拽 ComfyUI 节点**

---

## 功能概览

| 分类 | 节点数 | 能力 |
|------|--------|------|
| 🗣️ **Prompt** | 6 | 多视角 / 参考图 / 严格复制 / 复合场景提示词构建 |
| 🖼️ **Generate** | 5 | Gemini / AiProxy 云端生成 + Z-Image / Qwen 本地生成/编辑 |
| ✂️ **Process** | 5 | 多视角切割 / rembg 去背景 / 碎片清除 / Super-Resolution |
| 🔷 **3D** | 6 | InstantMesh / TripoSR / TRELLIS.2 / Hunyuan3D 2.0+2.1+Omni |
| 💎 **PostProcess** | 4 | UltraShape 精修 / 网格锐化 / Blender打印预处理 / 质量验证 |
| 👗 **Edit** | 3 | 服装提取 / AI 换装 / 风格迁移 |
| 🔧 **Utility** | 4 | Docker 管理 / 网格加载/保存 / 质量预设 |

---

## 安装

### 方法一：软链接（开发推荐）

```powershell
# Windows PowerShell（管理员）
New-Item -ItemType SymbolicLink `
  -Path "C:\path\to\ComfyUI\custom_nodes\ComfyUI-Cortex3d" `
  -Target "D:\repos\yunze7373\Cortex3d\ComfyUI-Cortex3d"
```

```bash
# Linux / macOS
ln -s /path/to/Cortex3d/ComfyUI-Cortex3d \
      /path/to/ComfyUI/custom_nodes/ComfyUI-Cortex3d
```

### 方法二：Docker（一键启动）

```bash
# 在 Cortex3d 项目根目录执行
docker compose up comfyui

# 访问 http://localhost:8188
```

> ComfyUI 容器通过 `/var/run/docker.sock` 调用其他 GPU 容器（无需共享 VRAM）。

### 依赖安装

```bash
# 在 ComfyUI 的 Python 环境内
pip install -r ComfyUI-Cortex3d/requirements.txt
```

---

## 配置

在项目根 `.env` 文件（或系统环境变量）中设置：

```dotenv
# 云端 API（至少配置一个图像生成来源）
GEMINI_API_KEY=AIza...          # Google Gemini API
AIPROXY_API_KEY=...             # AiProxy 代理 Key
AIPROXY_URL=https://...         # AiProxy 端点

# 本地服务地址（Docker 中可直接用服务名）
ZIMAGE_URL=http://localhost:8199       # Z-Image-Turbo 本地服务
QWEN_URL=http://localhost:8200         # Qwen-Image-Edit 本地服务

# 工作区路径（Docker 模式必填）
CORTEX3D_WORKSPACE=/workspace         # 容器内工作区路径（映射到项目根）

# 可选
CORTEX3D_CACHE_DIR=/tmp/cortex3d_cache   # 重建结果磁盘缓存目录
CORTEX3D_LOG_LEVEL=INFO                  # 日志级别 (DEBUG/INFO/WARNING)
HF_TOKEN=hf_...                          # HuggingFace Token（Hunyuan3D/TRELLIS下载用）
```

---

## 快速开始

1. 启动 ComfyUI → 打开 **Load** 菜单 → 导入 `workflows/text_to_3d_basic.json`。
2. 在 `MultiviewPromptBuilder` 节点中输入角色描述，填入 `GEMINI_API_KEY`。
3. 点击 **Queue Prompt** → 观看多视角图像生成 → InstantMesh 自动重建 3D。

---

## 工作流模板

| 文件 | 场景 | GPU 需求 |
|------|------|---------|
| `text_to_3d_basic.json` | 文字 → 多视角图 → InstantMesh 3D | 8 GB |
| `multi_algorithm_compare.json` | 同一角色用 3 种算法对比 | 16 GB |
| `premium_pipeline.json` | Gemini → TRELLIS.2 → UltraShape → Blender STL | 24 GB |
| `wardrobe_to_3d.json` | 参考服装图 → 换装 → 3D 重建 | 16 GB |
| `offline_pipeline.json` | 纯本地（Z-Image + TripoSR），无云 API | 8 GB |

---

## 节点参考

### Prompt 系列

#### `MultiviewPromptBuilder` — 多视角提示词构建器
| 输入 | 类型 | 说明 |
|------|------|------|
| character_description | STRING | 角色描述文本 |
| style | 枚举 | anime / realistic / chibi / western / sci-fi |
| view_mode | 枚举 | standard_4 / standard_6 / turntable_8 / custom |
| subject_only | BOOLEAN | 仅生成主体（去掉背景描述） |
| with_props | BOOLEAN | 包含道具描述 |

输出: `(prompt:STRING, view_config:CORTEX_VIEW_CONFIG)`

---

### Generate 系列

#### `GeminiGenerator` — Gemini 多视角生成
需要 `GEMINI_API_KEY`，支持 `reference_image` 输入实现 IP-Adapter 风格控制。

#### `ZImageGenerator` / `ZImageImg2Img` — 本地无需 API
需启动 `zimage` Docker 容器（端口 8199）。

#### `QwenImageEdit` — Qwen-Image-Edit 语义编辑
需启动 `qwen-image-edit` 容器（端口 8200），支持换装/修图/文字编辑。

---

### 3D 重建系列

| 节点 | 算法 | 输出格式 | 建议 VRAM |
|------|------|----------|----------|
| `InstantMesh` | InstantMesh (OpenLRM) | OBJ+纹理 | 8 GB |
| `TripoSR` | TripoSR | OBJ | 6 GB |
| `TRELLIS2` | TRELLIS.2-4B / 1B | GLB | 16 GB |
| `Hunyuan3D` | Hunyuan3D 2.0 / 2.1 | GLB | 16 GB |
| `Hunyuan3DOmni` | Hunyuan3D-Omni (条件控制) | GLB | 10 GB |
| `MultiviewReconstruction` | 路由到上述任意算法 | 取决于算法 | — |

---

### 自定义数据类型

| 类型 | 说明 |
|------|------|
| `CORTEX_MESH` | 3D 网格文件引用（含路径、格式、顶点/面片数统计） |
| `CORTEX_VIEW_CONFIG` | 多视角配置（rows × cols、宽高比） |
| `CORTEX_CONFIG` | 算法 + 质量预设参数包 |
| `CORTEX_CONTROL` | Hunyuan3D-Omni 条件控制（姿势/点云/体素/BBox） |

---

## 性能优化

### 结果缓存

重建结果会自动缓存（默认 24 小时），相同参数不会重复调用 GPU：

```python
# 可在 ComfyUI-Cortex3d/adapters/ 中的适配器内使用
from adapters.cache import ResultCache

cache = ResultCache("instantmesh")
hit = cache.get(image_path=img, steps=75, seed=42)
if hit:
    return CortexMesh(file_path=hit, ...)
```

环境变量 `CORTEX3D_CACHE_DIR` 控制缓存位置，使用 `DockerManager` 节点的 `clear_cache` 动作清空。

### 客户端复用

`ZImageAdapter` / `QwenAdapter` 自动复用单例 HTTP 客户端，避免每次请求重新建立连接。

---

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 节点显示 `None mesh` | GPU 容器未运行 | 使用 `DockerManager` 节点 → action=start |
| Gemini 返回空 | API Key 错误 / 配额耗尽 | 检查 `GEMINI_API_KEY`，或换 `ZImageGenerator` |
| Z-Image 连接拒绝 | 容器未启动 | `docker compose up zimage` |
| 3D 预览空白 | Three.js CDN 加载失败（离线环境） | 将 Three.js 放到 `web/js/vendor/` 并修改 import 路径 |
| `CORTEX_MESH` 连接线报类型错误 | ComfyUI 版本 < 0.3.5 | 升级 ComfyUI |

---

## 目录结构

```
ComfyUI-Cortex3d/
├── __init__.py                 # 节点注册入口 (WEB_DIRECTORY, NODE_CLASS_MAPPINGS)
├── requirements.txt            # 轻量级 Python 依赖
├── adapters/                   # 脚本封装层 (12 个适配器 + cache.py)
├── bridge/                     # Docker / HTTP / 文件路径桥接
├── nodes/                      # ComfyUI 节点实现 (7 个文件，33 个节点)
├── types/                      # 自定义数据类型 (CORTEX_MESH 等)
├── utils/                      # 错误处理 / 进度报告 / 日志
├── web/                        # 前端扩展 (JS Widgets + Three.js 预览 + CSS)
├── configs/                    # docker_services.yaml 服务配置表
└── workflows/                  # 5 个开箱即用工作流模板
```

---

## 许可证

本节点包与 Cortex3d 主项目使用相同许可证。所调用的 3D 模型权重各自遵守其原始许可：
- InstantMesh: Apache-2.0
- TripoSR: MIT
- TRELLIS.2: MIT
- Hunyuan3D: Tencent Hunyuan Community License
- UltraShape: 参见官方 repo

---

## 致谢

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — 节点化 AI 工作流框架
- [InstantMesh](https://github.com/TencentARC/InstantMesh) — 快速单图 3D 重建
- [TripoSR](https://github.com/VAST-AI-Research/TripoSR) — 高质量单图重建
- [TRELLIS](https://github.com/microsoft/TRELLIS) — 微软 Structured Latent 方法
- [Hunyuan3D](https://github.com/Tencent/Hunyuan3D-2) — 腾讯多功能 3D 生成
