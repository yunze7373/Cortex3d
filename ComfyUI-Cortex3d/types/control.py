"""CortexControl — Hunyuan3D-Omni 控制数据类型"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VALID_CONTROL_TYPES = ("none", "pose", "point", "voxel", "bbox")


@dataclass
class CortexControl:
    """Hunyuan3D-Omni 的控制数据，在节点间传递。

    Attributes:
        control_type: "none" | "pose" | "point" | "voxel" | "bbox"
        data_path:    控制数据文件路径（JSON / PLY / NPY）。
                      control_type="none" 时可为 None。
    """

    control_type: str = "none"
    data_path: Optional[str] = None

    def __post_init__(self):
        if self.control_type not in VALID_CONTROL_TYPES:
            raise ValueError(
                f"无效的 control_type={self.control_type!r}，"
                f"有效值: {VALID_CONTROL_TYPES}"
            )
        if self.control_type != "none" and self.data_path is None:
            raise ValueError(
                f"control_type={self.control_type!r} 需要提供 data_path"
            )

    @property
    def path(self) -> Optional[Path]:
        return Path(self.data_path) if self.data_path else None

    @property
    def exists(self) -> bool:
        return self.path.exists() if self.path else False

    def to_cli_args(self) -> list:
        """转换为 run_hunyuan3d_omni.py 的 CLI 参数列表。"""
        if self.control_type == "none":
            return []
        return ["--control-type", self.control_type,
                "--control-input", str(self.data_path)]

    def __repr__(self) -> str:
        return f"CortexControl(type={self.control_type!r}, path={self.data_path!r})"
