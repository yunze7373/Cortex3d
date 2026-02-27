"""图像编辑类节点 (3) — 服装提取 / 换装 / 风格迁移。"""
from __future__ import annotations
import os
from ..utils.errors import node_guard

CAT = "Cortex3d/Edit"


class Cortex3d_ClothingExtractor:
    """从参考图中提取服装区域（使用 Qwen-Image-Edit 或 rembg 掩码）。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":      ("IMAGE",),
                "server_url": ("STRING", {"default": "http://localhost:8200"}),
            },
            "optional": {
                "clothing_description": ("STRING", {"multiline": True, "default": ""}),
                "cfg_scale": ("FLOAT", {"default": 7.5, "min": 1.0, "max": 20.0}),
                "steps":     ("INT",   {"default": 30, "min": 1, "max": 100}),
            }
        }

    RETURN_TYPES  = ("IMAGE", "STRING")
    RETURN_NAMES  = ("clothing_image", "description")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, image, server_url, clothing_description="", cfg_scale=7.5, steps=30):
        from ..adapters.qwen_adapter import QwenAdapter
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        out_dir = str(fb.make_output_dir("comfyui_clothing"))

        prompt = (
            f"Extract only the clothing/outfit from this character. "
            f"{'Target clothing: ' + clothing_description + '. ' if clothing_description else ''}"
            "Remove the character, keep clothing isolated on white background."
        )
        result = QwenAdapter(server_url=server_url).edit(
            image_path=img_path, prompt=prompt, cfg_scale=cfg_scale, steps=steps, output_dir=out_dir,
        )
        if result and os.path.isfile(result):
            return (fb.path_to_tensor(result), clothing_description or "extracted clothing")
        return (image, clothing_description or "extraction failed")


class Cortex3d_WardrobeChange:
    """在人物图上更换服装（参考服装图 → 智能换装）。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_image": ("IMAGE",),
                "clothing_image":  ("IMAGE",),
                "server_url":      ("STRING", {"default": "http://localhost:8200"}),
            },
            "optional": {
                "clothing_description": ("STRING", {"multiline": True, "default": ""}),
                "cfg_scale": ("FLOAT", {"default": 7.5, "min": 1.0, "max": 20.0}),
                "steps":     ("INT",   {"default": 30, "min": 1, "max": 100}),
                "seed":      ("INT",   {"default": 0}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("result_image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, character_image, clothing_image, server_url,
                clothing_description="", cfg_scale=7.5, steps=30, seed=0):
        from ..adapters.qwen_adapter import QwenAdapter
        from ..bridge.file_bridge import FileBridge
        import tempfile, os
        fb = FileBridge()

        char_path     = fb.tensor_to_tmp_png(character_image)
        clothing_path = fb.tensor_to_tmp_png(clothing_image)
        out_dir       = str(fb.make_output_dir("comfyui_wardrobe"))

        prompt = (
            f"Change the character's outfit to match the provided clothing reference. "
            f"{clothing_description or 'Keep the character pose and face identical.'}"
        )
        # Qwen 目前只接受单图；将服装图路径写入提示词
        full_prompt = f"[Reference clothing image saved at: {clothing_path}]. {prompt}"
        result = QwenAdapter(server_url=server_url).edit(
            image_path=char_path, prompt=full_prompt,
            cfg_scale=cfg_scale, steps=steps,
            seed=seed if seed > 0 else None, output_dir=out_dir,
        )
        if result and os.path.isfile(result):
            return (fb.path_to_tensor(result),)
        return (character_image,)


class Cortex3d_StyleTransfer:
    """将画风（如写实→动漫）迁移到目标图像，保留角色结构。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":      ("IMAGE",),
                "target_style": (["anime", "realistic", "chibi", "watercolor", "oil_painting", "pixel_art"],),
                "server_url": ("STRING", {"default": "http://localhost:8200"}),
            },
            "optional": {
                "style_strength": ("FLOAT", {"default": 0.75, "min": 0.1, "max": 1.0, "step": 0.05}),
                "cfg_scale":      ("FLOAT", {"default": 7.5, "min": 1.0, "max": 20.0}),
                "steps":          ("INT",   {"default": 30, "min": 1, "max": 100}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    _STYLE_PROMPTS = {
        "anime":       "convert to high-quality anime illustration style, cel shading, vibrant colors",
        "realistic":   "convert to photorealistic style, high-detail skin texture, cinematic lighting",
        "chibi":       "convert to cute chibi style, big eyes, small body proportions, pastel colors",
        "watercolor":  "convert to watercolor painting style, soft edges, translucent washes",
        "oil_painting":"convert to classic oil painting style, rich texture, impasto technique",
        "pixel_art":   "convert to retro 16-bit pixel art style, limited palette, dithering",
    }

    @node_guard()
    def execute(self, image, target_style, server_url, style_strength=0.75, cfg_scale=7.5, steps=30):
        from ..adapters.qwen_adapter import QwenAdapter
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        out_dir  = str(fb.make_output_dir("comfyui_style"))

        style_desc = self._STYLE_PROMPTS.get(target_style, f"{target_style} style")
        prompt = (
            f"{style_desc}. Maintain the character's pose, proportions, and identity. "
            f"Style transfer strength: {style_strength:.0%}."
        )
        result = QwenAdapter(server_url=server_url).edit(
            image_path=img_path, prompt=prompt, cfg_scale=cfg_scale, steps=steps, output_dir=out_dir,
        )
        if result and os.path.isfile(result):
            return (fb.path_to_tensor(result),)
        return (image,)
