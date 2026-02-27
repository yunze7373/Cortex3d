"""CortexViewConfig — 多视角配置数据类型"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


VIEW_MODE_ALIASES = {
    "4":    "4-view",
    "6":    "6-view",
    "8":    "8-view",
    "4-view": "4-view",
    "6-view": "6-view",
    "8-view": "8-view",
    "custom": "custom",
}


@dataclass
class CortexViewConfig:
    """视角配置，封装 config.get_view_config() 的返回值。

    Attributes:
        view_mode: "4-view" | "6-view" | "8-view" | "custom"
        views:     视角名称列表，如 ["front", "back", "left", "right"]
        rows:      图像网格行数
        cols:      图像网格列数
        aspect_ratio: 拼图宽高比字符串，如 "2:2"
    """

    view_mode: str = "4-view"
    views: List[str] = field(default_factory=lambda: ["front", "back", "left", "right"])
    rows: int = 2
    cols: int = 2
    aspect_ratio: str = "1:1"

    # ── 工厂方法 ──────────────────────────────────────────────────

    @classmethod
    def from_config_result(cls, result: Tuple) -> "CortexViewConfig":
        """从 config.get_view_config() 的四元组返回值创建。"""
        views, rows, cols, aspect_ratio = result
        view_mode = f"{len(views)}-view" if len(views) in (4, 6, 8) else "custom"
        return cls(view_mode=view_mode, views=views,
                   rows=rows, cols=cols, aspect_ratio=aspect_ratio)

    @classmethod
    def default_4view(cls) -> "CortexViewConfig":
        return cls(
            view_mode="4-view",
            views=["front", "back", "left", "right"],
            rows=2, cols=2, aspect_ratio="1:1",
        )

    # ── 快捷属性 ──────────────────────────────────────────────────

    @property
    def num_views(self) -> int:
        return len(self.views)

    @property
    def normalized_mode(self) -> str:
        return VIEW_MODE_ALIASES.get(self.view_mode, self.view_mode)

    def __repr__(self) -> str:
        return f"CortexViewConfig({self.view_mode}, views={self.views})"
