#!/usr/bin/env python3
"""
Cortex3d 配置模块
统一管理提示词模板、模型名称和其他配置

所有生成脚本（aiproxy_client, gemini_generator）都从这里导入配置
"""

import os

try:
    from dotenv import load_dotenv
    # 加载 .env 文件 (从当前目录或父目录)
    load_dotenv()
except ImportError:
    pass # 如果没装 python-dotenv 就跳过

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
# 四视角角色参考表提示词模板
# 参考自: 2d图生成提示词/英文4视角提示词sample.md
# =============================================================================

MULTI_VIEW_PROMPT_TEMPLATE = """Create a {style} character design in 3D rendering style, showing front, back, left side, and right side views in a four-panel layout.

CHARACTER DESIGN: 4 views arranged horizontally side by side.

**CAMERA POSITIONS (CRITICAL - READ CAREFULLY):**
Think of a turntable with the character standing in the center:
- FRONT VIEW: Camera at 0° (directly facing the character's face)
- RIGHT SIDE VIEW: Camera at 90° (character has rotated, now showing their RIGHT side - right shoulder, right hip, right ear visible)
- BACK VIEW: Camera at 180° (showing the character's back, back of head)
- LEFT SIDE VIEW: Camera at 270° (character has rotated, now showing their LEFT side - left shoulder, left hip, left ear visible)

**IMPORTANT:** Left and Right profile views are NOT mirrors of each other. They show OPPOSITE sides of the body.

CHARACTER DESIGN:
{character_description}

SIDE VIEWS CLARIFICATION:
• In the LEFT SIDE VIEW: The character's LEFT arm, LEFT leg, LEFT ear are closest to the camera
• In the RIGHT SIDE VIEW: The character's RIGHT arm, RIGHT leg, RIGHT ear are closest to the camera
• The character should appear to have ROTATED, not been flipped/mirrored

POSE CONSISTENCY:
• Same relaxed standing pose in ALL 4 views
• Same arm positions, leg positions, and held items in all views
• If holding a weapon in right hand, it stays in right hand in ALL views

LAYOUT & COMPOSITION:
• Four-panel horizontal layout
• Character centered in each panel
• Clean separation between panels
• Neutral grey background in all panels

STYLE & AESTHETIC:
• 3D digital rendering with cinematic quality
• Photorealistic CGI, 8k textures
• Professional character reference sheet

ABSOLUTELY NO TEXT:
• NO labels, NO words, NO annotations
• NO "front" "back" "left" "right" text anywhere
• Completely clean image
"""


def build_multiview_prompt(
    character_description: str,
    style: str = "cinematic character"
) -> str:
    """
    构建多视图角色生成提示词
    
    Args:
        character_description: 角色描述（外貌、服装、配件等）
        style: 整体风格描述
    
    Returns:
        完整的提示词字符串
    """
    return MULTI_VIEW_PROMPT_TEMPLATE.format(
        style=style,
        character_description=character_description
    )


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

def get_character_prompt(preset_name: str = None, custom_description: str = None) -> str:
    """
    获取角色生成的完整提示词
    
    Args:
        preset_name: 预设角色名称 (zombie_santa, apocalypse_businessman)
        custom_description: 自定义角色描述
    
    Returns:
        完整的提示词
    """
    if preset_name and preset_name in PRESET_CHARACTERS:
        description = PRESET_CHARACTERS[preset_name]
    elif custom_description:
        description = custom_description
    else:
        description = PRESET_CHARACTERS["zombie_santa"]
    
    return build_multiview_prompt(description)
