"""
Cortex3d 视角配置模块
定义所有支持的视角及其属性
"""

from typing import List, Dict, Tuple, Union
from dataclasses import dataclass


@dataclass
class ViewConfig:
    """视角配置"""
    name: str           # 视角名称 (front, right, etc.)
    angle: Union[int, str]    # 角度 (0, 45, 90, etc.) 或特殊值 (top, bottom)
    display_name: str   # 显示名称
    description: str    # 面板描述 (用于提示词)


# 所有支持的视角定义 (通用描述，适用于人物/动物/物体)
ALL_VIEWS: Dict[str, ViewConfig] = {
    "front": ViewConfig(
        name="front", 
        angle=0, 
        display_name="FRONT",
        description="Camera at 0° - Camera faces the FRONT of the object. The object's front side is fully visible, facing the camera"
    ),
    "front_right": ViewConfig(
        name="front_right", 
        angle=45, 
        display_name="FRONT-RIGHT",
        description="Camera at 45° - Camera is positioned front-right of the object. We see both the front AND the right side. The object's front points toward the LEFT side of the image"
    ),
    "right": ViewConfig(
        name="right", 
        angle=90, 
        display_name="RIGHT",
        description="Camera at 90° - Camera is on the RIGHT side of the object. The object's RIGHT side faces the camera. The object's FRONT points toward the LEFT edge of the image"
    ),
    "back_right": ViewConfig(
        name="back_right", 
        angle=135, 
        display_name="BACK-RIGHT",
        description="Camera at 135° - Camera is positioned back-right of the object. We see both the back AND the right side"
    ),
    "back": ViewConfig(
        name="back", 
        angle=180, 
        display_name="BACK",
        description="Camera at 180° - Camera faces the BACK of the object. The object's back side is fully visible. The front is hidden"
    ),
    "back_left": ViewConfig(
        name="back_left", 
        angle=225, 
        display_name="BACK-LEFT",
        description="Camera at 225° - Camera is positioned back-left of the object. We see both the back AND the left side"
    ),
    "left": ViewConfig(
        name="left", 
        angle=270, 
        display_name="LEFT",
        description="Camera at 270° - Camera is on the LEFT side of the object. The object's LEFT side faces the camera. The object's FRONT points toward the RIGHT edge of the image"
    ),
    "front_left": ViewConfig(
        name="front_left", 
        angle=315, 
        display_name="FRONT-LEFT",
        description="Camera at 315° - Camera is positioned front-left of the object. We see both the front AND the left side. The object's front points toward the RIGHT side of the image"
    ),
    "top": ViewConfig(
        name="top", 
        angle="top", 
        display_name="TOP",
        description="Camera directly above - Bird's eye view looking straight down at the top of the object"
    ),
    "bottom": ViewConfig(
        name="bottom", 
        angle="bottom", 
        display_name="BOTTOM",
        description="Camera directly below - Looking straight up at the bottom of the object"
    ),
}


# 预设视角组合 (顺序经过优化，适合网格布局)
VIEW_PRESETS: Dict[str, List[str]] = {
    # 4视角: 1x4 横排 [FRONT] [RIGHT] [BACK] [LEFT]
    "4-view": ["front", "right", "back", "left"],
    
    # 6视角: 2x3 网格
    # 第一行: [FRONT] [FRONT-RIGHT] [RIGHT]
    # 第二行: [BACK]  [FRONT-LEFT]  [LEFT]
    "6-view": ["front", "front_right", "right", "back", "front_left", "left"],
    
    # 8视角: 2x4 网格 (6个水平视角 + 顶部 + 底部)
    # 第一行: [FRONT] [FRONT-RIGHT] [RIGHT] [BACK]
    # 第二行: [LEFT]  [FRONT-LEFT]  [TOP]   [BOTTOM]
    "8-view": ["front", "front_right", "right", "back", "left", "front_left", "top", "bottom"],
}


def get_views_for_mode(mode: str) -> List[ViewConfig]:
    """
    获取指定模式的视角列表
    
    Args:
        mode: 视角模式 (4-view, 6-view, 8-view)
    
    Returns:
        ViewConfig 列表
    """
    if mode in VIEW_PRESETS:
        return [ALL_VIEWS[name] for name in VIEW_PRESETS[mode]]
    return [ALL_VIEWS[name] for name in VIEW_PRESETS["4-view"]]


def get_views_by_names(names: List[str]) -> List[ViewConfig]:
    """
    根据名称列表获取视角配置
    
    Args:
        names: 视角名称列表 (如 ["front", "right", "back"])
    
    Returns:
        ViewConfig 列表
    """
    return [ALL_VIEWS[name] for name in names if name in ALL_VIEWS]


def get_layout_for_views(view_count: int) -> Tuple[int, int, str]:
    """
    根据视角数量确定最佳布局
    
    Args:
        view_count: 视角数量
    
    Returns:
        (rows, cols, aspect_ratio) 元组
        
    Note:
        宽高比必须是 Gemini API 支持的比例：
        '1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'
    """
    layouts = {
        1: (1, 1, "1:1"),      # 单个视角
        2: (1, 2, "3:2"),      # 修复: 2:1 → 3:2 (支持的比例)
        3: (1, 3, "21:9"),     # 修复: 3:1 → 21:9 (支持的比例，21:9 ≈ 2.33:1，接近3:1)
        4: (1, 4, "3:2"),      # 1x4 横排，保持 3:2
        5: (2, 3, "3:2"),      # 修复: 1x5 → 2x3 布局，使用 3:2
        6: (2, 3, "3:2"),      # 2x3 网格
        7: (2, 4, "3:2"),      # 2x4 网格 (多一个空位)
        8: (2, 4, "3:2"),      # 2x4 网格
    }
    return layouts.get(view_count, (2, 4, "3:2"))


def get_view_names_for_layout(rows: int, cols: int, views: List[ViewConfig]) -> List[str]:
    """
    根据布局获取视角名称列表
    
    Args:
        rows: 行数
        cols: 列数
        views: 视角配置列表
    
    Returns:
        视角名称列表
    """
    return [v.name for v in views]


def format_panel_list(views: List[ViewConfig]) -> str:
    """
    格式化面板列表（用于提示词）
    
    Args:
        views: 视角配置列表
    
    Returns:
        格式化的面板列表字符串
    """
    parts = []
    for v in views:
        if isinstance(v.angle, int):
            parts.append(f"[{v.display_name} {v.angle}°]")
        else:
            parts.append(f"[{v.display_name}]")
    return " ".join(parts)


def format_view_descriptions(views: List[ViewConfig]) -> str:
    """
    格式化视角描述（用于提示词）
    
    Args:
        views: 视角配置列表
    
    Returns:
        格式化的视角描述字符串
    """
    lines = []
    for i, v in enumerate(views):
        lines.append(f"  - Panel {i+1} ({v.display_name}): {v.description}")
    return "\n".join(lines)


def format_grid_layout(views: List[ViewConfig], rows: int, cols: int) -> str:
    """
    生成清晰的网格布局图
    
    Args:
        views: 视角配置列表
        rows: 行数
        cols: 列数
    
    Returns:
        ASCII 网格布局图字符串
    """
    if len(views) == 1:
        return f"Single panel: [{views[0].display_name}]"
    
    # 构建网格
    grid_lines = []
    idx = 0
    
    for row in range(rows):
        row_parts = []
        for col in range(cols):
            if idx < len(views):
                v = views[idx]
                if isinstance(v.angle, int):
                    row_parts.append(f"[{v.display_name} {v.angle}°]")
                else:
                    row_parts.append(f"[{v.display_name}]")
                idx += 1
            else:
                row_parts.append("[---]")
        
        row_str = " ".join(row_parts)
        grid_lines.append(f"  Row {row + 1}: {row_str}")
    
    return "\n".join(grid_lines)


def get_all_view_names() -> List[str]:
    """获取所有可用的视角名称"""
    return list(ALL_VIEWS.keys())


def validate_view_names(names: List[str]) -> Tuple[List[str], List[str]]:
    """
    验证视角名称列表
    
    Args:
        names: 要验证的视角名称列表
    
    Returns:
        (valid_names, invalid_names) 元组
    """
    valid = [n for n in names if n in ALL_VIEWS]
    invalid = [n for n in names if n not in ALL_VIEWS]
    return valid, invalid


def infer_reference_system(view_names: List[str]) -> Tuple[str, List[ViewConfig]]:
    """
    根据自定义视角名称推断所属的参考视角系统
    
    逻辑：
    - 如果包含 front_right, front_left, back_right, back_left, top, bottom 等
      → 使用 8-view 系统
    - 如果包含 front_right, front_left 等（无 top/bottom）
      → 使用 6-view 系统
    - 如果只包含 front, right, back, left
      → 使用 4-view 系统
    
    Args:
        view_names: 自定义视角名称列表
    
    Returns:
        (系统名称, 完整系统的 ViewConfig 列表)
    """
    # 检查是否有8视角独有的视角（top, bottom, back_right, back_left）
    eight_view_only = {"top", "bottom", "back_right", "back_left"}
    # 检查是否有6视角及以上的视角（front_right, front_left）
    six_view_and_above = {"front_right", "front_left", "back_right", "back_left", "top", "bottom"}
    
    view_set = set(view_names)
    
    if view_set & eight_view_only:
        # 包含8视角独有的视角
        return "8-view", get_views_for_mode("8-view")
    elif view_set & {"front_right", "front_left"}:
        # 包含6视角的斜向视角
        return "6-view", get_views_for_mode("6-view")
    else:
        # 默认使用4视角系统
        return "4-view", get_views_for_mode("4-view")


def format_reference_system_context(reference_system: str, all_views: List[ViewConfig], target_views: List[ViewConfig]) -> str:
    """
    格式化参考系统上下文说明
    
    用于在提示词中说明：这是X视角系统中的Y视角
    
    Args:
        reference_system: 参考系统名称 (4-view, 6-view, 8-view)
        all_views: 完整系统的所有视角
        target_views: 要生成的目标视角
    
    Returns:
        上下文说明字符串
    """
    # 格式化完整系统的视角列表
    all_view_names = [f"{v.display_name} ({v.angle}°)" if isinstance(v.angle, int) else f"{v.display_name}" for v in all_views]
    all_views_str = ", ".join(all_view_names)
    
    # 格式化目标视角
    target_names = [v.display_name for v in target_views]
    target_str = ", ".join(target_names)
    
    # 确定网格布局
    view_count = len(target_views)
    if view_count <= 4:
        rows, cols = 1, view_count
    elif view_count <= 6:
        rows, cols = 2, 3
    else:  # 8 views
        rows, cols = 2, 4
    
    # 生成网格布局图
    grid_layout = format_grid_layout(target_views, rows, cols)
    
    # 构建上下文说明 (通用描述，适用于任何对象)
    context = f"""## CAMERA ANGLE REFERENCE SYSTEM
⚠️ This uses a {reference_system} camera angle system:
{all_views_str}

## TARGET VIEW(S) TO GENERATE
From the {reference_system} system above, generate ONLY: {target_str}

## 📐 EXACT GRID LAYOUT (from left to right, top to bottom)
{grid_layout}

⚠️ IMPORTANT: Each cell position is FIXED. Follow this exact order!

## ⚠️ CRITICAL: UNDERSTANDING LEFT vs RIGHT VIEWS

Think of the object standing in the center. The camera orbits around it in a CLOCKWISE direction:

**FRONT (0°) → FRONT-RIGHT (45°) → RIGHT (90°) → BACK-RIGHT (135°) → BACK (180°) → BACK-LEFT (225°) → LEFT (270°) → FRONT-LEFT (315°)**

**RIGHT view (90°):**
- Camera is positioned on the object's RIGHT side
- We see the object's RIGHT surface
- The object's FRONT points toward the LEFT edge of the image
- Think: "I'm standing to the RIGHT of the object, looking at it"

**LEFT view (270°):**
- Camera is positioned on the object's LEFT side
- We see the object's LEFT surface
- The object's FRONT points toward the RIGHT edge of the image
- Think: "I'm standing to the LEFT of the object, looking at it"

⚠️ KEY DIFFERENCE: 
- In RIGHT view: object's front → points LEFT in image
- In LEFT view: object's front → points RIGHT in image
- These are OPPOSITE views, NOT mirrors!"""

    return context

