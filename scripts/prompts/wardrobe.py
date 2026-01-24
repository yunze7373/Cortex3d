#!/usr/bin/env python3
"""
Cortex3d 换装系统 v3.0 (Wardrobe System)
基于 PromptLibrary + YAML 模板系统，与多视图生成共享风格预设

设计原则:
- 使用与 --anime, --real, --paper 相同的 PromptLibrary 系统
- 共享风格预设（支持 --wear dress.png --anime 组合）
- YAML 模板驱动，易于维护和扩展
- 保持向后兼容的 API

模板位置:
    prompts/composite/clothing.yaml
    prompts/composite/accessory.yaml
    prompts/composite/full_outfit.yaml
    prompts/composite/general.yaml

用法示例:
    # 简单换装（默认 photorealistic）
    python generate_character.py --from-image model.png --wear dress.png --custom-views front
    
    # 换装 + 动漫风格
    python generate_character.py --from-image model.png --wear dress.png --anime --custom-views front
    
    # 换装 + 写实风格
    python generate_character.py --from-image model.png --wear dress.png --real --custom-views front
    
    # 带自定义指令
    python generate_character.py --from-image model.png --wear "red_dress.png" --wear-instruction "换上这件优雅的红裙"
    
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
    style: str = None  # 风格（anime, photorealistic 等）
    strict_mode: bool = True  # 严格保真模式


# =============================================================================
# 核心函数 - 使用 PromptLibrary 系统
# =============================================================================

def build_wardrobe_prompt(
    task_type: str,
    instruction: str = None,
    num_images: int = 2,
    strict_mode: bool = True,
    style: str = None
) -> str:
    """
    构建换装提示词
    
    使用 PromptLibrary 系统，与多视角生成共享风格预设。
    
    Args:
        task_type: 任务类型 ("clothing", "accessory", "full_outfit", "auto")
        instruction: 用户指令
        num_images: 图片数量
        strict_mode: 是否启用严格保真模式（目前始终启用）
        style: 风格（anime, photorealistic, paper 等）
    
    Returns:
        完整的换装提示词
    """
    # 使用 PromptLibrary 系统
    from prompts import prompt_library
    
    # 自动检测任务类型
    if task_type == "auto" and instruction:
        task_type = detect_wardrobe_task(instruction)
    
    # 默认指令
    if not instruction:
        if task_type == "clothing":
            instruction = "将图2中的服装穿到图1的人物身上"
        elif task_type == "accessory":
            instruction = "将图2中的配饰添加到图1的人物身上"
        elif task_type == "full_outfit":
            instruction = "将图2的完整造型应用到图1的人物身上"
        else:
            instruction = "按照用户意图合成图片"
    
    # 调用 PromptLibrary 构建提示词
    return prompt_library.build_composite_prompt(
        instruction=instruction,
        composite_type=task_type,
        style=style,
        num_images=num_images
    )


def detect_wardrobe_task(instruction: str) -> str:
    """
    根据用户指令自动检测换装任务类型
    
    Args:
        instruction: 用户指令
    
    Returns:
        任务类型 ("clothing", "accessory", "full_outfit", "general")
    """
    # 使用 PromptLibrary 的检测逻辑
    from prompts import prompt_library
    return prompt_library._detect_composite_type(instruction)


def get_wardrobe_help() -> str:
    """获取换装功能帮助信息"""
    return """
╔══════════════════════════════════════════════════════════════════════╗
║                    👗 WARDROBE SYSTEM v3.0 (换装系统)                 ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  🎨 风格支持 (与 --anime, --real 等共享同一系统):                    ║
║  ────────────────────────────────────────────────────────────────    ║
║  --wear dress.png                      默认写实风格                  ║
║  --wear dress.png --anime              动漫风格换装                  ║
║  --wear dress.png --real               超写实风格换装                ║
║  --wear dress.png --paper              纸艺风格换装                  ║
║  --wear dress.png --chibi              Q版风格换装                   ║
║                                                                      ║
║  📝 基本用法:                                                        ║
║  ────────────────────────────────────────────────────────────────    ║
║  --wear dress.png              给主体换上指定服装                    ║
║  --accessory hat.png bag.png   给主体添加配饰                        ║
║                                                                      ║
║  🔧 完整用法:                                                        ║
║  ────────────────────────────────────────────────────────────────    ║
║  --wear dress.png --wear-instruction "换上这件红裙"                  ║
║  --wear dress.png --wear-model pro     使用高保真模型                ║
║  --wear dress.png --custom-views front back  (换装后生成多视图)      ║
║                                                                      ║
║  💡 示例命令:                                                        ║
║  ────────────────────────────────────────────────────────────────    ║
║  # 简单换装 + 单视图                                                 ║
║  python generate_character.py \\                                     ║
║      --from-image model.png --wear dress.png --custom-views front    ║
║                                                                      ║
║  # 动漫风格换装                                                      ║
║  python generate_character.py \\                                     ║
║      --from-image model.png --wear dress.png --anime                 ║
║                                                                      ║
║  # 换装 + 4视图                                                      ║
║  python generate_character.py \\                                     ║
║      --from-image model.png --wear dress.png --views 4               ║
║                                                                      ║
║  # 添加配饰                                                          ║
║  python generate_character.py \\                                     ║
║      --from-image model.png --accessory hat.png --custom-views front ║
║                                                                      ║
║  ✅ 特性:                                                            ║
║  ────────────────────────────────────────────────────────────────    ║
║  ✅ 100% 保留面部特征、表情、发型                                    ║
║  ✅ 100% 保留身材比例、姿势、手势                                    ║
║  ✅ 使用 PromptLibrary + YAML 模板系统                               ║
║  ✅ 共享 --anime, --real, --paper 等风格预设                         ║
║  ✅ 可与 --custom-views 等参数链式使用                               ║
║                                                                      ║
║  📁 模板位置: prompts/composite/*.yaml                               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""


# =============================================================================
# 向后兼容的模板常量（已废弃，保留以兼容旧代码）
# 新代码请使用 build_wardrobe_prompt() 函数
# =============================================================================

# 这些常量现在从 YAML 模板动态加载，但保留接口以兼容旧代码
def _get_legacy_template(template_name: str) -> str:
    """获取旧版模板（用于向后兼容）"""
    try:
        from prompts import prompt_library
        template_data = prompt_library.load_prompt("composite", template_name)
        return template_data.get("template", "")
    except Exception:
        return f"Template '{template_name}' not found"


# 向后兼容的模板常量（动态代理）
class _LegacyTemplateProxy:
    """旧版模板代理，用于向后兼容"""
    def __init__(self, template_name: str):
        self._template_name = template_name
        self._cached = None
    
    def __str__(self):
        if self._cached is None:
            self._cached = _get_legacy_template(self._template_name)
        return self._cached
    
    def format(self, **kwargs):
        return str(self).format(**kwargs)


WARDROBE_CLOTHING_TEMPLATE = _LegacyTemplateProxy("clothing")
WARDROBE_ACCESSORY_TEMPLATE = _LegacyTemplateProxy("accessory")
WARDROBE_FULL_OUTFIT_TEMPLATE = _LegacyTemplateProxy("full_outfit")


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    'WardrobeTask',
    'build_wardrobe_prompt',
    'detect_wardrobe_task',
    'get_wardrobe_help',
    # 向后兼容
    'WARDROBE_CLOTHING_TEMPLATE',
    'WARDROBE_ACCESSORY_TEMPLATE', 
    'WARDROBE_FULL_OUTFIT_TEMPLATE',
]
