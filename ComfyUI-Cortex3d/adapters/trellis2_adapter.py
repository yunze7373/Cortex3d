"""Trellis2Adapter — 封装 run_trellis2.py 通过 trellis2 Docker 容器。"""
from __future__ import annotations
import logging
import subprocess
from typing import Optional
from ..bridge.docker_bridge import DockerBridge
from ..bridge.file_bridge import FileBridge
from ..types.mesh import CortexMesh

logger = logging.getLogger(__name__)
_bridge = DockerBridge()
_fb = FileBridge()

DEFAULT_MODEL = "microsoft/TRELLIS.2-4B"


class Trellis2Adapter:

    @staticmethod
    def reconstruct(
        image_path: str,
        model: str = DEFAULT_MODEL,
        ss_steps: int = 12,
        slat_steps: int = 12,
        seed: int = 42,
        decimation: int = 500_000,
        texture_size: int = 2048,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_trellis2"))
        container_img = _fb.to_container_path(image_path)
        container_out = _fb.to_container_path(out_dir)

        cmd = [
            "docker", "compose", "-f", _bridge.compose_file,
            "exec", "-T", "trellis2",
            "python3", "/workspace/scripts/run_trellis2.py",
            container_img,
            "--output",        container_out,
            "--model",         model,
            "--seed",          str(seed),
            "--decimation",    str(decimation),
            "--texture-size",  str(texture_size),
            "--ss-steps",      str(ss_steps),
            "--slat-steps",    str(slat_steps),
        ]
        logger.info(f"Trellis2 重建: {image_path}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            logger.error(f"Trellis2 失败:\n{proc.stderr[:1200]}")
            return None

        glb_path = _fb.find_latest_file(out_dir, "*.glb")
        if not glb_path:
            logger.warning("Trellis2 未找到 .glb 输出")
            return None
        return CortexMesh(file_path=glb_path, format="glb", source_algo="trellis2")

    @staticmethod
    def reconstruct_multiview(
        image_paths: list[str],
        **kwargs,
    ) -> Optional[CortexMesh]:
        """多视角模式：将第一张图作为主图（TRELLIS.2 前端只支持单图，其余做参考）。"""
        if not image_paths:
            return None
        return Trellis2Adapter.reconstruct(image_path=image_paths[0], **kwargs)
