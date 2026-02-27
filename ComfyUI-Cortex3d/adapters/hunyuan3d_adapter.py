"""Hunyuan3DAdapter — 封装 Hunyuan3D 2.0 / 2.1 / Omni 三个容器。"""
from __future__ import annotations
import logging
import subprocess
from typing import Optional, Literal
from ..bridge.docker_bridge import DockerBridge
from ..bridge.file_bridge import FileBridge
from ..types.mesh import CortexMesh
from ..types.control import CortexControl

logger = logging.getLogger(__name__)
_bridge = DockerBridge()
_fb = FileBridge()

HunyuanVersion = Literal["2.0", "2.1"]


class Hunyuan3DAdapter:

    # ------------------------------------------------------------------ #
    # Hunyuan3D 2.0 / 2.1
    # ------------------------------------------------------------------ #
    @staticmethod
    def reconstruct(
        image_path: str,
        version: HunyuanVersion = "2.1",
        no_texture: bool = False,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        service_map = {"2.0": "hunyuan3d", "2.1": "hunyuan3d-2.1"}
        service = service_map.get(version, "hunyuan3d-2.1")
        out_dir = output_dir or str(_fb.make_output_dir(f"comfyui_hunyuan_{version.replace('.','_')}"))
        container_img = _fb.to_container_path(image_path)
        container_out = _fb.to_container_path(out_dir)

        cmd = [
            "docker", "compose", "-f", _bridge.compose_file,
            "exec", "-T", service,
            "python3", "/workspace/scripts/run_hunyuan3d.py",
            container_img,
            "--output-dir", container_out,
        ]
        if no_texture:
            cmd.append("--no-texture")

        logger.info(f"Hunyuan3D {version} 重建: {image_path}")
        timeout = 1200 if version == "2.1" else 900
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            logger.error(f"Hunyuan3D {version} 失败:\n{proc.stderr[:1200]}")
            return None

        glb = _fb.find_latest_file(out_dir, "*.glb")
        if not glb:
            glb = _fb.find_latest_file(out_dir, "*.obj")
        if not glb:
            return None
        return CortexMesh(
            file_path=glb,
            format="glb" if glb.endswith(".glb") else "obj",
            source_algo=f"hunyuan3d-{version}",
        )

    # ------------------------------------------------------------------ #
    # Hunyuan3D-Omni
    # ------------------------------------------------------------------ #
    @staticmethod
    def reconstruct_omni(
        image_path: str,
        control: Optional[CortexControl] = None,
        steps: int = 50,
        octree_resolution: int = 512,
        guidance_scale: float = 5.5,
        flashvdm: bool = False,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_hunyuan_omni"))
        container_img = _fb.to_container_path(image_path)
        container_out = _fb.to_container_path(out_dir)

        cmd = [
            "docker", "compose", "-f", _bridge.compose_file,
            "exec", "-T", "hunyuan3d-omni",
            "python3", "/workspace/scripts/run_hunyuan3d_omni.py",
            container_img,
            "--output-dir",         container_out,
            "--steps",              str(steps),
            "--octree-resolution",  str(octree_resolution),
            "--guidance-scale",     str(guidance_scale),
        ]
        if flashvdm:
            cmd.append("--flashvdm")
        if control and control.control_type != "none":
            container_ctrl = _fb.to_container_path(control.data_path)
            cmd += ["--control-type", control.control_type, "--control-data", container_ctrl]

        logger.info(f"Hunyuan3D-Omni 重建: ctrl={control.control_type if control else 'none'}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            logger.error(f"Hunyuan3D-Omni 失败:\n{proc.stderr[:1200]}")
            return None

        glb = _fb.find_latest_file(out_dir, "*.glb")
        if not glb:
            return None
        return CortexMesh(file_path=glb, format="glb", source_algo="hunyuan3d-omni")
