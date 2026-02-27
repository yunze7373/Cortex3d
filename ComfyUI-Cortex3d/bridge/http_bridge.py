"""HttpBridge — 对已有 HTTP 服务 (Flask/Gradio) 的轻量客户端封装。

覆盖的服务:
  - Z-Image  (port 8199)  — Flask REST
  - Qwen-edit(port 8200)  — Flask REST
  - UltraShape(port 7863) — Gradio API（暂通过 gradio_client 调用）
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class HttpBridge:
    """对容器内 HTTP 服务的统一调用封装。"""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ── 健康检查 ──────────────────────────────────────────────────────

    def health_check(self, base_url: str, endpoint: str = "/health") -> bool:
        """检查服务健康状态。"""
        try:
            resp = self.session.get(f"{base_url}{endpoint}", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def wait_for_service(
        self,
        base_url: str,
        endpoint: str = "/health",
        timeout: int = 180,
        interval: int = 5,
    ) -> bool:
        """轮询等待服务就绪。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.health_check(base_url, endpoint):
                logger.info(f"服务就绪: {base_url}")
                return True
            logger.debug(f"等待服务就绪: {base_url} (剩余 {deadline - time.time():.0f}s)")
            time.sleep(interval)
        logger.error(f"服务等待超时 (>{timeout}s): {base_url}")
        return False

    # ── 通用 POST ─────────────────────────────────────────────────────

    def post(
        self,
        url: str,
        payload: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """发送 JSON POST，返回响应 JSON 或 None。"""
        try:
            resp = self.session.post(
                url,
                json=payload,
                timeout=timeout or self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            logger.error(f"HTTP 错误 [{url}]: {e.response.status_code} {e.response.text[:500]}")
        except requests.RequestException as e:
            logger.error(f"请求失败 [{url}]: {e}")
        return None

    # ── 图像工具 ──────────────────────────────────────────────────────

    @staticmethod
    def image_path_to_base64(image_path: str) -> str:
        """将图像文件编码为 base64 字符串。"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def base64_to_image_path(b64: str, output_path: str) -> str:
        """将 base64 字符串解码并保存到文件，返回保存路径。"""
        data = base64.b64decode(b64)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
        return output_path

    # ── Z-Image 专用方法 ──────────────────────────────────────────────

    def zimage_generate(
        self,
        base_url: str,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 9,
        seed: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """调用 Z-Image /generate 接口。"""
        if not self.wait_for_service(base_url):
            return None
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
        }
        if seed is not None:
            payload["seed"] = seed

        data = self.post(f"{base_url}/generate", payload)
        if not data or "image" not in data:
            return None

        output_path = output_path or f"/tmp/zimage_{int(time.time())}.png"
        return self.base64_to_image_path(data["image"], output_path)

    def zimage_img2img(
        self,
        base_url: str,
        image_path: str,
        prompt: str,
        strength: float = 0.7,
        steps: int = 9,
        seed: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """调用 Z-Image /img2img 接口。"""
        if not self.wait_for_service(base_url):
            return None
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "image": self.image_path_to_base64(image_path),
            "strength": strength,
            "steps": steps,
        }
        if seed is not None:
            payload["seed"] = seed

        data = self.post(f"{base_url}/img2img", payload)
        if not data or "image" not in data:
            return None

        output_path = output_path or f"/tmp/zimage_i2i_{int(time.time())}.png"
        return self.base64_to_image_path(data["image"], output_path)

    # ── Qwen 图像编辑 ─────────────────────────────────────────────────

    def qwen_edit(
        self,
        base_url: str,
        image_path: str,
        prompt: str,
        cfg_scale: float = 4.0,
        steps: int = 50,
        seed: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """调用 Qwen-Image-Edit /edit 接口。"""
        if not self.wait_for_service(base_url, timeout=600):
            return None
        payload: Dict[str, Any] = {
            "prompt": prompt,
            "image_b64": self.image_path_to_base64(image_path),
            "cfg_scale": cfg_scale,
            "steps": steps,
        }
        if seed is not None:
            payload["seed"] = seed

        data = self.post(f"{base_url}/edit", payload, timeout=600)
        if not data or "image" not in data:
            return None

        output_path = output_path or f"/tmp/qwen_edit_{int(time.time())}.png"
        return self.base64_to_image_path(data["image"], output_path)
