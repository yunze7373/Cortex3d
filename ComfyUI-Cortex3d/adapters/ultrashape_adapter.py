"""UltraShapeAdapter — 封装 UltraShape 精修容器 / Gradio 接口。"""
from __future__ import annotations
import logging
import subprocess
from typing import Optional, Literal
from ..bridge.docker_bridge import DockerBridge
from ..bridge.file_bridge import FileBridge
from ..types.mesh import CortexMesh

logger = logging.getLogger(__name__)
_bridge = DockerBridge()
_fb = FileBridge()

UltraPreset = Literal["lowmem", "fast", "balanced", "high", "ultra"]


class UltraShapeAdapter:

    @staticmethod
    def refine(
        image_path: str,
        mesh_path: str,
        preset: UltraPreset = "balanced",
        low_vram: bool = False,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_ultrashape"))
        container_img  = _fb.to_container_path(image_path)
        container_mesh = _fb.to_container_path(mesh_path)
        container_out  = _fb.to_container_path(out_dir)

        cmd = [
            "docker", "compose", "-f", _bridge.compose_file,
            "exec", "-T", "ultrashape",
            "python3", "/workspace/scripts/run_ultrashape.py",
            "--image",     container_img,
            "--mesh",      container_mesh,
            "--preset",    preset,
            "--output-dir", container_out,
        ]
        if low_vram:
            cmd.append("--low-vram")

        timeout_map = {"lowmem": 600, "fast": 900, "balanced": 1200, "high": 1800, "ultra": 3600}
        timeout = timeout_map.get(preset, 1200)

        logger.info(f"UltraShape 精修 preset={preset}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            logger.error(f"UltraShape 失败:\n{proc.stderr[:1200]}")
            return None

        glb = _fb.find_latest_file(out_dir, "*.glb")
        if not glb:
            glb = _fb.find_latest_file(out_dir, "*.obj")
        if not glb:
            return None
        return CortexMesh(
            file_path=glb,
            format="glb" if glb.endswith(".glb") else "obj",
            source_algo="ultrashape",
        )

    @staticmethod
    def refine_texture_only(
        mesh_path: str,
        image_path: str,
        texture_resolution: int = 2048,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        """仅重新烘焙纹理，不重建几何体（适合已有良好网格的情况）。"""
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_ultrashape_tex"))
        container_img  = _fb.to_container_path(image_path)
        container_mesh = _fb.to_container_path(mesh_path)
        container_out  = _fb.to_container_path(out_dir)

        cmd = [
            "docker", "compose", "-f", _bridge.compose_file,
            "exec", "-T", "ultrashape",
            "python3", "/workspace/scripts/run_ultrashape.py",
            "--image",              container_img,
            "--mesh",               container_mesh,
            "--texture-only",
            "--texture-resolution", str(texture_resolution),
            "--output-dir",         container_out,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            logger.error(f"UltraShape 纹理烘焙失败:\n{proc.stderr[:800]}")
            return None

        glb = _fb.find_latest_file(out_dir, "*.glb")
        if not glb:
            return None
        return CortexMesh(file_path=glb, format="glb", source_algo="ultrashape")
