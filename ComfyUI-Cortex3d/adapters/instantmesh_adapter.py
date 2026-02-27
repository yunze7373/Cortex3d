"""InstantMeshAdapter — 封装 run_instantmesh.py 通过 Docker 的调用。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from ..bridge.docker_bridge import DockerBridge
from ..bridge.file_bridge import FileBridge
from ..types.mesh import CortexMesh

logger = logging.getLogger(__name__)

_bridge = DockerBridge()
_fb = FileBridge()


class InstantMeshAdapter:

    @staticmethod
    def reconstruct(
        image_path: str,
        config: str = "instant-mesh-hq",
        diffusion_steps: int = 75,
        guidance_scale: float = 7.5,
        seed: int = 42,
        texture_resolution: int = 1024,
        export_texture: bool = True,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        """在 instantmesh 容器内运行 run_instantmesh.py，返回 CortexMesh。"""
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_instantmesh"))
        container_img  = _fb.to_container_path(image_path)
        container_out  = _fb.to_container_path(out_dir)
        workspace = Path(__file__).parent.parent.parent
        config_path = f"/workspace/configs/{config}.yaml"

        result = _bridge.exec_script(
            service="instantmesh",
            script="/workspace/scripts/run_instantmesh.py",
            args={
                "config":   config_path,
                "input":    container_img,
                "output_path": container_out,
                "diffusion_steps": diffusion_steps,
                "guidance_scale":  guidance_scale,
                "seed":     seed,
                "texture_resolution": texture_resolution,
            },
            flags=["export_texmap"] if export_texture else [],
            timeout=600,
        )
        if not result["success"]:
            logger.error(f"InstantMesh 失败: {result['stderr'][:1000]}")
            return None

        # 查找输出 OBJ
        obj_path = _fb.find_latest_file(out_dir, "*.obj")
        if not obj_path:
            logger.error("InstantMesh 未生成 OBJ 文件")
            return None
        return CortexMesh(file_path=obj_path, format="obj", source_algo="instantmesh")

    @staticmethod
    def reconstruct_multiview(
        views: list,
        config: str = "instant-mesh-hq",
        seed: int = 42,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        """多视角重建（调用 run_instantmesh_multiview.py）。"""
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_instantmesh_mv"))
        container_out = _fb.to_container_path(out_dir)
        config_path   = f"/workspace/configs/{config}.yaml"
        view_str = ",".join(_fb.to_container_path(v) for v in views)

        result = _bridge.exec_script(
            service="instantmesh",
            script="/workspace/scripts/run_instantmesh_multiview.py",
            args={
                "config":  config_path,
                "input":   view_str,
                "output_path": container_out,
                "seed":    seed,
            },
            timeout=600,
        )
        if not result["success"]:
            logger.error(f"InstantMesh 多视角失败: {result['stderr'][:1000]}")
            return None

        obj_path = _fb.find_latest_file(out_dir, "*.obj")
        if not obj_path:
            return None
        return CortexMesh(file_path=obj_path, format="obj", source_algo="instantmesh_mv")
