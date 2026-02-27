"""
ComfyUI-Cortex3d
================
Cortex3d AI 3D 打印手办自动化流水线的 ComfyUI 自定义节点包。

将 Cortex3d 的 35+ 个 Python 脚本封装为 33 个 ComfyUI 节点，支持：
- 多视角 AI 图像生成（Gemini / AiProxy / Z-Image 本地 / Qwen 编辑）
- 7 种 3D 重建算法（InstantMesh / TripoSR / TRELLIS.2 / Hunyuan3D 系列）
- 几何精化（UltraShape）
- Blender 3D 打印后处理（水密化 → 体素重建 → STL 导出）
- 服装提取 / 换装 / 风格迁移

安装: 将本目录复制或链接到 ComfyUI/custom_nodes/ComfyUI-Cortex3d/
"""

import sys
import os
from pathlib import Path

# 将 Cortex3d 的 scripts/ 目录加入 Python 路径
_CORTEX3D_ROOT = Path(__file__).parent.parent
_SCRIPTS_DIR = _CORTEX3D_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# ── 按节点组导入 ───────────────────────────────────────────────────────────

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
    Cortex3d_ImageListMerge,
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

# ── 节点类映射（ComfyUI 内部 ID → 类）────────────────────────────────────

NODE_CLASS_MAPPINGS = {
    # Prompt 构建节点
    "Cortex3d_MultiviewPromptBuilder": Cortex3d_MultiviewPromptBuilder,
    "Cortex3d_ImageRefPromptBuilder":  Cortex3d_ImageRefPromptBuilder,
    "Cortex3d_StrictCopyPromptBuilder":Cortex3d_StrictCopyPromptBuilder,
    "Cortex3d_CompositePromptBuilder": Cortex3d_CompositePromptBuilder,
    "Cortex3d_NegativePrompt":         Cortex3d_NegativePrompt,
    "Cortex3d_PromptPreset":           Cortex3d_PromptPreset,
    # 图像生成节点
    "Cortex3d_GeminiGenerator":        Cortex3d_GeminiGenerator,
    "Cortex3d_AiProxyGenerator":       Cortex3d_AiProxyGenerator,
    "Cortex3d_ZImageGenerator":        Cortex3d_ZImageGenerator,
    "Cortex3d_ZImageImg2Img":          Cortex3d_ZImageImg2Img,
    "Cortex3d_QwenImageEdit":          Cortex3d_QwenImageEdit,
    # 图像处理节点
    "Cortex3d_MultiviewCutter":        Cortex3d_MultiviewCutter,
    "Cortex3d_BackgroundRemover":      Cortex3d_BackgroundRemover,
    "Cortex3d_FragmentCleaner":        Cortex3d_FragmentCleaner,
    "Cortex3d_ImageEnhancer":          Cortex3d_ImageEnhancer,
    "Cortex3d_ImageListMerge":         Cortex3d_ImageListMerge,
    # 3D 重建节点
    "Cortex3d_InstantMesh":            Cortex3d_InstantMesh,
    "Cortex3d_TripoSR":                Cortex3d_TripoSR,
    "Cortex3d_TRELLIS2":               Cortex3d_TRELLIS2,
    "Cortex3d_Hunyuan3D":              Cortex3d_Hunyuan3D,
    "Cortex3d_Hunyuan3DOmni":          Cortex3d_Hunyuan3DOmni,
    "Cortex3d_MultiviewReconstruction":Cortex3d_MultiviewReconstruction,
    # 后处理节点
    "Cortex3d_UltraShapeRefiner":      Cortex3d_UltraShapeRefiner,
    "Cortex3d_MeshSharpener":          Cortex3d_MeshSharpener,
    "Cortex3d_BlenderPrintPrep":       Cortex3d_BlenderPrintPrep,
    "Cortex3d_MeshValidator":          Cortex3d_MeshValidator,
    # 编辑节点
    "Cortex3d_ClothingExtractor":      Cortex3d_ClothingExtractor,
    "Cortex3d_WardrobeChange":         Cortex3d_WardrobeChange,
    "Cortex3d_StyleTransfer":          Cortex3d_StyleTransfer,
    # 工具节点
    "Cortex3d_DockerManager":          Cortex3d_DockerManager,
    "Cortex3d_MeshLoader":             Cortex3d_MeshLoader,
    "Cortex3d_MeshSaver":              Cortex3d_MeshSaver,
    "Cortex3d_QualityPreset":          Cortex3d_QualityPreset,
}

# ── 节点显示名称映射（Canvas 画布显示文本）─────────────────────────────────

NODE_DISPLAY_NAME_MAPPINGS = {
    # Prompt
    "Cortex3d_MultiviewPromptBuilder": "🎨 多视角提示词构建",
    "Cortex3d_ImageRefPromptBuilder":  "🖼️ 图像参考提示词",
    "Cortex3d_StrictCopyPromptBuilder":"📋 严格复制提示词",
    "Cortex3d_CompositePromptBuilder": "🧩 合成提示词构建",
    "Cortex3d_NegativePrompt":         "⛔ 负面提示词",
    "Cortex3d_PromptPreset":           "📦 预设角色模板",
    # 图像生成
    "Cortex3d_GeminiGenerator":        "✨ Gemini 多视角生成",
    "Cortex3d_AiProxyGenerator":       "🌐 AiProxy 图像生成",
    "Cortex3d_ZImageGenerator":        "🏠 Z-Image 文生图（本地）",
    "Cortex3d_ZImageImg2Img":          "🏠 Z-Image 图生图（本地）",
    "Cortex3d_QwenImageEdit":          "✏️ Qwen 图像编辑（本地）",
    # 图像处理
    "Cortex3d_MultiviewCutter":        "✂️ 多视角图像切割",
    "Cortex3d_BackgroundRemover":      "🔲 背景移除（rembg）",
    "Cortex3d_FragmentCleaner":        "🧹 碎片清除",
    "Cortex3d_ImageEnhancer":          "⬆️ 图像增强（超分+人脸）",
    "Cortex3d_ImageListMerge":         "🔗 图像列表合并",
    # 3D 重建
    "Cortex3d_InstantMesh":            "🔷 InstantMesh 3D 重建",
    "Cortex3d_TripoSR":                "🔷 TripoSR 3D 重建",
    "Cortex3d_TRELLIS2":               "🔷 TRELLIS.2 3D 重建",
    "Cortex3d_Hunyuan3D":              "🔷 Hunyuan3D 重建",
    "Cortex3d_Hunyuan3DOmni":          "🔷 Hunyuan3D-Omni 多模态",
    "Cortex3d_MultiviewReconstruction":"🔷 多视角 3D 重建（InstantMesh）",
    # 后处理
    "Cortex3d_UltraShapeRefiner":      "💎 UltraShape 几何精化",
    "Cortex3d_MeshSharpener":          "🔪 网格锐化",
    "Cortex3d_BlenderPrintPrep":       "🖨️ Blender 3D 打印预处理",
    "Cortex3d_MeshValidator":          "✅ 网格质量验证",
    # 编辑
    "Cortex3d_ClothingExtractor":      "👗 智能服装提取",
    "Cortex3d_WardrobeChange":         "👔 AI 换装",
    "Cortex3d_StyleTransfer":          "🎭 风格迁移",
    # 工具
    "Cortex3d_DockerManager":          "🐳 Docker 容器管理",
    "Cortex3d_MeshLoader":             "📂 网格文件加载",
    "Cortex3d_MeshSaver":              "💾 网格文件保存",
    "Cortex3d_QualityPreset":          "⚙️ 质量预设",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
