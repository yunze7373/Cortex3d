"""ComfyUI-Cortex3d Bridge 层 — Docker / HTTP 容器通信抽象"""

from .docker_bridge import DockerBridge
from .http_bridge import HttpBridge
from .file_bridge import FileBridge

# 全局单例（节点中直接 import 使用）
docker = DockerBridge()
file_bridge = FileBridge()

__all__ = ["DockerBridge", "HttpBridge", "FileBridge", "docker", "file_bridge"]
