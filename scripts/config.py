#!/usr/bin/env python3
"""
Cortex3d 配置模块
统一管理提示词模板、模型名称和其他配置

所有生成脚本（aiproxy_client, gemini_generator）都从这里导入配置

v2.0 更新:
- 提示词模板迁移到 prompts/ 目录
- 支持 4/6/8 视角和自定义视角
- 新增负面提示词支持
- 保持向后兼容的 API
"""

import os
from typing import List, Optional

try:
    from dotenv import load_dotenv
    # 加载 .env 文件 (从当前目录或父目录)
    load_dotenv()
except ImportError:
    pass  # 如果没装 python-dotenv 就跳过


# =============================================================================
# 模型配置 - 统一管理，代理和直连使用相同名称
# =============================================================================

# 图像生成模型 (NanoBanana Pro)
IMAGE_MODEL = "models/nano-banana-pro-preview"

# 文本模型
TEXT_MODEL = "gemini-2.0-flash"

# AiProxy 服务地址
AIPROXY_BASE_URL = os.environ.get("AIPROXY_URL", "https://bot.bigjj.click/aiproxy")


# =============================================================================
# 提示词库 - 从 prompts/ 目录加载
# =============================================================================

# 延迟导入提示词库，避免循环导入
_prompt_library = None


def _get_prompt_library():
    """获取提示词库实例（延迟加载）"""
    global _prompt_library
    if _prompt_library is None:
        try:
            from prompts import prompt_library
            _prompt_library = prompt_library
        except ImportError:
            # 如果导入失败，使用旧版硬编码模板
            _prompt_library = None
    return _prompt_library


# =============================================================================
# 向后兼容的 API - 保持原有函数签名
# =============================================================================

def build_multiview_prompt(
    character_description: str,
    style: str = "cinematic character",
    view_mode: str = "4-view",
    custom_views: List[str] = None
) -> str:
    """
    构建多视图角色生成提示词
    
    Args:
        character_description: 角色描述（外貌、服装、配件等）
        style: 整体风格描述
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表 (仅 custom 模式)
    
    Returns:
        完整的提示词字符串
    """
    lib = _get_prompt_library()
    if lib:
        return lib.build_multiview_prompt(
            character_description=character_description,
            style=style,
            view_mode=view_mode,
            custom_views=custom_views
        )
    
    # 回退到硬编码模板（旧版兼容）
    return _LEGACY_MULTIVIEW_TEMPLATE.format(
        character_description=character_description,
        style=style
    )


def build_image_reference_prompt(
    character_description: str,
    view_mode: str = "4-view",
    custom_views: List[str] = None,
    style: str = None
) -> str:
    """
    构建图片参考模式专用提示词（保留原图动作）
    
    Args:
        character_description: 从参考图片提取的角色描述
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表 (仅 custom 模式)
        style: 风格描述 (photorealistic, anime, 或自定义)
    
    Returns:
        完整的提示词字符串
    """
    lib = _get_prompt_library()
    if lib:
        return lib.build_image_reference_prompt(
            character_description=character_description,
            view_mode=view_mode,
            custom_views=custom_views,
            style=style
        )
    
    # 回退到硬编码模板
    return _LEGACY_IMAGE_REF_TEMPLATE.format(
        character_description=character_description
    )


def build_strict_copy_prompt(
    view_mode: str = "4-view",
    custom_views: List[str] = None,
    style: str = None
) -> str:
    """
    构建严格复制模式提示词（100%复制原图）
    
    Args:
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表 (仅 custom 模式)
        style: 风格描述 (photorealistic, anime, 或自定义)
    
    Returns:
        完整的提示词字符串
    """
    lib = _get_prompt_library()
    if lib:
        return lib.build_strict_copy_prompt(
            view_mode=view_mode,
            custom_views=custom_views,
            style=style
        )
    
    return _LEGACY_STRICT_COPY_TEMPLATE


def get_negative_prompt(categories: List[str] = None) -> str:
    """
    获取负面提示词（合并多个类别）
    
    Args:
        categories: 类别列表，可选 ["anatomy", "quality", "layout"]
                    默认使用所有类别
    
    Returns:
        负面提示词字符串
    """
    lib = _get_prompt_library()
    if lib:
        return lib.get_negative_prompt(categories)
    
    # 回退到硬编码负面提示词
    return _LEGACY_NEGATIVE_PROMPT


# =============================================================================
# 新增 API - 多视角支持
# =============================================================================

def get_view_config(view_mode: str = "4-view", custom_views: List[str] = None):
    """
    获取视角配置信息
    
    Args:
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表
    
    Returns:
        (views, rows, cols, aspect_ratio) 元组
    """
    try:
        from prompts.views import (
            get_views_for_mode,
            get_views_by_names,
            get_layout_for_views
        )
        
        if view_mode == "custom" and custom_views:
            views = get_views_by_names(custom_views)
        else:
            views = get_views_for_mode(view_mode)
        
        view_count = len(views)
        rows, cols, aspect = get_layout_for_views(view_count)
        
        return views, rows, cols, aspect
    except ImportError:
        # 回退默认值
        return None, 1, 4, "3:2"


def get_available_views() -> List[str]:
    """获取所有可用的视角名称"""
    try:
        from prompts.views import get_all_view_names
        return get_all_view_names()
    except ImportError:
        return ["front", "right", "back", "left"]


def get_view_presets() -> dict:
    """获取视角预设配置"""
    try:
        from prompts.views import VIEW_PRESETS
        return VIEW_PRESETS
    except ImportError:
        return {
            "4-view": ["front", "right", "back", "left"],
            "6-view": ["front", "front_right", "right", "back", "left", "front_left"],
            "8-view": ["front", "front_right", "right", "back", "left", "front_left", "top", "bottom"]
        }


# =============================================================================
# 预设角色模板
# =============================================================================

PRESET_CHARACTERS = {
    "zombie_santa": """• Head-body ratio: 1:7.5 (Realistic human proportions)
• Expression: Weary, vigilant gaze with grim determination
• Face: Dirty white beard stained with blood and grime, weathered skin
• Body: Upright posture, right hand holding a fire axe at side
• Clothing: Tattered red Santa suit covered in blood and dirt
• Hat: Damaged Santa hat, worn and dirty
• Accessories: Old gift sack converted to survival bag on back
• Shoes: Worn black boots covered in mud""",

    "apocalypse_businessman": """• Head-body ratio: 1:7.5 (Realistic human proportions, lean and weathered)
• Expression: Intense, vigilant, weary gaze with grim determination
• Face: Grimy skin texture, stubble beard, perhaps a small scar
• Body: Upright tense posture, with a defensive stance
• Clothing: A once-expensive bespoke suit now tattered and torn
• Shirt: White dress shirt that is yellowed, stained with sweat, mud, and dried blood
• Pants: Suit trousers with rips at the knees, covered in dust and mud
• Accessories: A shoulder holster with a pistol, a watch on the wrist
• Shoes: Scuffed leather dress shoes covered in mud""",
}


# =============================================================================
# 辅助函数
# =============================================================================

def get_character_prompt(
    preset_name: str = None,
    custom_description: str = None,
    style: str = "cinematic character",
    view_mode: str = "4-view",
    custom_views: List[str] = None
) -> str:
    """
    获取角色生成的完整提示词
    
    Args:
        preset_name: 预设角色名称 (zombie_santa, apocalypse_businessman)
        custom_description: 自定义角色描述
        style: 风格描述
        view_mode: 视角模式
        custom_views: 自定义视角列表
    
    Returns:
        完整的提示词
    """
    if preset_name and preset_name in PRESET_CHARACTERS:
        description = PRESET_CHARACTERS[preset_name]
    elif custom_description:
        description = custom_description
    else:
        description = PRESET_CHARACTERS["zombie_santa"]
    
    return build_multiview_prompt(
        character_description=description,
        style=style,
        view_mode=view_mode,
        custom_views=custom_views
    )


# =============================================================================
# 旧版硬编码模板 (仅作回退使用)
# =============================================================================

_LEGACY_MULTIVIEW_TEMPLATE = """Generate a professional 3D character turntable reference sheet with exactly 4 panels arranged horizontally.

## OUTPUT REQUIREMENT
Single image containing 4 panels in a row: [FRONT] [RIGHT] [BACK] [LEFT]

## CHARACTER
{character_description}
Style: {style}

## CRITICAL RULES - READ CAREFULLY

### TURNTABLE ROTATION (NOT MIRROR!)
Imagine the character standing on a rotating platform:
- Panel 1 (FRONT): Platform at 0° - We see the FACE, chest, front of body
- Panel 2 (RIGHT SIDE): Platform rotated 90° clockwise - We see the RIGHT ear, RIGHT shoulder, RIGHT hip
- Panel 3 (BACK): Platform rotated 180° - We see back of HEAD, spine, buttocks
- Panel 4 (LEFT SIDE): Platform rotated 270° clockwise - We see the LEFT ear, LEFT shoulder, LEFT hip

⚠️ IMPORTANT: Panels 2 and 4 are NOT mirrors! They show OPPOSITE sides of the body!

### ANATOMICAL CORRECTNESS (CRITICAL!)
- Arms MUST connect to shoulders only
- Legs MUST connect to hips only
- NO extra limbs, NO twisted body parts

### POSE CONSISTENCY (CRITICAL!)
- EXACT same pose in ALL 4 panels - only the viewing angle changes

### PANEL LAYOUT
- 4 equal-width panels arranged horizontally
- Neutral gray or white background

### ABSOLUTELY FORBIDDEN
- NO text labels
- NO twisted bodies
- NO anatomical errors
- NO pose variations between panels

Generate a clean, professional character reference sheet following ALL rules above."""

_LEGACY_IMAGE_REF_TEMPLATE = """Generate a 3D character turntable reference sheet with exactly 4 panels, showing the character described below from 4 angles.

## OUTPUT
Single image with 4 panels horizontally: [FRONT] [RIGHT] [BACK] [LEFT]

## CHARACTER DESCRIPTION (from reference photo)
{character_description}

## CRITICAL: PRESERVE THE ORIGINAL POSE
You MUST preserve the original pose from the reference.

## TURNTABLE ROTATION
- Panel 1 (FRONT): 0° - facing camera
- Panel 2 (RIGHT): 90° - right side visible
- Panel 3 (BACK): 180° - back visible
- Panel 4 (LEFT): 270° - left side visible

Generate the character maintaining the EXACT pose described, viewed from 4 angles."""

_LEGACY_STRICT_COPY_TEMPLATE = """Create a 4-panel CHARACTER TURNTABLE showing THIS PERSON from the reference image.

## THE 4 DISTINCT VIEWS
| Panel | Angle | What You See |
|-------|-------|--------------|
| 1 | 0° (FRONT) | Face visible |
| 2 | 90° (RIGHT SIDE) | Right ear visible |
| 3 | 180° (BACK) | Back of head only |
| 4 | 270° (LEFT SIDE) | Left ear visible |

## REQUIREMENTS
- EACH VIEW MUST BE UNIQUE
- NO text labels

## OUTPUT
Single horizontal image: [FRONT] [RIGHT] [BACK] [LEFT]"""

_LEGACY_NEGATIVE_PROMPT = "extra limbs, missing limbs, extra fingers, deformed hands, twisted body, low quality, blurry, watermark, text, duplicate panels"
