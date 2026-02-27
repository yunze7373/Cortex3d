"""CortexMesh — 网格文件数据类型"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CortexMesh:
    """在 ComfyUI 节点间传递网格文件的统一数据类型。

    Attributes:
        file_path: 网格文件的绝对路径（OBJ / GLB / STL）。
        format:    文件格式，"obj" | "glb" | "stl"。
        vertices:  顶点数（0 = 未统计）。
        faces:     面数（0 = 未统计）。
        is_watertight: 是否水密（None = 未检验）。
        source_algo:   生成该网格的算法名称（如 "trellis2"）。
    """

    file_path: str
    format: str = "glb"
    vertices: int = 0
    faces: int = 0
    is_watertight: Optional[bool] = None
    source_algo: str = "unknown"

    # ── 便捷属性 ──────────────────────────────────────────────────

    @property
    def path(self) -> Path:
        return Path(self.file_path)

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @property
    def size_mb(self) -> float:
        if self.exists:
            return self.path.stat().st_size / 1024 / 1024
        return 0.0

    # ── 加载为 trimesh ────────────────────────────────────────────

    def to_trimesh(self):
        """加载为 trimesh.Trimesh 对象，用于分析/预览。"""
        try:
            import trimesh
            scene_or_mesh = trimesh.load(self.file_path, force="mesh")
            return scene_or_mesh
        except Exception as e:
            raise RuntimeError(f"无法加载网格 {self.file_path}: {e}") from e

    # ── 自动填充统计信息 ──────────────────────────────────────────

    def populate_stats(self) -> "CortexMesh":
        """读取实际网格统计信息，就地更新并返回 self。"""
        try:
            mesh = self.to_trimesh()
            self.vertices = len(mesh.vertices)
            self.faces = len(mesh.faces)
            self.is_watertight = mesh.is_watertight
        except Exception:
            pass
        return self

    # ── 序列化 ───────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "format": self.format,
            "vertices": self.vertices,
            "faces": self.faces,
            "is_watertight": self.is_watertight,
            "source_algo": self.source_algo,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CortexMesh":
        return cls(**d)

    def __repr__(self) -> str:
        return (
            f"CortexMesh(format={self.format}, "
            f"v={self.vertices}, f={self.faces}, "
            f"path={self.file_path!r})"
        )
