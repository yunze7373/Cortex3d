"""AiProxyAdapter — 封装 scripts/aiproxy_client.py 的调用。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AiProxyAdapter:
    """通过 AiProxy 代理调用 Gemini 生成图像。"""

    @staticmethod
    def generate_image(
        prompt: str,
        token: Optional[str] = None,
        model: str = "gemini-3-pro-image-preview",
        reference_image_path: Optional[str] = None,
        resolution: str = "2K",
        aspect_ratio: str = "3:2",
        negative_prompt: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """调用 aiproxy_client.generate_image_via_proxy() 并保存结果。

        Returns:
            保存的图像文件路径，失败返回 None。
        """
        _token = token or os.environ.get("AIPROXY_TOKEN", "")
        if not _token:
            raise ValueError(
                "AiProxy Token 未提供，请在节点中填写或设置环境变量 AIPROXY_TOKEN"
            )

        try:
            from aiproxy_client import generate_image_via_proxy
        except ImportError as e:
            raise ImportError(f"无法导入 aiproxy_client.py: {e}") from e

        # 加载参考图像（转为 data URL）
        ref_data_url = None
        if reference_image_path:
            import base64
            suffix = Path(reference_image_path).suffix.lower().lstrip(".")
            mime = "image/png" if suffix == "png" else f"image/{suffix}"
            with open(reference_image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ref_data_url = f"data:{mime};base64,{b64}"

        result = generate_image_via_proxy(
            prompt=prompt,
            token=_token,
            model=model,
            reference_image=ref_data_url,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
        )

        if result is None:
            logger.error("AiProxy 生成失败，返回 None")
            return None

        image_bytes, mime_type = result
        ext = "png" if "png" in mime_type else "jpg"

        # 确定输出路径
        if not output_path:
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = Path("outputs") / "comfyui_aiproxy"
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(out_dir / f"aiproxy_{ts}.{ext}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        logger.info(f"AiProxy 图像已保存: {output_path}")
        return output_path
