"""TripoSRAdapter — 封装 run_triposr.py 通过 Docker 的调用。"""
from __future__ import annotations
import logging
from typing import Optional
from ..bridge.docker_bridge import DockerBridge
from ..bridge.file_bridge import FileBridge
from ..types.mesh import CortexMesh

logger = logging.getLogger(__name__)
_bridge = DockerBridge()
_fb = FileBridge()


class TripoSRAdapter:

    @staticmethod
    def reconstruct(
        image_path: str,
        mc_resolution: int = 256,
        bake_texture: bool = True,
        texture_resolution: int = 2048,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_triposr"))
        container_img = _fb.to_container_path(image_path)
        container_out = _fb.to_container_path(out_dir)

        result = _bridge.exec_script(
            service="instantmesh",           # TripoSR 共享 instantmesh 容器
            script="/workspace/scripts/run_triposr.py",
            args={
                "output_dir":          container_out,
                "mc_resolution":       mc_resolution,
                "texture_resolution":  texture_resolution,
            },
            flags=(["bake_texture"] if bake_texture else []),
            timeout=600,
        )
        # 位置参数（图像路径）追加在所有 --args 之后
        if result.get("success") is None:
            return None

        # 手动添加位置参数 — exec_script 不直接支持，补丁方式
        import subprocess
        fb = _fb
        cmd = [
            "docker", "compose", "-f", _bridge.compose_file,
            "exec", "-T", "instantmesh",
            "python3", "/workspace/scripts/run_triposr.py",
            container_img,
            "--output-dir", container_out,
            "--mc-resolution", str(mc_resolution),
            "--texture-resolution", str(texture_resolution),
        ]
        if bake_texture:
            cmd.append("--bake-texture")

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            logger.error(f"TripoSR 失败: {proc.stderr[:1000]}")
            return None

        obj_path = _fb.find_latest_file(out_dir, "*.obj")
        if not obj_path:
            return None
        return CortexMesh(file_path=obj_path, format="obj", source_algo="triposr")
