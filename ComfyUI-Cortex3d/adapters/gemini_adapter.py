"""GeminiAdapter — 封装 scripts/gemini_generator.py 的调用。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class GeminiAdapter:
    """直连 Gemini API 生成多视角图像。"""

    @staticmethod
    def generate_views(
        character_description: str,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3-pro-image-preview",
        output_dir: str = "test_images",
        style: str = "cinematic character",
        view_mode: str = "4-view",
        custom_views: Optional[List[str]] = None,
        negative_prompt: Optional[str] = None,
        reference_image_path: Optional[str] = None,
        use_strict_mode: bool = False,
        resolution: str = "2K",
        subject_only: bool = True,
        with_props: Optional[List[str]] = None,
    ) -> Optional[str]:
        """调用 gemini_generator.generate_character_views()。

        Returns:
            生成图像的文件路径（通常是四宫格 PNG），失败返回 None。
        """
        _api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not _api_key:
            raise ValueError(
                "Gemini API Key 未提供，请在节点中填写或设置环境变量 GEMINI_API_KEY"
            )
        try:
            from gemini_generator import generate_character_views
        except ImportError as e:
            raise ImportError(
                f"无法导入 gemini_generator.py: {e}\n"
                "请确认 scripts/ 目录在 sys.path 中。"
            ) from e

        # 确保输出目录存在
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        return generate_character_views(
            character_description=character_description,
            api_key=_api_key,
            model_name=model_name,
            output_dir=output_dir,
            auto_cut=True,
            style=style,
            view_mode=view_mode,
            custom_views=custom_views,
            negative_prompt=negative_prompt,
            reference_image_path=reference_image_path,
            use_strict_mode=use_strict_mode,
            resolution=resolution,
            subject_only=subject_only,
            with_props=with_props,
        )
