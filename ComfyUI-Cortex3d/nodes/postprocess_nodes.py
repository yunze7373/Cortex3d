"""后处理类节点 (4) — UltraShape / 网格锐化 / Blender打印预处理 / 网格验证。"""
from __future__ import annotations
import os
from ..utils.errors import node_guard

CAT = "Cortex3d/PostProcess"


class Cortex3d_UltraShapeRefiner:
    """使用 UltraShape 对粗体重建结果进行高质量几何精修。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":  ("IMAGE",),
                "mesh":   ("CORTEX_MESH",),
                "preset": (["lowmem", "fast", "balanced", "high", "ultra"], {"default": "balanced"}),
            },
            "optional": {
                "low_vram": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "IMAGE")
    RETURN_NAMES  = ("mesh", "preview")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, image, mesh, preset="balanced", low_vram=False):
        from ..adapters.ultrashape_adapter import UltraShapeAdapter
        from ..bridge.file_bridge import FileBridge
        from .reconstruction_nodes import _make_preview
        import torch

        if mesh is None:
            return (None, torch.zeros(1, 512, 512, 3))
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        refined = UltraShapeAdapter.refine(
            image_path=img_path, mesh_path=mesh.file_path,
            preset=preset, low_vram=low_vram,
        )
        result = refined if refined else mesh
        return (result, _make_preview(result))


class Cortex3d_MeshSharpener:
    """网格边缘锐化 — 使用 trimesh 的 Laplacian 平滑/锐化。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh":           ("CORTEX_MESH",),
                "iterations":     ("INT",   {"default": 3,   "min": 1, "max": 20}),
                "lambda_factor":  ("FLOAT", {"default": -0.5, "min": -1.0, "max": 0.0, "step": 0.05}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH",)
    RETURN_NAMES  = ("mesh",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, mesh, iterations=3, lambda_factor=-0.5):
        if mesh is None:
            return (None,)
        try:
            import trimesh
            import trimesh.smoothing as sm
            tm = mesh.to_trimesh()
            if tm is None:
                return (mesh,)
            sm.filter_laplacian(tm, lamb=abs(lambda_factor), iterations=iterations)
            # 保存到临时目录
            from ..bridge.file_bridge import FileBridge
            import tempfile, os
            fb = FileBridge()
            out_dir = fb.make_output_dir("comfyui_sharpen")
            out_path = str(out_dir / "sharpened.obj")
            tm.export(out_path)
            from ..types.mesh import CortexMesh
            return (CortexMesh(file_path=out_path, format="obj", source_algo=mesh.source_algo),)
        except Exception as e:
            import logging; logging.getLogger(__name__).warning(f"MeshSharpener 失败: {e}")
            return (mesh,)


class Cortex3d_BlenderPrintPrep:
    """调用 Blender 预处理网格（体素重网格 + 修补 + 缩放 + 导出 STL）。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh":           ("CORTEX_MESH",),
                "profile":        (["fdm", "resin", "sla", "multi_material"], {"default": "fdm"}),
                "height_mm":      ("FLOAT", {"default": 100.0, "min": 10.0,  "max": 500.0, "step": 5.0}),
                "voxel_size_mm":  ("FLOAT", {"default": 0.5,   "min": 0.1,   "max": 2.0,   "step": 0.1}),
                "decimate_ratio": ("FLOAT", {"default": 0.5,   "min": 0.05,  "max": 1.0,   "step": 0.05}),
            },
            "optional": {
                "skip_remesh": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH",)
    RETURN_NAMES  = ("mesh",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, mesh, profile, height_mm, voxel_size_mm, decimate_ratio, skip_remesh=False):
        if mesh is None:
            return (None,)
        from ..adapters.blender_adapter import BlenderAdapter
        result = BlenderAdapter.prepare_for_print(
            mesh_path=mesh.file_path, profile=profile,
            height_mm=height_mm, voxel_size_mm=voxel_size_mm,
            decimate_ratio=decimate_ratio, skip_remesh=skip_remesh,
        )
        return (result if result else mesh,)


class Cortex3d_MeshValidator:
    """网格有效性验证：水密 / 法向 / 面积 / 顶点数统计，输出报告字符串。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh": ("CORTEX_MESH",),
            },
            "optional": {
                "fix_normals":   ("BOOLEAN", {"default": True}),
                "fill_holes":    ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "STRING", "BOOLEAN")
    RETURN_NAMES  = ("mesh", "report", "is_valid")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, mesh, fix_normals=True, fill_holes=False):
        if mesh is None:
            return (None, "mesh is None", False)
        try:
            mesh.populate_stats()
            tm = mesh.to_trimesh()
            issues = []
            if tm is not None:
                if fix_normals:
                    tm.fix_normals()
                if fill_holes:
                    tm.fill_holes()
                if not tm.is_watertight:
                    issues.append("NOT watertight")
                if tm.is_empty:
                    issues.append("EMPTY geometry")
            report_lines = [
                f"Algorithm  : {mesh.source_algo}",
                f"Format     : {mesh.format}",
                f"Vertices   : {mesh.vertices}",
                f"Faces      : {mesh.faces}",
                f"Watertight : {mesh.is_watertight}",
                f"Issues     : {', '.join(issues) if issues else 'none'}",
            ]
            is_valid = len(issues) == 0
            return (mesh, "\n".join(report_lines), is_valid)
        except Exception as e:
            return (mesh, f"Validation error: {e}", False)
