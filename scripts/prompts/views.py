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


# 所有支持的视角定义
ALL_VIEWS: Dict[str, ViewConfig] = {
    "front": ViewConfig(
        name="front", 
        angle=0, 
        display_name="FRONT",
        description="Platform at 0° - We see the FACE, chest, front of body"
    ),
    "front_right": ViewConfig(
        name="front_right", 
        angle=45, 
        display_name="FRONT-RIGHT",
        description="Platform at 45° - Front-3/4 view, facing LEFT, we see the right side of face and body"
    ),
    "right": ViewConfig(
        name="right", 
        angle=90, 
        display_name="RIGHT",
        description="Platform at 90° - Profile view facing LEFT, we see the RIGHT side of body, RIGHT ear, RIGHT arm"
    ),
    "back_right": ViewConfig(
        name="back_right", 
        angle=135, 
        display_name="BACK-RIGHT",
        description="Platform at 135° - Back-3/4 view, facing AWAY-LEFT, we see the back of right side"
    ),
    "back": ViewConfig(
        name="back", 
        angle=180, 
        display_name="BACK",
        description="Platform at 180° - Strictly from behind, we see back of HEAD, spine, buttocks"
    ),
    "back_left": ViewConfig(
        name="back_left", 
        angle=225, 
        display_name="BACK-LEFT",
        description="Platform at 225° - Back-3/4 view, facing AWAY-RIGHT, we see the back of left side"
    ),
    "left": ViewConfig(
        name="left", 
        angle=270, 
        display_name="LEFT",
        description="Platform at 270° - Profile view facing RIGHT, we see the LEFT side of body, LEFT ear, LEFT arm"
    ),
    "front_left": ViewConfig(
        name="front_left", 
        angle=315, 
        display_name="FRONT-LEFT",
        description="Platform at 315° - Front-3/4 view, facing RIGHT, we see the left side of face and body"
    ),
    "top": ViewConfig(
        name="top", 
        angle="top", 
        display_name="TOP",
        description="Bird's eye view from directly above - We see the TOP of head, shoulders, looking straight down"
    ),
    "bottom": ViewConfig(
        name="bottom", 
        angle="bottom", 
        display_name="BOTTOM",
        description="Worm's eye view from directly below - We see the soles of feet, looking straight up"
    ),
}


# 预设视角组合
VIEW_PRESETS: Dict[str, List[str]] = {
    "4-view": ["front", "right", "back", "left"],
    "6-view": ["front", "front_right", "right", "back", "left", "front_left"],
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
    """
    layouts = {
        1: (1, 1, "1:1"),
        2: (1, 2, "2:1"),
        3: (1, 3, "3:1"),
        4: (1, 4, "3:2"),      # 1x4 横排
        5: (1, 5, "5:2"),
        6: (2, 3, "3:2"),      # 2x3 网格
        7: (2, 4, "3:2"),
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
