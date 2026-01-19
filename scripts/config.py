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
# 四视角角色参考表提示词模板 (优化版 v2)
# 针对常见问题优化：解剖学错误、左右混淆、动作不一致
# =============================================================================

MULTI_VIEW_PROMPT_TEMPLATE = """Generate a professional 3D character turntable reference sheet with exactly 4 panels arranged horizontally.

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
- RIGHT SIDE shows: right ear, right arm, right leg
- LEFT SIDE shows: left ear, left arm, left leg

### ANATOMICAL CORRECTNESS (CRITICAL!)
- Arms MUST connect to shoulders only
- Legs MUST connect to hips only
- Head MUST connect to neck only
- NO extra limbs, NO twisted body parts
- Upper body and lower body MUST face the SAME direction in each panel
- The entire body rotates together as one unit

### POSE CONSISTENCY (CRITICAL!)
- EXACT same pose in ALL 4 panels - only the viewing angle changes
- Same arm positions, same leg positions, same head tilt
- If holding an object in right hand → it stays in right hand in ALL views
- This is ONE character photographed from 4 angles, NOT 4 different poses

### PANEL LAYOUT
- 4 equal-width panels arranged horizontally (side by side)
- Character centered in each panel
- Same scale/size in all panels
- Clean separation between panels
- Neutral gray or white background

### LIGHTING
- Flat, even studio lighting (no harsh shadows)
- Face clearly visible without shadow obstruction
- Consistent lighting direction across all panels

### ABSOLUTELY FORBIDDEN
- NO text labels (no "front", "back", "left", "right")
- NO twisted bodies (upper body facing different direction than legs)
- NO mirror flips (left and right views must show different sides)
- NO anatomical errors (no extra limbs, no wrong joint positions)
- NO pose variations between panels

Generate a clean, professional character reference sheet following ALL rules above.
"""


# =============================================================================
# 图片参考模式专用提示词模板 (保留原图动作)
# 用于从参考照片生成多视角图时使用
# =============================================================================

IMAGE_REFERENCE_PROMPT_TEMPLATE = """Generate a 3D character turntable reference sheet with exactly 4 panels, showing the character described below from 4 angles.

## OUTPUT
Single image with 4 panels horizontally: [FRONT] [RIGHT] [BACK] [LEFT]

## CHARACTER DESCRIPTION (from reference photo)
{character_description}

## CRITICAL: PRESERVE THE ORIGINAL POSE
⚠️ The character has a SPECIFIC pose from the reference photo. You MUST preserve this pose:
- If the character is WALKING → show walking pose from all 4 angles
- If the character is SITTING → show sitting pose from all 4 angles  
- If one leg is forward → keep that leg forward in all views
- If arms are in a specific position → maintain that position

DO NOT change the pose to a generic standing pose!

## TURNTABLE ROTATION
The 4 panels show the SAME character in the SAME pose, just rotated:
- Panel 1 (FRONT): 0° - facing camera
- Panel 2 (RIGHT): 90° - right side visible
- Panel 3 (BACK): 180° - back visible
- Panel 4 (LEFT): 270° - left side visible

## ANATOMICAL RULES
- Arms connect to shoulders only
- Legs connect to hips only
- Upper and lower body face the SAME direction
- NO twisted bodies, NO extra limbs

## PANEL LAYOUT
- 4 equal panels side by side
- Same scale in all panels
- Neutral gray background
- NO text labels

## LIGHTING
- Flat, even studio lighting
- No harsh shadows
- Face clearly visible

Generate the character maintaining the EXACT pose described, viewed from 4 angles.
"""


def build_multiview_prompt(
    character_description: str,
    style: str = "cinematic character"
) -> str:
    """
    构建多视图角色生成提示词（文字生成模式）
    
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


def build_image_reference_prompt(character_description: str) -> str:
    """
    构建图片参考模式专用提示词（保留原图动作）
    
    Args:
        character_description: 从参考图片提取的角色描述
    
    Returns:
        完整的提示词字符串
    """
    return IMAGE_REFERENCE_PROMPT_TEMPLATE.format(
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
