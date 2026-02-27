"""BlenderAdapter — 封装 blender_factory.py CLI，支持本地或 Docker 调用。"""
from __future__ import annotations
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Literal
from ..bridge.file_bridge import FileBridge
from ..types.mesh import CortexMesh

logger = logging.getLogger(__name__)
_fb = FileBridge()

PrintProfile = Literal["fdm", "resin", "sla", "multi_material"]


def _blender_bin() -> Optional[str]:
    """尝试找到本地 Blender 二进制。"""
    for name in ("blender", "blender3", "blender4"):
        path = shutil.which(name)
        if path:
            return path
    common = ["/usr/bin/blender", "/usr/local/bin/blender", "/Applications/Blender.app/Contents/MacOS/Blender"]
    for p in common:
        if Path(p).exists():
            return p
    return None


class BlenderAdapter:

    @staticmethod
    def prepare_for_print(
        mesh_path: str,
        profile: PrintProfile = "fdm",
        height_mm: float = 100.0,
        voxel_size_mm: float = 0.5,
        decimate_ratio: float = 0.5,
        skip_remesh: bool = False,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        """调用 scripts/blender_factory.py 准备打印网格，返回 STL。"""
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_blender"))
        blender = _blender_bin()

        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        blender_script = scripts_dir / "blender_factory.py"

        if not blender_script.exists():
            logger.error(f"未找到 blender_factory.py: {blender_script}")
            return None

        if blender:
            # 本地 Blender 调用
            cmd = [
                blender, "--background", "--python", str(blender_script),
                "--",            # Blender 在 -- 之后传递给脚本的参数
                mesh_path,
                "--output-dir",     out_dir,
                "--profile",        profile,
                "--height-mm",      str(height_mm),
                "--voxel-size-mm",  str(voxel_size_mm),
                "--decimate-ratio", str(decimate_ratio),
            ]
            if skip_remesh:
                cmd.append("--skip-remesh")
            timeout = 600
        else:
            # Docker 容器（假设有挂载 blender 的容器，或者直接用 instantmesh 内的 blender）
            from ..bridge.docker_bridge import DockerBridge
            _bridge = DockerBridge()
            container_mesh = _fb.to_container_path(mesh_path)
            container_out  = _fb.to_container_path(out_dir)
            cmd = [
                "docker", "compose", "-f", _bridge.compose_file,
                "exec", "-T", "instantmesh",
                "blender", "--background", "--python",
                "/workspace/scripts/blender_factory.py",
                "--",
                container_mesh,
                "--output-dir",     container_out,
                "--profile",        profile,
                "--height-mm",      str(height_mm),
                "--voxel-size-mm",  str(voxel_size_mm),
                "--decimate-ratio", str(decimate_ratio),
            ]
            if skip_remesh:
                cmd.append("--skip-remesh")
            timeout = 900

        logger.info(f"Blender 打印预处理: profile={profile} height={height_mm}mm")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            logger.warning(f"Blender 退出码={proc.returncode}:\n{proc.stderr[:800]}")

        stl = _fb.find_latest_file(out_dir, "*.stl")
        if not stl:
            stl = _fb.find_latest_file(out_dir, "*.obj")
        if not stl:
            return None
        return CortexMesh(
            file_path=stl,
            format="stl" if stl.endswith(".stl") else "obj",
            source_algo="blender",
        )

    @staticmethod
    def repair_mesh(
        mesh_path: str,
        output_dir: Optional[str] = None,
    ) -> Optional[CortexMesh]:
        """简单网格修复：修补孔洞 + 确保流形。复用 blender_factory --repair-only。"""
        out_dir = output_dir or str(_fb.make_output_dir("comfyui_blender_repair"))
        blender = _blender_bin()
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        blender_script = scripts_dir / "blender_factory.py"

        if not blender or not blender_script.exists():
            logger.error("无法找到 Blender 或 blender_factory.py")
            return None

        cmd = [
            blender, "--background", "--python", str(blender_script),
            "--", mesh_path, "--output-dir", out_dir, "--repair-only",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        stl = _fb.find_latest_file(out_dir, "*.stl") or _fb.find_latest_file(out_dir, "*.obj")
        if not stl:
            return None
        return CortexMesh(file_path=stl, format="stl", source_algo="blender")
