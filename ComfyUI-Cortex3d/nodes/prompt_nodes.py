"""Prompt 类节点 (6) — 生成/组合 Cortex3d 风格化提示词。"""
from __future__ import annotations

# ─── 全局分类前缀 ───────────────────────────────────────────────────────────
CAT = "Cortex3d/Prompt"

# ───────────────────────────────────────────────────────────────────────────
# 1. 多视角提示词构建器
# ───────────────────────────────────────────────────────────────────────────
class Cortex3d_MultiviewPromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_description": ("STRING", {"multiline": True, "default": "anime girl with long silver hair"}),
                "style":    (["anime", "realistic", "chibi", "western", "sci-fi"], {"default": "anime"}),
                "view_mode": (["standard_4", "standard_6", "turntable_8", "custom"], {"default": "standard_4"}),
            },
            "optional": {
                "subject_only": ("BOOLEAN", {"default": False}),
                "with_props":   ("BOOLEAN", {"default": False}),
                "custom_views": ("STRING",  {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES  = ("STRING", "CORTEX_VIEW_CONFIG")
    RETURN_NAMES  = ("prompt", "view_config")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, character_description, style, view_mode,
                subject_only=False, with_props=False, custom_views=""):
        from ..adapters.prompt_adapter import PromptAdapter
        from ..types.view_config import CortexViewConfig
        prompt = PromptAdapter.build_multiview_prompt(
            character_description=character_description,
            style=style, view_mode=view_mode,
            custom_views=custom_views or None,
            subject_only=subject_only, with_props=with_props,
        )
        vc_data = PromptAdapter.get_view_config(view_mode, custom_views or None)
        view_cfg = CortexViewConfig.from_config_result(vc_data)
        return (prompt, view_cfg)


# ───────────────────────────────────────────────────────────────────────────
# 2. 参考图提示词构建器
# ───────────────────────────────────────────────────────────────────────────
class Cortex3d_ImageRefPromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_image": ("IMAGE",),
                "character_description": ("STRING", {"multiline": True, "default": ""}),
                "style": (["anime", "realistic", "chibi", "western", "sci-fi"], {"default": "anime"}),
            },
            "optional": {
                "view_mode": (["standard_4", "standard_6", "turntable_8"], {"default": "standard_4"}),
            }
        }

    RETURN_TYPES  = ("STRING", "CORTEX_VIEW_CONFIG", "STRING")   # prompt, view_config, ref_image_path
    RETURN_NAMES  = ("prompt", "view_config", "ref_image_path")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, reference_image, character_description, style, view_mode="standard_4"):
        from ..adapters.prompt_adapter import PromptAdapter
        from ..types.view_config import CortexViewConfig
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        ref_path = fb.tensor_to_tmp_png(reference_image)
        prompt = PromptAdapter.build_image_reference_prompt(
            character_description=character_description,
            style=style, view_mode=view_mode,
        )
        vc_data = PromptAdapter.get_view_config(view_mode)
        view_cfg = CortexViewConfig.from_config_result(vc_data)
        return (prompt, view_cfg, ref_path)


# ───────────────────────────────────────────────────────────────────────────
# 3. 严格复制提示词构建器
# ───────────────────────────────────────────────────────────────────────────
class Cortex3d_StrictCopyPromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_description": ("STRING", {"multiline": True, "default": ""}),
                "style": (["anime", "realistic", "chibi", "western", "sci-fi"], {"default": "anime"}),
                "view_mode": (["standard_4", "standard_6", "turntable_8"], {"default": "standard_4"}),
            }
        }

    RETURN_TYPES  = ("STRING", "CORTEX_VIEW_CONFIG")
    RETURN_NAMES  = ("prompt", "view_config")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, character_description, style, view_mode):
        from ..adapters.prompt_adapter import PromptAdapter
        from ..types.view_config import CortexViewConfig
        prompt = PromptAdapter.build_strict_copy_prompt(
            character_description=character_description, style=style, view_mode=view_mode,
        )
        vc_data = PromptAdapter.get_view_config(view_mode)
        return (prompt, CortexViewConfig.from_config_result(vc_data))


# ───────────────────────────────────────────────────────────────────────────
# 4. 复合场景提示词构建器
# ───────────────────────────────────────────────────────────────────────────
class Cortex3d_CompositePromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_description": ("STRING", {"multiline": True, "default": ""}),
                "style": (["anime", "realistic", "chibi", "western", "sci-fi"],),
                "scene_description": ("STRING", {"multiline": True, "default": "standing in a neutral studio"}),
                "view_mode": (["standard_4", "standard_6", "turntable_8"],),
            }
        }

    RETURN_TYPES  = ("STRING", "CORTEX_VIEW_CONFIG")
    RETURN_NAMES  = ("prompt", "view_config")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, character_description, style, scene_description, view_mode):
        from ..adapters.prompt_adapter import PromptAdapter
        from ..types.view_config import CortexViewConfig
        prompt = PromptAdapter.build_composite_prompt(
            character_description=character_description,
            style=style, scene_description=scene_description, view_mode=view_mode,
        )
        vc_data = PromptAdapter.get_view_config(view_mode)
        return (prompt, CortexViewConfig.from_config_result(vc_data))


# ───────────────────────────────────────────────────────────────────────────
# 5. 负面提示词
# ───────────────────────────────────────────────────────────────────────────
class Cortex3d_NegativePrompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "style": (["anime", "realistic", "chibi", "western", "sci-fi"],),
            },
            "optional": {
                "extra_negative": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES  = ("STRING",)
    RETURN_NAMES  = ("negative_prompt",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, style, extra_negative=""):
        from ..adapters.prompt_adapter import PromptAdapter
        neg = PromptAdapter.get_negative_prompt(style=style)
        if extra_negative:
            neg = f"{neg}, {extra_negative}"
        return (neg,)


# ───────────────────────────────────────────────────────────────────────────
# 6. 预设提示词加载
# ───────────────────────────────────────────────────────────────────────────
class Cortex3d_PromptPreset:
    PRESETS = [
        "cute_anime_girl", "armored_warrior", "mecha_robot",
        "fantasy_wizard", "sci_fi_soldier", "chibi_mascot",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "preset_name": (cls.PRESETS,),
                "view_mode":   (["standard_4", "standard_6", "turntable_8"],),
            }
        }

    RETURN_TYPES  = ("STRING", "CORTEX_VIEW_CONFIG")
    RETURN_NAMES  = ("prompt", "view_config")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, preset_name, view_mode):
        from ..adapters.prompt_adapter import PromptAdapter
        from ..types.view_config import CortexViewConfig
        prompt = PromptAdapter.load_preset(preset_name=preset_name, view_mode=view_mode)
        vc_data = PromptAdapter.get_view_config(view_mode)
        return (prompt, CortexViewConfig.from_config_result(vc_data))
