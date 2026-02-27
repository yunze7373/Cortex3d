"""DockerBridge — 通过 docker compose exec 调用容器内脚本的抽象层。

使用模式:
    bridge = DockerBridge()
    result = bridge.exec_script(
        service="trellis2",
        script="/workspace/scripts/run_trellis2.py",
        args={"image": "/workspace/outputs/front.png", "output": "/workspace/outputs"},
        flags=["no-texture"],
        timeout=900,
    )
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DockerBridge:
    """封装 docker compose exec，将 ComfyUI 节点调用路由到对应 GPU 容器。"""

    def __init__(
        self,
        compose_file: Optional[str] = None,
        workspace: Optional[str] = None,
    ):
        # compose.yml 路径
        self.compose_file = compose_file or os.environ.get(
            "CORTEX3D_COMPOSE_FILE",
            str(Path(__file__).parent.parent.parent / "compose.yml"),
        )
        # 宿主工作空间根目录（与容器内 /workspace 相同挂载点）
        self.workspace = workspace or os.environ.get(
            "CORTEX3D_WORKSPACE",
            str(Path(__file__).parent.parent.parent),
        )
        self.is_in_docker = Path("/.dockerenv").exists()

    # ── 公共接口 ──────────────────────────────────────────────────────────

    def is_running(self, service: str) -> bool:
        """检查指定服务的容器是否正在运行。"""
        try:
            result = subprocess.run(
                [
                    "docker", "compose",
                    "-f", self.compose_file,
                    "ps", "-q", "--status", "running", service,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return bool(result.stdout.strip())
        except Exception as e:
            logger.warning(f"检查容器状态失败 [{service}]: {e}")
            return False

    def ensure_running(self, service: str, timeout: int = 120) -> bool:
        """确保容器在运行，若未运行则启动并等待就绪。"""
        if self.is_running(service):
            return True
        logger.info(f"启动 Docker 容器: {service}")
        try:
            subprocess.run(
                [
                    "docker", "compose",
                    "-f", self.compose_file,
                    "up", "-d", "--no-recreate", service,
                ],
                check=True,
                timeout=timeout,
            )
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"启动容器 [{service}] 失败: {e}")
            return False

    def exec_script(
        self,
        service: str,
        script: str,
        args: Dict[str, Any],
        flags: List[str] = None,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """在容器内执行 Python 脚本。

        Args:
            service: docker compose 服务名（如 "trellis2"）。
            script:  容器内脚本路径（如 "/workspace/scripts/run_trellis2.py"）。
            args:    key-value 参数，转换为 ``--key value`` CLI 参数。
            flags:   布尔标志列表，转换为 ``--flag``（值为 True 时才添加）。
            timeout: 最大等待秒数。

        Returns:
            dict 包含 ``success``, ``stdout``, ``stderr``, ``return_code``。
        """
        if not self.ensure_running(service):
            return {
                "success": False,
                "stdout": "",
                "stderr": f"无法启动容器: {service}",
                "return_code": -1,
            }

        cmd = [
            "docker", "compose",
            "-f", self.compose_file,
            "exec", "-T", service,
            "python3", script,
        ]

        for key, value in args.items():
            cli_key = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    cmd.append(cli_key)
            elif value is not None:
                cmd.extend([cli_key, str(value)])

        for flag in (flags or []):
            cmd.append(f"--{flag.replace('_', '-')}")

        logger.debug(f"DockerBridge exec: {' '.join(cmd)}")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode != 0:
                logger.error(
                    f"容器脚本失败 [{service}/{script.split('/')[-1]}]:\n{proc.stderr}"
                )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "return_code": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"执行超时（>{timeout}s）: {service}/{script}",
                "return_code": -2,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -3,
            }

    def start(self, service: str) -> str:
        """启动服务并返回状态信息。"""
        try:
            subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "up", "-d", service],
                check=True, timeout=120,
            )
            return f"✅ 已启动: {service}"
        except Exception as e:
            return f"❌ 启动失败 [{service}]: {e}"

    def stop(self, service: str) -> str:
        """停止服务并返回状态信息。"""
        try:
            subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "stop", service],
                check=True, timeout=60,
            )
            return f"🛑 已停止: {service}"
        except Exception as e:
            return f"❌ 停止失败 [{service}]: {e}"

    def status(self, service: str) -> str:
        """查询服务状态，返回可读字符串。"""
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", self.compose_file, "ps", service],
                capture_output=True, text=True, timeout=15,
            )
            return result.stdout.strip() or "（无输出）"
        except Exception as e:
            return f"❌ 查询失败: {e}"
