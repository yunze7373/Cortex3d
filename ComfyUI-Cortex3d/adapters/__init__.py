"""Adapters — 对现有 Cortex3d scripts/ 的 Python 调用封装层。"""

from .prompt_adapter import PromptAdapter
from .gemini_adapter import GeminiAdapter
from .aiproxy_adapter import AiProxyAdapter
from .zimage_adapter import ZImageAdapter
from .qwen_adapter import QwenAdapter
from .image_adapter import ImageAdapter
from .instantmesh_adapter import InstantMeshAdapter
from .triposr_adapter import TripoSRAdapter
from .trellis2_adapter import Trellis2Adapter
from .hunyuan3d_adapter import Hunyuan3DAdapter
from .ultrashape_adapter import UltraShapeAdapter
from .blender_adapter import BlenderAdapter

__all__ = [
    "PromptAdapter",
    "GeminiAdapter",
    "AiProxyAdapter",
    "ZImageAdapter",
    "QwenAdapter",
    "ImageAdapter",
    "InstantMeshAdapter",
    "TripoSRAdapter",
    "Trellis2Adapter",
    "Hunyuan3DAdapter",
    "UltraShapeAdapter",
    "BlenderAdapter",
]
