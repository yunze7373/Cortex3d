"""PromptAdapter — 封装 scripts/config.py 中的提示词构建函数。"""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── 懒惰导入 config（脚本在 sys.path 中，由 __init__.py 注入）────────────

def _get_config():
    try:
        import config as _cfg
        return _cfg
    except ImportError as e:
        raise ImportError(
            "无法导入 scripts/config.py，请确认 CORTEX3D_WORKSPACE 配置正确，"
            f"以及 scripts/ 目录已添加到 sys.path。原始错误: {e}"
        ) from e


class PromptAdapter:
    """封装 config.py 的全部提示词构建函数，提供错误处理和回退逻辑。"""

    # ── 视角提示词构建 ────────────────────────────────────────────────

    @staticmethod
    def build_multiview_prompt(
        character_description: str,
        style: str = "cinematic character",
        view_mode: str = "4-view",
        custom_views: Optional[List[str]] = None,
        subject_only: bool = True,
        with_props: Optional[List[str]] = None,
    ) -> str:
        cfg = _get_config()
        try:
            return cfg.build_multiview_prompt(
                character_description=character_description,
                style=style,
                view_mode=view_mode,
                custom_views=custom_views,
                subject_only=subject_only,
                with_props=with_props,
            )
        except Exception as e:
            logger.error(f"build_multiview_prompt 失败: {e}")
            # 最简回退提示词
            return (
                f"3D character sheet, {character_description}, "
                f"4 views: front, back, left, right, transparent background"
            )

    @staticmethod
    def build_image_reference_prompt(
        character_description: str,
        view_mode: str = "4-view",
        custom_views: Optional[List[str]] = None,
        style: Optional[str] = None,
        subject_only: bool = True,
        with_props: Optional[List[str]] = None,
    ) -> str:
        cfg = _get_config()
        try:
            return cfg.build_image_reference_prompt(
                character_description=character_description,
                view_mode=view_mode,
                custom_views=custom_views,
                style=style,
                subject_only=subject_only,
                with_props=with_props,
            )
        except Exception as e:
            logger.error(f"build_image_reference_prompt 失败: {e}")
            return (
                f"Based on the reference image, create a {view_mode} character sheet "
                f"of {character_description}, transparent background"
            )

    @staticmethod
    def build_strict_copy_prompt(
        view_mode: str = "4-view",
        custom_views: Optional[List[str]] = None,
        style: Optional[str] = None,
        subject_only: bool = True,
        with_props: Optional[List[str]] = None,
        user_instruction: Optional[str] = None,
    ) -> str:
        cfg = _get_config()
        try:
            return cfg.build_strict_copy_prompt(
                view_mode=view_mode,
                custom_views=custom_views,
                style=style,
                subject_only=subject_only,
                with_props=with_props,
                user_instruction=user_instruction,
            )
        except Exception as e:
            logger.error(f"build_strict_copy_prompt 失败: {e}")
            return (
                f"Strictly copy the character from the reference image, "
                f"generate {view_mode} turnaround sheet, transparent background"
            )

    @staticmethod
    def build_composite_prompt(
        instruction: str,
        composite_type: str = "clothing",
        num_images: int = 2,
        style: Optional[str] = None,
    ) -> str:
        cfg = _get_config()
        try:
            return cfg.build_composite_prompt(
                instruction=instruction,
                composite_type=composite_type,
                num_images=num_images,
                style=style,
            )
        except Exception as e:
            logger.error(f"build_composite_prompt 失败: {e}")
            return (
                f"Composite image: {instruction}. Type: {composite_type}. "
                f"Transparent background, high quality"
            )

    @staticmethod
    def get_negative_prompt(categories: Optional[List[str]] = None) -> str:
        cfg = _get_config()
        try:
            return cfg.get_negative_prompt(categories=categories)
        except Exception as e:
            logger.error(f"get_negative_prompt 失败: {e}")
            return (
                "blurry, low quality, deformed, ugly, watermark, text, "
                "multiple heads, extra limbs, distorted, duplicated"
            )

    @staticmethod
    def get_view_config(
        view_mode: str = "4-view",
        custom_views: Optional[List[str]] = None,
    ):
        """返回 (views, rows, cols, aspect_ratio) 四元组。"""
        cfg = _get_config()
        try:
            return cfg.get_view_config(view_mode=view_mode, custom_views=custom_views)
        except Exception as e:
            logger.error(f"get_view_config 失败: {e}")
            # 默认 4 视角
            return (["front", "back", "left", "right"], 2, 2, "1:1")

    # ── 预设模板加载 ──────────────────────────────────────────────────

    @staticmethod
    def load_preset(preset_name: str) -> dict:
        """加载 scripts/prompts/presets/{preset_name}.yaml 并返回 dict。"""
        from pathlib import Path
        import yaml

        root = Path(__file__).parent.parent.parent / "scripts" / "prompts" / "presets"
        yaml_path = root / f"{preset_name}.yaml"
        if not yaml_path.exists():
            logger.warning(f"预设文件不存在: {yaml_path}")
            return {}
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
