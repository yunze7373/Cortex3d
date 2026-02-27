"""FileBridge — 宿主/容器路径转换与临时文件管理。

Docker 挂载约定:
  宿主: CORTEX3D_WORKSPACE (默认项目根目录)
  容器: /workspace
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class FileBridge:
    """宿主与容器之间的路径映射和文件 I/O 工具。"""

    def __init__(self, workspace: Optional[str] = None):
        self.workspace = Path(
            workspace
            or os.environ.get(
                "CORTEX3D_WORKSPACE",
                str(Path(__file__).parent.parent.parent),
            )
        )
        self.container_root = Path("/workspace")

    # ── 路径转换 ──────────────────────────────────────────────────────

    def to_container_path(self, host_path: str) -> str:
        """将宿主绝对路径转换为容器内路径。"""
        p = Path(host_path)
        try:
            rel = p.relative_to(self.workspace)
            return str(self.container_root / rel)
        except ValueError:
            # 已经是容器路径，直接返回
            return host_path

    def to_host_path(self, container_path: str) -> str:
        """将容器内路径转换为宿主绝对路径。"""
        p = Path(container_path)
        try:
            rel = p.relative_to(self.container_root)
            return str(self.workspace / rel)
        except ValueError:
            return container_path

    # ── ComfyUI IMAGE tensor 工具 ──────────────────────────────────────

    def tensor_to_pil(self, image_tensor):
        """ComfyUI IMAGE tensor (B,H,W,C float32 0-1) → PIL Image。"""
        from PIL import Image
        arr = (image_tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    def tensor_to_tmp_png(self, image_tensor, name: str = "comfyui_input") -> str:
        """将 ComfyUI IMAGE tensor 保存为临时 PNG，返回宿主绝对路径。"""
        from PIL import Image
        tmp_dir = self.workspace / "outputs" / "comfyui_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        out = str(tmp_dir / f"{name}.png")
        img = self.tensor_to_pil(image_tensor)
        img.save(out)
        logger.debug(f"tensor → {out}")
        return out

    def pil_to_tensor(self, pil_image):
        """PIL Image → ComfyUI IMAGE tensor (1,H,W,C float32 0-1)。"""
        import torch
        from PIL import Image
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        arr = np.array(pil_image).astype(np.float32) / 255.0
        return torch.from_numpy(arr).unsqueeze(0)

    def path_to_tensor(self, image_path: str):
        """从文件路径读取图像并转为 ComfyUI IMAGE tensor。"""
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        return self.pil_to_tensor(img)

    # ── 临时目录管理 ──────────────────────────────────────────────────

    def make_output_dir(self, subdir: str) -> Path:
        """在 outputs/ 下创建子目录并返回 Path。"""
        d = self.workspace / "outputs" / subdir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def find_latest_file(self, directory: str, pattern: str = "*.glb") -> Optional[str]:
        """在目录中找最新修改的匹配文件，返回路径字符串或 None。"""
        d = Path(directory)
        if not d.exists():
            return None
        files = sorted(d.rglob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
        return str(files[0]) if files else None
