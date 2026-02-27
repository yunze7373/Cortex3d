"""3D 重建类节点 (6) — InstantMesh / TripoSR / TRELLIS2 / Hunyuan3D / Hunyuan3DOmni / MultiviewReconstruction。"""
from __future__ import annotations
import os

CAT = "Cortex3d/3D"


def _make_preview(mesh) -> "torch.Tensor":
    """用 trimesh + pyrender/软光栅生成预览图，失败时返回灰色占位。"""
    import torch
    if mesh is None:
        return torch.zeros(1, 512, 512, 3)
    try:
        tm = mesh.to_trimesh()
        if tm is None:
            raise ValueError
        import numpy as np
        from PIL import Image as PILImage

        # 尝试用 pyrender 离屏渲染
        try:
            import pyrender
            scene = pyrender.Scene.from_trimesh_scene(tm) if hasattr(tm, "graph") else pyrender.Scene()
            if not hasattr(tm, "graph"):
                m = pyrender.Mesh.from_trimesh(tm)
                scene.add(m)
            camera = pyrender.PerspectiveCamera(yfov=0.8)
            bounds = tm.bounds
            center = (bounds[0] + bounds[1]) / 2
            extent = max(bounds[1] - bounds[0])
            cam_pose = np.eye(4)
            cam_pose[2, 3] = extent * 2
            cam_pose[:3, 3] += center
            scene.add(camera, pose=cam_pose)
            light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.0)
            scene.add(light, pose=cam_pose)
            r = pyrender.OffscreenRenderer(512, 512)
            color, _ = r.render(scene)
            r.delete()
            img = PILImage.fromarray(color)
        except Exception:
            # Fallback: trimesh内置渲染
            img = PILImage.fromarray(tm.export(file_type=None))

        arr = np.array(img.convert("RGB")).astype("float32") / 255.0
        return torch.from_numpy(arr).unsqueeze(0)
    except Exception:
        return torch.zeros(1, 512, 512, 3)


# ─────────────────────────────────────────────────────────────────────────────
# 1. InstantMesh
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_InstantMesh:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":            ("IMAGE",),
                "quality_preset":   (["fast", "balanced", "high", "ultra"], {"default": "balanced"}),
            },
            "optional": {
                "diffusion_steps":     ("INT",   {"default": 75, "min": 10, "max": 200}),
                "texture_resolution":  ("INT",   {"default": 1024, "min": 512, "max": 4096, "step": 512}),
                "seed":                ("INT",   {"default": 42}),
                "export_texture":      ("BOOLEAN", {"default": True}),
                "cortex_config":       ("CORTEX_CONFIG",),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "IMAGE")
    RETURN_NAMES  = ("mesh", "preview")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, image, quality_preset="balanced", diffusion_steps=75,
                texture_resolution=1024, seed=42, export_texture=True, cortex_config=None):
        from ..adapters.instantmesh_adapter import InstantMeshAdapter
        from ..bridge.file_bridge import FileBridge
        from ..types.config import QUALITY_PRESETS
        import torch

        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)

        # 从 CortexConfig 覆盖参数
        if cortex_config:
            presets = QUALITY_PRESETS.get("instantmesh", {}).get(quality_preset, {})
            diffusion_steps = cortex_config.params.get("diffusion_steps", presets.get("diffusion_steps", diffusion_steps))
            texture_resolution = cortex_config.params.get("texture_resolution", presets.get("texture_resolution", texture_resolution))

        mesh = InstantMeshAdapter.reconstruct(
            image_path=img_path, diffusion_steps=diffusion_steps,
            texture_resolution=texture_resolution, seed=seed, export_texture=export_texture,
        )
        preview = _make_preview(mesh)
        return (mesh, preview)


# ─────────────────────────────────────────────────────────────────────────────
# 2. TripoSR
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_TripoSR:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":          ("IMAGE",),
                "quality_preset": (["fast", "balanced", "high", "ultra"], {"default": "balanced"}),
            },
            "optional": {
                "mc_resolution":      ("INT", {"default": 256, "min": 64, "max": 512, "step": 32}),
                "texture_resolution": ("INT", {"default": 2048, "min": 512, "max": 4096, "step": 512}),
                "bake_texture":       ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "IMAGE")
    RETURN_NAMES  = ("mesh", "preview")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, image, quality_preset="balanced", mc_resolution=256,
                texture_resolution=2048, bake_texture=True):
        from ..adapters.triposr_adapter import TripoSRAdapter
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        mesh = TripoSRAdapter.reconstruct(
            image_path=img_path, mc_resolution=mc_resolution,
            bake_texture=bake_texture, texture_resolution=texture_resolution,
        )
        return (mesh, _make_preview(mesh))


# ─────────────────────────────────────────────────────────────────────────────
# 3. TRELLIS.2
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_TRELLIS2:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":          ("IMAGE",),
                "quality_preset": (["fast", "balanced", "high", "ultra"], {"default": "balanced"}),
            },
            "optional": {
                "model":        (["microsoft/TRELLIS.2-4B", "microsoft/TRELLIS.2-1B"], {"default": "microsoft/TRELLIS.2-4B"}),
                "ss_steps":     ("INT", {"default": 12, "min": 1, "max": 30}),
                "slat_steps":   ("INT", {"default": 12, "min": 1, "max": 30}),
                "seed":         ("INT", {"default": 42}),
                "decimation":   ("INT", {"default": 500000, "min": 10000, "max": 2000000, "step": 10000}),
                "texture_size": ("INT", {"default": 2048, "min": 512, "max": 4096, "step": 512}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "IMAGE")
    RETURN_NAMES  = ("mesh", "preview")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, image, quality_preset="balanced", model="microsoft/TRELLIS.2-4B",
                ss_steps=12, slat_steps=12, seed=42, decimation=500000, texture_size=2048):
        from ..adapters.trellis2_adapter import Trellis2Adapter
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        mesh = Trellis2Adapter.reconstruct(
            image_path=img_path, model=model, ss_steps=ss_steps,
            slat_steps=slat_steps, seed=seed, decimation=decimation, texture_size=texture_size,
        )
        return (mesh, _make_preview(mesh))


# ─────────────────────────────────────────────────────────────────────────────
# 4. Hunyuan3D (2.0 / 2.1)
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_Hunyuan3D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":   ("IMAGE",),
                "version": (["2.1", "2.0"], {"default": "2.1"}),
                "quality_preset": (["fast", "balanced", "high"], {"default": "balanced"}),
            },
            "optional": {
                "no_texture": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "IMAGE")
    RETURN_NAMES  = ("mesh", "preview")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, image, version="2.1", quality_preset="balanced", no_texture=False):
        from ..adapters.hunyuan3d_adapter import Hunyuan3DAdapter
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        if quality_preset == "fast":
            no_texture = True
        mesh = Hunyuan3DAdapter.reconstruct(
            image_path=img_path, version=version, no_texture=no_texture,
        )
        return (mesh, _make_preview(mesh))


# ─────────────────────────────────────────────────────────────────────────────
# 5. Hunyuan3D-Omni（条件控制重建）
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_Hunyuan3DOmni:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":   ("IMAGE",),
                "quality_preset": (["fast", "balanced", "high"], {"default": "balanced"}),
            },
            "optional": {
                "control":          ("CORTEX_CONTROL",),
                "steps":            ("INT",   {"default": 50, "min": 10, "max": 100}),
                "octree_resolution": ("INT",  {"default": 512, "min": 128, "max": 1024, "step": 64}),
                "guidance_scale":   ("FLOAT", {"default": 5.5, "min": 1.0, "max": 15.0, "step": 0.5}),
                "flashvdm":         ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "IMAGE")
    RETURN_NAMES  = ("mesh", "preview")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, image, quality_preset="balanced", control=None,
                steps=50, octree_resolution=512, guidance_scale=5.5, flashvdm=False):
        from ..adapters.hunyuan3d_adapter import Hunyuan3DAdapter
        from ..bridge.file_bridge import FileBridge
        from ..types.config import QUALITY_PRESETS
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        preset = QUALITY_PRESETS.get("hunyuan3d-omni", {}).get(quality_preset, {})
        mesh = Hunyuan3DAdapter.reconstruct_omni(
            image_path=img_path, control=control,
            steps=preset.get("steps", steps),
            octree_resolution=preset.get("octree_resolution", octree_resolution),
            guidance_scale=preset.get("guidance_scale", guidance_scale),
            flashvdm=preset.get("flashvdm", flashvdm),
        )
        return (mesh, _make_preview(mesh))


# ─────────────────────────────────────────────────────────────────────────────
# 6. 多视角重建路由器（算法选择 + 视图馈入）
# ─────────────────────────────────────────────────────────────────────────────
class Cortex3d_MultiviewReconstruction:
    ALGORITHMS = ["instantmesh", "trellis2", "hunyuan3d-2.1", "hunyuan3d-2.0", "triposr"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images":     ("IMAGE",),
                "algorithm":  (cls.ALGORITHMS, {"default": "instantmesh"}),
                "quality_preset": (["fast", "balanced", "high", "ultra"], {"default": "balanced"}),
            },
            "optional": {
                "cortex_config": ("CORTEX_CONFIG",),
                "seed":          ("INT", {"default": 42}),
            }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES  = ("CORTEX_MESH", "IMAGE")
    RETURN_NAMES  = ("mesh", "preview")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    def execute(self, images, algorithm, quality_preset, cortex_config=None, seed=None):
        # INPUT_IS_LIST=True 时所有入参都是列表
        algo     = algorithm[0]     if isinstance(algorithm, list)     else algorithm
        preset   = quality_preset[0] if isinstance(quality_preset, list) else quality_preset
        seed_val = (seed[0] if isinstance(seed, list) else seed) or 42
        images_list = images if isinstance(images, list) else [images]

        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        paths = [fb.tensor_to_tmp_png(img) for img in images_list]
        primary = paths[0] if paths else None

        mesh = None
        if algo == "instantmesh":
            from ..adapters.instantmesh_adapter import InstantMeshAdapter
            mesh = InstantMeshAdapter.reconstruct_multiview(views=paths, seed=seed_val)
        elif algo == "trellis2":
            from ..adapters.trellis2_adapter import Trellis2Adapter
            mesh = Trellis2Adapter.reconstruct_multiview(image_paths=paths, seed=seed_val)
        elif algo.startswith("hunyuan3d"):
            ver = "2.1" if "2.1" in algo else "2.0"
            from ..adapters.hunyuan3d_adapter import Hunyuan3DAdapter
            mesh = Hunyuan3DAdapter.reconstruct(image_path=primary, version=ver,
                                                no_texture=(preset == "fast"))
        elif algo == "triposr":
            from ..adapters.triposr_adapter import TripoSRAdapter
            mesh = TripoSRAdapter.reconstruct(image_path=primary)

        return (mesh, _make_preview(mesh))
