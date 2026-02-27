"""工具类节点 (4) — Docker管理 / 网格加载 / 网格保存 / 质量预设。"""
from __future__ import annotations
import os
from ..utils.errors import node_guard

CAT = "Cortex3d/Utility"


class Cortex3d_DockerManager:
    """检查 / 启动 / 停止指定 GPU 容器服务。"""
    SERVICES = [
        "instantmesh", "trellis2", "hunyuan3d", "hunyuan3d-2.1",
        "hunyuan3d-omni", "ultrashape", "zimage", "qwen-image-edit",
    ]
    ACTIONS = ["status", "start", "stop", "restart", "clear_cache"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "service": (cls.SERVICES,),
                "action":  (cls.ACTIONS, {"default": "status"}),
            }
        }

    RETURN_TYPES  = ("STRING", "BOOLEAN")
    RETURN_NAMES  = ("status_msg", "is_running")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, service, action):
        from ..bridge.docker_bridge import DockerBridge
        bridge = DockerBridge()
        try:
            if action == "status":
                running = bridge.is_running(service)
                msg = f"{service}: {'running ✓' if running else 'stopped ✗'}"
                return (msg, running)
            elif action == "start":
                bridge.start(service)
                running = bridge.is_running(service)
                return (f"{service}: started", running)
            elif action == "stop":
                bridge.stop(service)
                return (f"{service}: stopped", False)
            elif action == "restart":
                bridge.stop(service)
                bridge.start(service)
                running = bridge.is_running(service)
                return (f"{service}: restarted", running)
            elif action == "clear_cache":
                from ..adapters.cache import clear_all_caches
                clear_all_caches()
                return ("Cache cleared ✓", True)
        except Exception as e:
            return (f"Error: {e}", False)
        return (f"Unknown action: {action}", False)


class Cortex3d_MeshLoader:
    """从文件路径加载 3D 网格为 CORTEX_MESH 类型。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path":    ("STRING", {"default": ""}),
                "source_algo":  ("STRING", {"default": "external"}),
            }
        }

    RETURN_TYPES  = ("CORTEX_MESH", "STRING")
    RETURN_NAMES  = ("mesh", "info")
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, file_path, source_algo="external"):
        from ..types.mesh import CortexMesh
        if not file_path or not os.path.isfile(file_path):
            return (None, f"File not found: {file_path}")
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        if ext not in ("obj", "glb", "gltf", "stl", "ply", "fbx"):
            return (None, f"Unsupported format: {ext}")
        mesh = CortexMesh(file_path=file_path, format=ext, source_algo=source_algo)
        mesh.populate_stats()
        info = f"Loaded: {os.path.basename(file_path)} | v={mesh.vertices} f={mesh.faces}"
        return (mesh, info)


class Cortex3d_MeshSaver:
    """将 CORTEX_MESH 保存到指定目录，可以转换格式。"""
    FORMATS = ["obj", "glb", "stl", "ply"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mesh":       ("CORTEX_MESH",),
                "output_dir": ("STRING", {"default": ""}),
                "filename":   ("STRING", {"default": "output_mesh"}),
                "format":     (cls.FORMATS, {"default": "glb"}),
            }
        }

    RETURN_TYPES  = ("STRING",)
    RETURN_NAMES  = ("saved_path",)
    OUTPUT_NODE   = True
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, mesh, output_dir, filename, format):
        import shutil
        from ..bridge.file_bridge import FileBridge

        if mesh is None:
            return ("mesh is None",)

        fb = FileBridge()
        if output_dir and os.path.isdir(output_dir):
            save_dir = output_dir
        else:
            save_dir = str(fb.make_output_dir("comfyui_mesh_save"))

        dest = os.path.join(save_dir, f"{filename}.{format}")

        src_ext = os.path.splitext(mesh.file_path)[1].lower().lstrip(".")
        if src_ext == format:
            shutil.copy2(mesh.file_path, dest)
        else:
            try:
                import trimesh
                tm = trimesh.load(mesh.file_path, force="mesh")
                tm.export(dest)
            except Exception as e:
                return (f"Format conversion failed: {e}",)

        return (dest,)


class Cortex3d_QualityPreset:
    """输出 CORTEX_CONFIG 预设对象，供下游重建节点使用。"""
    ALGORITHMS    = ["instantmesh", "triposr", "trellis2", "hunyuan3d", "hunyuan3d-omni", "ultrashape"]
    PRESET_LEVELS = ["fast", "balanced", "high", "ultra"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "algorithm":    (cls.ALGORITHMS, {"default": "instantmesh"}),
                "preset_level": (cls.PRESET_LEVELS, {"default": "balanced"}),
            },
            "optional": {
                "custom_params": ("STRING", {"multiline": True, "default": "{}",
                                             "tooltip": "JSON string to override individual params"}),
            }
        }

    RETURN_TYPES  = ("CORTEX_CONFIG",)
    RETURN_NAMES  = ("config",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, algorithm, preset_level, custom_params="{}"):
        import json
        from ..types.config import CortexConfig, QUALITY_PRESETS

        preset_params = QUALITY_PRESETS.get(algorithm, {}).get(preset_level, {}).copy()
        try:
            overrides = json.loads(custom_params or "{}")
            preset_params.update(overrides)
        except json.JSONDecodeError as e:
            import logging
            logging.getLogger(__name__).warning(f"custom_params JSON parse error: {e}")

        cfg = CortexConfig(algorithm=algorithm, quality=preset_level, params=preset_params)
        return (cfg,)
