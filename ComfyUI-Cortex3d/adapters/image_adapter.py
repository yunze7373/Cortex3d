"""ImageAdapter — 封装 image_processor.py 和 image_enhancer.py 的调用。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class ImageAdapter:
    """封装图像预处理相关脚本。"""

    # ── 多视角切割 ─────────────────────────────────────────────────────

    @staticmethod
    def cut_multiview(
        image_path: str,
        output_dir: str,
        views: int = 4,
        remove_bg: bool = True,
        margin: int = 5,
    ) -> List[str]:
        """调用 image_processor.py 的 CLI，切割四宫格为独立视角图像。

        Returns:
            切割后各视角图像的路径列表（按视角顺序）。
        """
        import subprocess, sys
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        cmd = [
            sys.executable,
            str(scripts_dir / "image_processor.py"),
            image_path,
            "--output", output_dir,
            "--views", str(views),
            "--margin", str(margin),
        ]
        if not remove_bg:
            cmd.append("--no-rembg")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error(f"image_processor 失败:\n{result.stderr}")
            return []

        # 寻找输出的视角图像（通常命名为 *_front.png, *_back.png ...）
        out_dir = Path(output_dir)
        view_names = {
            4: ["front", "back", "left", "right"],
            6: ["front", "back", "left", "right", "front_left", "front_right"],
            8: ["front", "back", "left", "right",
                "front_left", "front_right", "back_left", "back_right"],
        }
        names = view_names.get(views, ["front", "back", "left", "right"])
        found = []
        for name in names:
            # 支持多种命名约定
            for pattern in [f"*_{name}.png", f"{name}.png", f"*{name}*.png"]:
                matches = list(out_dir.glob(pattern))
                if matches:
                    found.append(str(sorted(matches)[-1]))
                    break

        # 如果按名称找不到，按修改时间排序返回前 N 张 PNG
        if not found:
            pngs = sorted(out_dir.glob("*.png"), key=lambda f: f.stat().st_mtime)
            found = [str(p) for p in pngs[-views:]]

        return found

    @staticmethod
    def remove_background(image_path: str, output_path: Optional[str] = None) -> str:
        """使用 rembg 去除背景，返回 RGBA PNG 路径。"""
        try:
            from rembg import remove
            from PIL import Image
        except ImportError as e:
            raise ImportError(f"rembg 未安装: {e}") from e

        img = Image.open(image_path)
        result = remove(img)

        if not output_path:
            p = Path(image_path)
            output_path = str(p.parent / f"{p.stem}_nobg.png")
        result.save(output_path)
        return output_path

    # ── 图像增强 ──────────────────────────────────────────────────────

    @staticmethod
    def enhance(
        image_path: str,
        scale: int = 2,
        target_size: int = 1024,
        use_realesrgan: bool = True,
        use_gfpgan: bool = True,
        output_path: Optional[str] = None,
    ) -> str:
        """调用 image_enhancer.py CLI 进行超分 + 人脸增强。"""
        import subprocess, sys
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        cmd = [
            sys.executable,
            str(scripts_dir / "image_enhancer.py"),
            image_path,
            "--scale", str(scale),
            "--target-size", str(target_size),
        ]
        if not use_realesrgan:
            cmd.append("--no-realesrgan")
        if not use_gfpgan:
            cmd.append("--no-gfpgan")
        if output_path:
            cmd.extend(["--output", output_path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"image_enhancer 失败:\n{result.stderr}")
            return image_path  # 回退原图

        # 查找输出文件（通常是 *_enhanced.png）
        p = Path(image_path)
        enhanced = p.parent / f"{p.stem}_enhanced.png"
        return str(enhanced) if enhanced.exists() else image_path
