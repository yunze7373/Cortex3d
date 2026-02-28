"""
Cortex3d 全局错误处理与进度报告工具
────────────────────────────────────
- CortexError     : 统一异常基类
- node_guard      : 节点执行异常安全装饰器（返回占位值而非崩溃ComfyUI）
- ProgressReporter: 向 ComfyUI WebSocket 推送进度消息
"""
from __future__ import annotations
import logging
import traceback
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger("cortex3d")


# ── 统一异常 ──────────────────────────────────────────────────────────────────

class CortexError(Exception):
    """所有 Cortex3d 节点错误的基类。"""
    def __init__(self, message: str, node_type: str = "", recoverable: bool = True):
        super().__init__(message)
        self.node_type   = node_type
        self.recoverable = recoverable


class DockerError(CortexError):
    """Docker 容器调用失败。"""


class ApiError(CortexError):
    """云端 API 调用失败（Gemini / AiProxy）。"""


class MeshError(CortexError):
    """3D 网格处理失败。"""


# ── 节点异常安全包装 ──────────────────────────────────────────────────────────

def node_guard(fallback_fn: Optional[Callable] = None):
    """
    装饰 ComfyUI 节点的 execute() 方法，捕获所有异常并返回安全占位值。

    用法::

        class Cortex3d_MyNode:
            @node_guard()
            def execute(self, ...):
                ...
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            try:
                return fn(self, *args, **kwargs)
            except KeyboardInterrupt:
                raise
            except CortexError as e:
                logger.error(f"[{e.node_type or fn.__qualname__}] {e}")
                _send_comfyui_error(str(e))
                if fallback_fn:
                    return fallback_fn(self, *args, **kwargs)
                return _auto_fallback(fn)
            except Exception as e:
                tb = traceback.format_exc()
                logger.error(f"[{fn.__qualname__}] 未处理异常:\n{tb}")
                _send_comfyui_error(f"{type(e).__name__}: {e}")
                if fallback_fn:
                    return fallback_fn(self, *args, **kwargs)
                return _auto_fallback(fn)
        return wrapper
    return decorator


def _auto_fallback(fn: Callable):
    """根据节点类的 RETURN_TYPES 生成最小化占位返回值。"""
    import torch

    # 尝试从所属类的 RETURN_TYPES 推断每个输出槽的占位值
    cls = None
    qualname = getattr(fn, "__qualname__", "")
    if "." in qualname:
        cls_name = qualname.rsplit(".", 1)[0]
        # fn.__globals__ 中可能有所属类（同模块中已定义）
        cls = fn.__globals__.get(cls_name)

    if cls and hasattr(cls, "RETURN_TYPES"):
        placeholders = []
        for rtype in cls.RETURN_TYPES:
            if rtype == "IMAGE":
                placeholders.append(torch.zeros(1, 64, 64, 3))
            elif rtype == "CORTEX_MESH":
                # 返回空 CortexMesh 占位
                try:
                    from ..types.mesh import CortexMesh
                    placeholders.append(CortexMesh())
                except Exception:
                    placeholders.append(None)
            elif rtype in ("STRING",):
                placeholders.append("")
            elif rtype in ("INT",):
                placeholders.append(0)
            elif rtype in ("FLOAT",):
                placeholders.append(0.0)
            elif rtype in ("BOOLEAN",):
                placeholders.append(False)
            else:
                placeholders.append(None)
        return tuple(placeholders)

    # 最通用的占位：空图像
    return (torch.zeros(1, 64, 64, 3),)


def _send_comfyui_error(msg: str):
    """尝试通过 ComfyUI PromptServer 向前端推送错误消息。"""
    try:
        from server import PromptServer
        PromptServer.instance.send_sync("cortex3d.error", {"message": msg})
    except Exception:
        pass  # 在单元测试或独立运行时无 PromptServer


# ── 进度报告 ─────────────────────────────────────────────────────────────────

class ProgressReporter:
    """
    向 ComfyUI 前端推送进度条消息。

    用法::

        pr = ProgressReporter(node_id, total_steps=10)
        pr.update(1, "正在生成多视角图像...")
        ...
        pr.done("3D 重建完成")
    """
    def __init__(self, node_id: Any = None, total: int = 100):
        self.node_id = node_id
        self.total   = total
        self._step   = 0

    def update(self, step: int, message: str = ""):
        self._step = step
        pct = int(step / max(self.total, 1) * 100)
        logger.info(f"[progress] {pct}% — {message}")
        self._push({"value": pct, "max": 100, "message": message})

    def increment(self, message: str = ""):
        self.update(self._step + 1, message)

    def done(self, message: str = "完成"):
        self.update(self.total, message)

    def _push(self, data: dict):
        try:
            from server import PromptServer
            PromptServer.instance.send_sync("cortex3d.progress", {
                "node": self.node_id, **data,
            })
        except Exception:
            pass


# ── 日志配置 ─────────────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO"):
    """配置 cortex3d 日志器（避免重复注册 handler）。"""
    log = logging.getLogger("cortex3d")
    if log.handlers:
        return
    log.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(name)s] %(levelname)s — %(message)s",
        datefmt="%H:%M:%S",
    ))
    log.addHandler(handler)
    log.propagate = False
