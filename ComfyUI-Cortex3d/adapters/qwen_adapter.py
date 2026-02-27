"""QwenAdapter — 封装 scripts/qwen_image_edit_client.py 的调用（Qwen 图像编辑服务）。"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_URL = os.environ.get("QWEN_IMAGE_EDIT_URL", "http://localhost:8200")


class QwenAdapter:
    """封装 QwenImageEditClient。"""

    def __init__(self, server_url: str = _DEFAULT_URL):
        self.server_url = server_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from qwen_image_edit_client import QwenImageEditClient
                self._client = QwenImageEditClient(base_url=self.server_url)
            except ImportError as e:
                raise ImportError(f"无法导入 qwen_image_edit_client.py: {e}") from e
        return self._client

    def edit(
        self,
        image_path: str,
        prompt: str,
        cfg_scale: float = 4.0,
        steps: int = 50,
        seed: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """调用 Qwen 图像编辑，返回编辑后图像路径。"""
        client = self._get_client()
        try:
            return client.edit(
                image_path=image_path,
                prompt=prompt,
                cfg_scale=cfg_scale,
                steps=steps,
                seed=seed,
                output_path=output_path,
            )
        except Exception as e:
            logger.error(f"Qwen edit 失败: {e}")
            # 尝试直接 HTTP fallback
            from ..bridge.http_bridge import HttpBridge
            bridge = HttpBridge()
            return bridge.qwen_edit(
                base_url=self.server_url,
                image_path=image_path,
                prompt=prompt,
                cfg_scale=cfg_scale,
                steps=steps,
                seed=seed,
                output_path=output_path,
            )
