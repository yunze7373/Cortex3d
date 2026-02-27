"""TripoSRAdapter — 封装 run_triposr.py 通过 Docker 的调用。"""
from __future__ import annotations
import logging
import subprocess
from typing import Optional
from ..bridge.docker_bridge import DockerBridge
from ..bridge.file_bridge import FileBridge
from ..types.mesh import CortexMesh
from .cache import ResultCache

logger = logging.getLogger(__name__)
_bridge = DockerBridge()
_fb = FileBridge()
_cache = ResultCache("triposr")


class TripoSRAdapter:

    @staticmethod
    def reconstruct(
        image_path: str,
        mc_resolution: int = 256,
        bake_texture: bool = True,
        texture_resolution: int = 2048,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        # ── 缓存查找 ──
        cache_kw = dict(image_path=image_path, mc_resolution=mc_resolution,
                        bake_texture=bake_texture, texture_resolution=texture_resolution)
        hit = _cache.get(**cache_kw)
        if hit:
            return CortexMesh(file_path=hit, format="obj", source_algo="triposr")

        out_dir = output_dir or str(_fb.make_output_dir("comfyui_triposr"))
        container_img = _fb.to_container_path(image_path)
        container_out = _fb.to_container_path(out_dir)

        # run_triposr.py 需要位置参数（图像路径），exec_script 不直接支持，
        # 因此直接使用 subprocess 构建命令
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

        logger.info(f"TripoSR 重建: {image_path}")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            logger.error(f"TripoSR 失败: {proc.stderr[:1000]}")
            return None

        obj_path = _fb.find_latest_file(out_dir, "*.obj")
        if not obj_path:
            logger.error("TripoSR 未生成 OBJ 文件")
            return None
        _cache.put(obj_path, **cache_kw)
        return CortexMesh(file_path=obj_path, format="obj", source_algo="triposr")
