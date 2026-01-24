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

# 图像生成模型 (NanoBanana Pro) - 用于 proxy/direct 模式
IMAGE_MODEL = "models/nano-banana-pro-preview"

# 文本模型
TEXT_MODEL = "gemini-2.0-flash"

# AiProxy 服务地址
AIPROXY_BASE_URL = os.environ.get("AIPROXY_URL", "https://bot.bigjj.click/aiproxy")

# =============================================================================
# 本地模型配置 (Z-Image-Turbo)
# =============================================================================

# Z-Image 本地服务地址
ZIMAGE_LOCAL_URL = os.environ.get("ZIMAGE_URL", "http://localhost:8199")

# Z-Image 模型名称
ZIMAGE_MODEL = "Tongyi-MAI/Z-Image-Turbo"

# 支持的生成后端
GENERATION_BACKENDS = ["proxy", "direct", "local"]

# 本地默认使用 Z-Image
DEFAULT_LOCAL_BACKEND = "zimage"



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

def _build_subject_instructions(subject_only: bool = False, with_props: List[str] = None) -> str:
    """
    构建主体隔离指令
    
    Args:
        subject_only: 只处理主体，移除背景物体
        with_props: 要包含的道具列表
    
    Returns:
        主体隔离指令字符串
    """
    if subject_only:
        return """
## ⚠️ SUBJECT ISOLATION - REMOVE BACKGROUND OBJECTS
**IMPORTANT: Extract ONLY the main person/character from the reference.**

- ❌ REMOVE all background objects (cars, furniture, buildings, scenery)
- ❌ REMOVE any objects the subject is leaning on, sitting in, or standing near
- ✅ KEEP only the main person/character
- ✅ Place the isolated subject on a clean neutral background
- The subject should appear to be standing/floating alone

Think of it as: Extract the person and place them in an empty photo studio.
"""
    elif with_props:
        props_list = ", ".join(with_props)
        return f"""
## ⚠️ SUBJECT WITH PROPS - INCLUDE SPECIFIC OBJECTS
**IMPORTANT: Process the main subject TOGETHER with these items: {props_list}**

- ✅ KEEP the main person/character
- ✅ KEEP these specific props/objects: {props_list}
- ❌ REMOVE all other background objects not in the list above
- The subject and their props should appear together on a clean neutral background

These props are considered part of the subject and must appear in ALL views:
{chr(10).join(f'  - {prop}' for prop in with_props)}
"""
    else:
        return ""


def build_multiview_prompt(
    character_description: str,
    style: str = "cinematic character",
    view_mode: str = "4-view",
    custom_views: List[str] = None,
    subject_only: bool = False,
    with_props: List[str] = None
) -> str:
    """
    构建多视图角色生成提示词
    
    Args:
        character_description: 角色描述（外貌、服装、配件等）
        style: 整体风格描述
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表 (仅 custom 模式)
        subject_only: 只处理主体，移除背景物体
        with_props: 要包含的道具列表
    
    Returns:
        完整的提示词字符串
    """
    lib = _get_prompt_library()
    if lib:
        base_prompt = lib.build_multiview_prompt(
            character_description=character_description,
            style=style,
            view_mode=view_mode,
            custom_views=custom_views
        )
        # 添加主体隔离指令
        subject_instructions = _build_subject_instructions(subject_only, with_props)
        if subject_instructions:
            return base_prompt + "\n" + subject_instructions
        return base_prompt
    
    # 回退到硬编码模板（旧版兼容）
    return _LEGACY_MULTIVIEW_TEMPLATE.format(
        character_description=character_description,
        style=style
    )


def build_image_reference_prompt(
    character_description: str,
    view_mode: str = "4-view",
    custom_views: List[str] = None,
    style: str = None,
    subject_only: bool = False,
    with_props: List[str] = None
) -> str:
    """
    构建图片参考模式专用提示词（保留原图动作）
    
    Args:
        character_description: 从参考图片提取的角色描述
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表 (仅 custom 模式)
        style: 风格描述 (photorealistic, anime, 或自定义)
        subject_only: 只处理主体，移除背景物体
        with_props: 要包含的道具列表
    
    Returns:
        完整的提示词字符串
    """
    lib = _get_prompt_library()
    if lib:
        base_prompt = lib.build_image_reference_prompt(
            character_description=character_description,
            view_mode=view_mode,
            custom_views=custom_views,
            style=style
        )
        # 添加主体隔离指令
        subject_instructions = _build_subject_instructions(subject_only, with_props)
        if subject_instructions:
            return base_prompt + "\n" + subject_instructions
        return base_prompt
    
    # 回退到硬编码模板
    return _LEGACY_IMAGE_REF_TEMPLATE.format(
        character_description=character_description
    )


def build_strict_copy_prompt(
    view_mode: str = "4-view",
    custom_views: List[str] = None,
    style: str = None,
    subject_only: bool = False,
    with_props: List[str] = None
) -> str:
    """
    构建严格复制模式提示词（100%复制原图）
    
    Args:
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表 (仅 custom 模式)
        style: 风格描述 (photorealistic, anime, 或自定义)
        subject_only: 只处理主体，移除背景物体
        with_props: 要包含的道具列表
    
    Returns:
        完整的提示词字符串
    """
    lib = _get_prompt_library()
    if lib:
        base_prompt = lib.build_strict_copy_prompt(
            view_mode=view_mode,
            custom_views=custom_views,
            style=style
        )
        # 添加主体隔离指令
        subject_instructions = _build_subject_instructions(subject_only, with_props)
        if subject_instructions:
            return base_prompt + "\n" + subject_instructions
        return base_prompt
    
    return _LEGACY_STRICT_COPY_TEMPLATE


def build_composite_prompt(
    instruction: str,
    composite_type: str = "clothing",
    num_images: int = 2,
    style: str = None
) -> str:
    """
    构建高精度合成提示词（换装、配饰等）
    
    使用 PromptLibrary + YAML 模板系统，与多视角生成共享风格预设。
    
    Args:
        instruction: 用户的合成指令
        composite_type: 合成类型 ("clothing", "accessory", "general", "auto")
        num_images: 图片数量
        style: 风格（anime, photorealistic 等）
    
    Returns:
        完整的提示词字符串
    """
    # 优先使用 PromptLibrary 系统（与多视角生成统一）
    lib = _get_prompt_library()
    if lib and hasattr(lib, 'build_composite_prompt'):
        return lib.build_composite_prompt(
            instruction=instruction,
            composite_type=composite_type,
            style=style,
            num_images=num_images
        )
    
    # 回退：尝试使用 wardrobe 模块
    try:
        from prompts.wardrobe import build_wardrobe_prompt, detect_wardrobe_task
        
        # 自动检测任务类型
        if composite_type == "auto":
            composite_type = detect_wardrobe_task(instruction)
        
        # 映射到 wardrobe 任务类型
        task_type_map = {
            "clothing": "clothing",
            "accessory": "accessory",
            "general": "full_outfit"
        }
        task_type = task_type_map.get(composite_type, "clothing")
        
        return build_wardrobe_prompt(
            task_type=task_type,
            instruction=instruction,
            num_images=num_images,
            strict_mode=True,
            style=style
        )
    except ImportError:
        pass
    
    # 最终回退：硬编码模板（不推荐）
    # 自动检测合成类型
    if composite_type == "auto":
        lower_inst = instruction.lower()
        clothing_keywords = ["穿", "衣服", "裙", "裤", "上衣", "外套", "shirt", "dress", "wear", "clothing", "outfit", "换装", "换衣"]
        accessory_keywords = ["帽", "包", "眼镜", "配饰", "耳环", "项链", "手表", "hat", "bag", "glasses", "accessory", "戴", "jewelry"]
        
        if any(kw in lower_inst for kw in clothing_keywords):
            composite_type = "clothing"
        elif any(kw in lower_inst for kw in accessory_keywords):
            composite_type = "accessory"
        else:
            composite_type = "general"
    
    # 回退模板
    if composite_type == "clothing":
        return f"""Using the provided images, place the clothing/garment from Image 2 onto the person in Image 1.

Ensure that the following features of the person in Image 1 remain COMPLETELY UNCHANGED:
- Face: all facial features, expression, gaze direction, makeup
- Hair: exact style, length, color, texture
- Skin tone and any visible marks
- Body proportions and build
- Pose: exact body position, hand placement, leg stance, head angle
- Background: environment, lighting, shadows

The new clothing should:
- Fit naturally on the person's body shape and pose
- Have realistic fabric draping, folds, and wrinkles matching the pose
- Reflect the same lighting conditions as Image 1
- Create consistent shadows

User instruction: {instruction}

Generate a single photorealistic composite image. No text or annotations."""
    
    elif composite_type == "accessory":
        return f"""Using the provided images, place the accessory from Image 2 onto the person in Image 1.

Ensure that the following features of the person in Image 1 remain COMPLETELY UNCHANGED:
- Face: all facial features, expression, gaze direction
- Hair: style, length, color (unless the accessory is hair-related)
- Clothing: entire outfit, all garments, all details
- Body: proportions, build, pose, hand position
- Background: environment, lighting, shadows

The accessory should:
- Be positioned naturally and anatomically correct
- Be sized appropriately for the person
- Receive the same lighting as the subject
- Cast appropriate shadows

User instruction: {instruction}

Generate a single photorealistic composite image. No text or annotations."""
    
    else:  # general
        return f"""Using the provided images, combine elements according to the instruction.

Preserve the main subject (especially face and body) from Image 1 as much as possible.
Ensure seamless, natural blending with consistent lighting and perspective.

User instruction: {instruction}

Generate a single composite image. No text or annotations."""


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

_LEGACY_MULTIVIEW_TEMPLATE = """Generate a STRICT multi-view reference sheet with EXACTLY 4 panels.

This is a GEOMETRIC CAMERA ORBIT TASK, not a character redesign task.

The subject is a STATIC OBJECT in 3D space.
Only the CAMERA position changes.
NO pose correction, NO aesthetic adjustment, NO reinterpretation.

==================================================
## OUTPUT LAYOUT (MANDATORY)
Single image with exactly 4 equal-sized panels in ONE horizontal row only.

Order (left to right):
[FRONT 0°] [RIGHT 90°] [BACK 180°] [LEFT 270°]

No labels, no text, no markers inside the image.
==================================================

## CAMERA DEFINITION (CRITICAL)

Camera rotates around the subject at a fixed radius and height.
Camera target is the subject's original center.

The subject does NOT rotate.

--------------------------------------------------
### THE 4 REQUIRED VIEWS

Panel 1 — FRONT (0°):
- Camera faces the FRONT of the subject
- Subject front is fully visible
- This view must visually MATCH the reference image orientation

Panel 2 — RIGHT (90°):
- Camera is positioned on the SUBJECT'S RIGHT side
- The SUBJECT'S RIGHT SIDE faces the camera
- The subject's FRONT points toward the LEFT edge of the image

Panel 3 — BACK (180°):
- Camera faces the BACK of the subject
- Subject back is fully visible
- Subject front is completely hidden

Panel 4 — LEFT (270°):
- Camera is positioned on the SUBJECT'S LEFT side
- The SUBJECT'S LEFT SIDE faces the camera
- The subject's FRONT points toward the RIGHT edge of the image
--------------------------------------------------

==================================================
## 🔒 ABSOLUTE SPATIAL LOCK — ZERO DEVIATION ALLOWED

The subject is FROZEN in world space.

ALL spatial relationships are locked relative to the BODY, not the camera.

The following MUST remain 100% IDENTICAL across ALL panels:

- Head tilt, head rotation
- Eye direction and gaze angle (NO eye contact correction)
- Facial expression
- Shoulder angle
- Arm position, bend angle, hand orientation
- Leg stance, weight distribution, crossing order
- Torso lean, twist, and center of mass
- Clothing folds and attachment points
- Accessories, weapons, props and their relative positions

❌ DO NOT adjust pose for visibility
❌ DO NOT rotate body to face the camera
❌ DO NOT mirror or swap left/right anatomy
❌ DO NOT "fix" anatomy per view

ONLY perspective changes due to camera rotation are allowed.
==================================================

## 🎨 STYLE CONSTRAINTS
- Cinematic character design
- EXACT style match to reference image
- Identical materials, lighting mood, and surface detail
- Consistent rendering quality across all panels

==================================================
## CHARACTER
{character_description}

Style: {style}

==================================================
## BACKGROUND & ENVIRONMENT
- Pure neutral gray or white background
- Seamless, studio-style environment
- No visible floor, horizon, ground texture, or stage
- No turntable, pedestal, disc, or platform
- Subject appears naturally grounded without visible geometry

==================================================
## CONFIGURATION PARAMETERS
Resolution: 4K
Aspect Ratio: 3:2
Sampling: deterministic (low randomness)

==================================================
## FINAL HARD RULES

- EXACTLY 4 panels — no more, no less
- Identical scale and framing across panels
- No duplicated or mirrored views
- No creative interpretation
- Treat the subject as a scanned physical object

Failure to follow these rules is unacceptable."""

_LEGACY_IMAGE_REF_TEMPLATE = """Generate a STRICT multi-view reference sheet with EXACTLY 4 panels, based on the reference image.

This is a GEOMETRIC CAMERA ORBIT TASK, not a character redesign task.

The subject is a STATIC OBJECT in 3D space.
Only the CAMERA position changes.
NO pose correction, NO aesthetic adjustment, NO reinterpretation.

## OUTPUT LAYOUT (MANDATORY)
Single image with exactly 4 equal-sized panels in ONE horizontal row.
Order: [FRONT 0°] [RIGHT 90°] [BACK 180°] [LEFT 270°]

## CAMERA DEFINITION (CRITICAL)
- Camera rotates around the subject at a fixed radius and height
- Camera target is the subject's original center
- The subject does NOT rotate

## CHARACTER DESCRIPTION (from reference photo)
{character_description}

## 🔒 ABSOLUTE SPATIAL LOCK — ZERO DEVIATION ALLOWED
The subject is FROZEN in world space.

The following MUST remain 100% IDENTICAL across ALL panels:
- Head tilt, head rotation
- Eye direction and gaze angle (NO eye contact correction)
- Facial expression
- Shoulder angle
- Arm position, bend angle, hand orientation
- Leg stance, weight distribution, crossing order
- Torso lean, twist, center of mass
- Clothing folds and attachment points
- Accessories, weapons, props positions

❌ DO NOT adjust pose for visibility
❌ DO NOT rotate body to face the camera
❌ DO NOT mirror or swap left/right anatomy
❌ DO NOT "fix" anatomy per view

ONLY perspective changes from camera rotation are allowed.

## BACKGROUND & ENVIRONMENT
- Pure neutral gray or white background
- Seamless, studio-style environment
- No visible floor, horizon, ground texture, or stage
- No turntable, pedestal, or platform
- Subject appears naturally grounded

## CONFIGURATION
Resolution: 4K
Aspect Ratio: 3:2
Sampling: deterministic (low randomness)

## FINAL HARD RULES
- EXACTLY 4 panels — no more, no less
- Identical scale and framing across panels
- No duplicated or mirrored views
- No creative interpretation
- Treat the subject as a scanned physical object

Failure to follow these rules is unacceptable."""

_LEGACY_STRICT_COPY_TEMPLATE = """Create a STRICT 4-panel CHARACTER TURNTABLE showing THIS PERSON from the reference image.

This is a GEOMETRIC CAMERA ORBIT TASK, not a character redesign task.

The subject is a STATIC OBJECT in 3D space.
Only the CAMERA position changes.
NO pose correction, NO aesthetic adjustment, NO reinterpretation.

## OUTPUT LAYOUT (MANDATORY)
Single image with exactly 4 equal-sized panels in ONE horizontal row.
Order: [FRONT 0°] [RIGHT 90°] [BACK 180°] [LEFT 270°]

## CAMERA DEFINITION (CRITICAL)
- Camera rotates around the subject at a fixed radius and height
- Camera target is the subject's original center
- The subject does NOT rotate

## THE 4 REQUIRED VIEWS

Panel 1 — FRONT (0°):
- Camera faces the FRONT of the subject
- Subject front is fully visible
- Match the reference image orientation exactly

Panel 2 — RIGHT (90°):
- Camera is on the SUBJECT'S RIGHT side
- SUBJECT'S RIGHT SIDE faces the camera
- Subject's FRONT points LEFT

Panel 3 — BACK (180°):
- Camera faces the BACK of the subject
- Subject back is fully visible
- NO face visible in this panel

Panel 4 — LEFT (270°):
- Camera is on the SUBJECT'S LEFT side
- SUBJECT'S LEFT SIDE faces the camera
- Subject's FRONT points RIGHT

## 🔒 ABSOLUTE SPATIAL LOCK — ZERO DEVIATION ALLOWED

The subject is FROZEN in world space.

The following MUST remain 100% IDENTICAL across ALL panels:
- Head tilt and rotation
- Eye direction (NO "fixing" eye contact)
- Facial expression
- Shoulder angle
- Arm position and hand orientation
- Leg stance and weight distribution
- Torso angle and center of mass
- Clothing details and folds
- All accessories and props

❌ DO NOT adjust pose for visibility
❌ DO NOT rotate body to face camera
❌ DO NOT mirror anatomy
❌ DO NOT "fix" anatomy per view

## BACKGROUND & ENVIRONMENT
- Pure neutral gray or white background
- Seamless, studio-style environment
- No visible floor, horizon, ground texture, or stage
- No turntable, pedestal, or platform
- Subject appears naturally grounded

## CONFIGURATION
Resolution: 4K
Aspect Ratio: 3:2
Sampling: deterministic (low randomness)

## FINAL HARD RULES
- EXACTLY 4 panels — no more, no less
- Identical scale and framing across panels
- No duplicated or mirrored views
- No creative interpretation
- Treat the subject as a scanned physical object

Failure to follow these rules is unacceptable."""

_LEGACY_NEGATIVE_PROMPT = "extra limbs, missing limbs, extra fingers, deformed hands, twisted body, low quality, blurry, watermark, text, duplicate panels"
