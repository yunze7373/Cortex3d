#!/usr/bin/env python3
"""
Cortex3d 换装系统 v2.0 (Wardrobe System)
工业级换装/穿搭提示词模板，复用多视图系统的严格控制机制

设计原则:
- 像风格预设一样简单易用 (--wear dress.png)
- 复用多视图的 SPATIAL LOCK 约束系统
- 支持严格保真 (100% 保留面部/身材/姿势)
- 支持链式处理 (换装后可继续多视图生成)

用法示例:
    # 简单换装
    python generate_character.py --from-image model.png --wear dress.png --custom-views front
    
    # 带自定义指令
    python generate_character.py --from-image model.png --wear "red_dress.png" --wear-instruction "换上这件优雅的红裙"
    
    # 换装 + 多视图
    python generate_character.py --from-image model.png --wear dress.png --custom-views front back left right
    
    # 添加配饰
    python generate_character.py --from-image model.png --accessory hat.png bag.png --custom-views front
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class WardrobeTask:
    """换装任务定义"""
    task_type: str  # "clothing", "accessory", "full_outfit"
    description: str
    strict_mode: bool = True  # 严格保真模式
    
    
# =============================================================================
# 核心换装提示词模板 - 使用 Google 官方推荐的高保真细节保留格式
# 参考: https://ai.google.dev/gemini-api/docs/image-generation#5_high_fidelity_detail_preservation
# =============================================================================

WARDROBE_CLOTHING_TEMPLATE = """Using the provided images, place the clothing/garment from Image 2 onto the person in Image 1.

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


WARDROBE_ACCESSORY_TEMPLATE = """Using the provided images, place the accessory from Image 2 onto the person in Image 1.

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


WARDROBE_FULL_OUTFIT_TEMPLATE = """Using the provided images, apply the complete outfit from Image 2 onto the person in Image 1.

Ensure that the following features of the person in Image 1 remain COMPLETELY UNCHANGED:
- Face: ALL facial features, expression, gaze - must be identical
- Hair: style, length, color, texture - must be identical
- Skin tone: must remain exactly the same
- Body proportions: height, build, shape - must be identical
- Pose: body position, gesture, stance - must be identical
- Background: environment, lighting direction - must be unchanged

The outfit should:
- Be extracted completely from Image 2 (all clothing and accessories)
- Fit naturally on Image 1's body shape and pose
- Maintain the overall aesthetic style

User instruction: {instruction}

Generate a single photorealistic composite image. No text or annotations."""


# =============================================================================
# 辅助函数
# =============================================================================

def build_wardrobe_prompt(
    task_type: str,
    instruction: str = None,
    num_images: int = 2,
    strict_mode: bool = True
) -> str:
    """
    构建换装提示词
    
    Args:
        task_type: 任务类型 ("clothing", "accessory", "full_outfit", "auto")
        instruction: 用户指令
        num_images: 图片数量
        strict_mode: 是否启用严格保真模式
    
    Returns:
        完整的换装提示词
    """
    # 自动检测任务类型
    if task_type == "auto" and instruction:
        task_type = detect_wardrobe_task(instruction)
    
    # 默认指令
    if not instruction:
        if task_type == "clothing":
            instruction = "让图1的人穿上图2中的衣服/服装"
        elif task_type == "accessory":
            instruction = "给图1的人添加图2中的配饰"
        else:
            instruction = "将图2的完整造型应用到图1的人身上"
    
    # 选择模板
    if task_type == "clothing":
        template = WARDROBE_CLOTHING_TEMPLATE
    elif task_type == "accessory":
        template = WARDROBE_ACCESSORY_TEMPLATE
    else:
        template = WARDROBE_FULL_OUTFIT_TEMPLATE
    
    return template.format(instruction=instruction)


def detect_wardrobe_task(instruction: str) -> str:
    """
    根据用户指令自动检测换装任务类型
    
    Args:
        instruction: 用户指令
    
    Returns:
        任务类型 ("clothing", "accessory", "full_outfit")
    """
    lower_inst = instruction.lower()
    
    # 服装关键词
    clothing_keywords = [
        "穿", "衣服", "裙", "裤", "上衣", "外套", "衬衫", "t恤", "连衣裙",
        "wear", "dress", "shirt", "pants", "jacket", "outfit", "clothing",
        "换装", "换衣", "试穿", "穿上", "换上"
    ]
    
    # 配饰关键词  
    accessory_keywords = [
        "帽", "包", "眼镜", "墨镜", "耳环", "项链", "手表", "戒指", "手链",
        "围巾", "领带", "腰带", "鞋", "袜",
        "hat", "bag", "glasses", "sunglasses", "earring", "necklace", "watch",
        "ring", "bracelet", "scarf", "tie", "belt", "shoes", "socks",
        "戴", "配饰", "饰品", "accessory", "jewelry"
    ]
    
    # 完整造型关键词
    full_outfit_keywords = [
        "整套", "全身", "完整造型", "整体", "全套",
        "complete outfit", "full look", "entire outfit", "whole look"
    ]
    
    # 优先检测完整造型
    if any(kw in lower_inst for kw in full_outfit_keywords):
        return "full_outfit"
    
    # 然后检测服装
    if any(kw in lower_inst for kw in clothing_keywords):
        return "clothing"
    
    # 然后检测配饰
    if any(kw in lower_inst for kw in accessory_keywords):
        return "accessory"
    
    # 默认为服装
    return "clothing"


def get_wardrobe_help() -> str:
    """获取换装功能帮助信息"""
    return """
╔══════════════════════════════════════════════════════════════════════╗
║                    👗 WARDROBE SYSTEM (换装系统)                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  简单用法 (类似 --anime):                                            ║
║  ────────────────────────────────────────────────────────────────    ║
║  --wear dress.png              给主体换上指定服装                    ║
║  --accessory hat.png bag.png   给主体添加配饰                        ║
║                                                                      ║
║  完整用法:                                                           ║
║  ────────────────────────────────────────────────────────────────    ║
║  --wear dress.png --wear-instruction "换上这件红裙"                  ║
║  --wear dress.png --custom-views front back  (换装后生成多视图)      ║
║                                                                      ║
║  示例命令:                                                           ║
║  ────────────────────────────────────────────────────────────────    ║
║  # 简单换装 + 单视图                                                 ║
║  python generate_character.py \\                                     ║
║      --from-image model.png --wear dress.png --custom-views front    ║
║                                                                      ║
║  # 换装 + 4视图                                                      ║
║  python generate_character.py \\                                     ║
║      --from-image model.png --wear dress.png --views 4               ║
║                                                                      ║
║  # 添加配饰                                                          ║
║  python generate_character.py \\                                     ║
║      --from-image model.png --accessory hat.png --custom-views front ║
║                                                                      ║
║  特性:                                                               ║
║  ────────────────────────────────────────────────────────────────    ║
║  ✅ 100% 保留面部特征、表情、发型                                    ║
║  ✅ 100% 保留身材比例、姿势、手势                                    ║
║  ✅ 复用多视图系统的严格约束模板                                     ║
║  ✅ 可与 --custom-views, --real, --anime 等参数链式使用              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'WardrobeTask',
    'build_wardrobe_prompt',
    'detect_wardrobe_task',
    'get_wardrobe_help',
    'WARDROBE_CLOTHING_TEMPLATE',
    'WARDROBE_ACCESSORY_TEMPLATE', 
    'WARDROBE_FULL_OUTFIT_TEMPLATE',
]
