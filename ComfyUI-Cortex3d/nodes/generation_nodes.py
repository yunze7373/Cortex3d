"""图像生成类节点 (5) — Gemini / AiProxy / Z-Image / Qwen。"""
from __future__ import annotations
import os
from ..utils.errors import node_guard

CAT = "Cortex3d/Generate"

# ─────────────────────────────────────────────────────────────────────────────
# 辅助：从磁盘 PNG 列表转成 ComfyUI IMAGE batch tensor
# ─────────────────────────────────────────────────────────────────────────────
def _paths_to_batch(paths: list[str]):
    """将文件路径列表转成 B×H×W×C float32 tensor (ComfyUI IMAGE)。"""
    import torch
    from ..bridge.file_bridge import FileBridge
    fb = FileBridge()
    tensors = [fb.path_to_tensor(p) for p in paths if p and os.path.isfile(p)]
    if not tensors:
        return torch.zeros(1, 64, 64, 3)
    return torch.cat(tensors, dim=0)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Gemini 多视角生成器
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_GeminiGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt":      ("STRING", {"multiline": True}),
                "view_config": ("CORTEX_VIEW_CONFIG",),
                "api_key":     ("STRING", {"default": ""}),
            },
            "optional": {
                "model_name":        (["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],),
                "negative_prompt":   ("STRING", {"multiline": True, "default": ""}),
                "reference_image":   ("IMAGE",),
                "resolution":        ("INT", {"default": 1024, "min": 512, "max": 2048, "step": 64}),
                "use_strict_mode":   ("BOOLEAN", {"default": False}),
                "seed":              ("INT", {"default": 0, "min": 0, "max": 2**31}),
            }
        }

    RETURN_TYPES  = ("IMAGE", "CORTEX_VIEW_CONFIG", "STRING")
    RETURN_NAMES  = ("images", "view_config", "output_dir")
    FUNCTION      = "execute"
    CATEGORY      = CAT
    OUTPUT_IS_LIST = (True, False, False)

    @node_guard()
    def execute(self, prompt, view_config, api_key,
                model_name="gemini-2.0-flash-exp", negative_prompt="",
                reference_image=None, resolution=1024,
                use_strict_mode=False, seed=0):
        from ..adapters.gemini_adapter import GeminiAdapter
        from ..bridge.file_bridge import FileBridge
        import torch

        fb = FileBridge()
        ref_path = None
        if reference_image is not None:
            ref_path = fb.tensor_to_tmp_png(reference_image)

        results = GeminiAdapter.generate_views(
            character_description=prompt,
            api_key=api_key or os.environ.get("GEMINI_API_KEY", ""),
            model_name=model_name,
            view_config=view_config,
            negative_prompt=negative_prompt,
            reference_image_path=ref_path,
            resolution=resolution,
            use_strict_mode=use_strict_mode,
            seed=seed if seed > 0 else None,
        )
        out_dir = results.get("output_dir", "")
        file_paths = results.get("image_paths", [])
        tensors = [fb.path_to_tensor(p) for p in file_paths if p and os.path.isfile(p)]
        if not tensors:
            tensors = [torch.zeros(1, resolution, resolution, 3)]
        return (tensors, view_config, out_dir)


# ─────────────────────────────────────────────────────────────────────────────
# 2. AiProxy 图像生成（云端图像模型代理）
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_AiProxyGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt":   ("STRING", {"multiline": True}),
                "api_key":  ("STRING", {"default": ""}),
                "model":    (["flux-kontext-pro", "flux-dev", "stable-diffusion-3.5"], {"default": "flux-kontext-pro"}),
                "width":    ("INT", {"default": 1024, "min": 512, "max": 2048, "step": 64}),
                "height":   ("INT", {"default": 1024, "min": 512, "max": 2048, "step": 64}),
            },
            "optional": {
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "reference_image": ("IMAGE",),
                "seed":            ("INT", {"default": 0, "min": 0, "max": 2**31}),
                "steps":           ("INT", {"default": 20, "min": 1, "max": 50}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, prompt, api_key, model, width, height,
                negative_prompt="", reference_image=None, seed=0, steps=20):
        from ..adapters.aiproxy_adapter import AiProxyAdapter
        from ..bridge.file_bridge import FileBridge
        from ..types.mesh import CortexMesh
        import torch

        fb = FileBridge()
        ref_path = None
        if reference_image is not None:
            ref_path = fb.tensor_to_tmp_png(reference_image)

        out = fb.make_output_dir("comfyui_aiproxy")
        img_path = AiProxyAdapter.generate_image(
            prompt=prompt,
            api_key=api_key or os.environ.get("AIPROXY_API_KEY", ""),
            model=model, width=width, height=height,
            negative_prompt=negative_prompt,
            reference_image_path=ref_path,
            seed=seed if seed > 0 else None,
            steps=steps, output_dir=str(out),
        )
        if img_path and os.path.isfile(img_path):
            return (fb.path_to_tensor(img_path),)
        return (torch.zeros(1, height, width, 3),)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Z-Image-Turbo 文生图
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_ZImageGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt":      ("STRING", {"multiline": True}),
                "server_url":  ("STRING", {"default": "http://localhost:8199"}),
                "width":       ("INT", {"default": 1024, "min": 512, "max": 2048, "step": 64}),
                "height":      ("INT", {"default": 1024, "min": 512, "max": 2048, "step": 64}),
            },
            "optional": {
                "steps":  ("INT",  {"default": 20, "min": 1, "max": 50}),
                "seed":   ("INT",  {"default": 0,  "min": 0, "max": 2**31}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, prompt, server_url, width, height, steps=20, seed=0):
        from ..adapters.zimage_adapter import ZImageAdapter
        from ..bridge.file_bridge import FileBridge
        import torch
        fb = FileBridge()
        out = fb.make_output_dir("comfyui_zimage")
        img_path = ZImageAdapter(server_url=server_url).generate(
            prompt=prompt, width=width, height=height,
            steps=steps, seed=seed if seed > 0 else None,
            output_dir=str(out),
        )
        if img_path and os.path.isfile(img_path):
            return (fb.path_to_tensor(img_path),)
        return (torch.zeros(1, height, width, 3),)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Z-Image-Turbo 图生图
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_ZImageImg2Img:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":       ("IMAGE",),
                "prompt":      ("STRING", {"multiline": True}),
                "server_url":  ("STRING", {"default": "http://localhost:8199"}),
                "strength":    ("FLOAT",  {"default": 0.75, "min": 0.0, "max": 1.0, "step": 0.05}),
            },
            "optional": {
                "steps": ("INT", {"default": 20, "min": 1, "max": 50}),
                "seed":  ("INT", {"default": 0,  "min": 0, "max": 2**31}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, image, prompt, server_url, strength, steps=20, seed=0):
        from ..adapters.zimage_adapter import ZImageAdapter
        from ..bridge.file_bridge import FileBridge
        import torch
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        out = fb.make_output_dir("comfyui_zimage_i2i")
        result = ZImageAdapter(server_url=server_url).img2img(
            image_path=img_path, prompt=prompt, strength=strength,
            steps=steps, seed=seed if seed > 0 else None, output_dir=str(out),
        )
        if result and os.path.isfile(result):
            return (fb.path_to_tensor(result),)
        return (image,)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Qwen-Image-Edit 图像编辑
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_QwenImageEdit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":       ("IMAGE",),
                "prompt":      ("STRING", {"multiline": True}),
                "server_url":  ("STRING", {"default": "http://localhost:8200"}),
            },
            "optional": {
                "cfg_scale": ("FLOAT", {"default": 7.5, "min": 1.0, "max": 20.0, "step": 0.5}),
                "steps":     ("INT",   {"default": 30, "min": 1, "max": 100}),
                "seed":      ("INT",   {"default": 0,  "min": 0, "max": 2**31}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, image, prompt, server_url, cfg_scale=7.5, steps=30, seed=0):
        from ..adapters.qwen_adapter import QwenAdapter
        from ..bridge.file_bridge import FileBridge
        import torch
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        out = fb.make_output_dir("comfyui_qwen")
        result = QwenAdapter(server_url=server_url).edit(
            image_path=img_path, prompt=prompt,
            cfg_scale=cfg_scale, steps=steps,
            seed=seed if seed > 0 else None, output_dir=str(out),
        )
        if result and os.path.isfile(result):
            return (fb.path_to_tensor(result),)
        return (image,)
