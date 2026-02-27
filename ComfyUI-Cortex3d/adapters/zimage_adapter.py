"""ZImageAdapter — 封装 scripts/zimage_client.py 的调用（Z-Image 本地服务）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_URL = os.environ.get("ZIMAGE_URL", "http://localhost:8199")


class ZImageAdapter:
    """封装 ZImageClient 以供 ComfyUI 节点调用。"""

    def __init__(self, server_url: str = _DEFAULT_URL):
        self.server_url = server_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from zimage_client import ZImageClient
                self._client = ZImageClient(base_url=self.server_url)
            except ImportError as e:
                raise ImportError(f"无法导入 zimage_client.py: {e}") from e
        return self._client

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 9,
        seed: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """文生图，返回图像文件路径。"""
        client = self._get_client()
        try:
            return client.generate(
                prompt=prompt,
                width=width,
                height=height,
                steps=steps,
                seed=seed,
                output_path=output_path,
            )
        except Exception as e:
            logger.error(f"ZImage generate 失败: {e}")
            return None

    def img2img(
        self,
        image_path: str,
        prompt: str,
        strength: float = 0.7,
        steps: int = 9,
        seed: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """图生图，返回图像文件路径。"""
        # ZImageClient 没有 img2img 带参数的独立接口，用 http_bridge 直接调用
        from ..bridge.http_bridge import HttpBridge
        bridge = HttpBridge()
        return bridge.zimage_img2img(
            base_url=self.server_url,
            image_path=image_path,
            prompt=prompt,
            strength=strength,
            steps=steps,
            seed=seed,
            output_path=output_path,
        )
