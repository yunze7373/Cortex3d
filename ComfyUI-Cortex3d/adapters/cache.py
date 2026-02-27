"""
Cortex3d 适配器缓存工具
──────────────────────
提供以下缓存机制：
  - ResultCache   : 基于参数 hash 的磁盘/内存结果缓存（避免重复重建）
  - ClientCache   : HTTP 客户端单例缓存（如 ZImageClient / QwenClient）
  - lru_result    : 函数级 LRU 内存缓存装饰器
"""
from __future__ import annotations
import hashlib
import json
import logging
import os
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ── 磁盘结果缓存目录 ──────────────────────────────────────────────────────────
_CACHE_ROOT = Path(os.environ.get("CORTEX3D_CACHE_DIR", "/tmp/cortex3d_cache"))


def _hash_args(*args, **kwargs) -> str:
    """将任意调用参数序列化为 SHA-256 短 hash。"""
    try:
        key = json.dumps({"a": args, "k": kwargs}, sort_keys=True, default=str)
    except Exception:
        key = str(args) + str(sorted(kwargs.items()))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class ResultCache:
    """
    轻量级磁盘缓存，用于缓存耗时重建结果的文件路径。

    用法::

        cache = ResultCache("instantmesh")
        hit = cache.get(image_path=img, steps=75)
        if hit:
            return hit
        result = ... 执行重建 ...
        cache.put(result, image_path=img, steps=75)
    """

    def __init__(self, namespace: str, ttl_hours: float = 24.0):
        self.ns     = namespace
        self.ttl    = ttl_hours * 3600
        self.dir    = _CACHE_ROOT / namespace
        self.dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.dir / "index.json"
        self._index: Dict[str, dict] = self._load_index()

    def _load_index(self) -> dict:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text())
            except Exception:
                return {}
        return {}

    def _save_index(self):
        self._index_path.write_text(json.dumps(self._index, indent=2))

    def _key(self, **kwargs) -> str:
        return _hash_args(**kwargs)

    def get(self, **kwargs) -> Optional[str]:
        """返回缓存的文件路径，缺失或过期时返回 None。"""
        key = self._key(**kwargs)
        entry = self._index.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > self.ttl:
            logger.debug(f"[cache:{self.ns}] 过期 key={key}")
            del self._index[key]
            self._save_index()
            return None
        path = entry["path"]
        if not Path(path).exists():
            del self._index[key]
            self._save_index()
            return None
        logger.info(f"[cache:{self.ns}] 命中 key={key} → {path}")
        return path

    def put(self, result_path: Optional[str], **kwargs):
        """将文件路径存入缓存。"""
        if not result_path:
            return
        key = self._key(**kwargs)
        self._index[key] = {"path": result_path, "ts": time.time()}
        self._save_index()
        logger.info(f"[cache:{self.ns}] 写入 key={key} → {result_path}")

    def clear(self):
        """清空本命名空间的全部缓存。"""
        self._index.clear()
        self._save_index()
        logger.info(f"[cache:{self.ns}] 已清空")


# ── HTTP 客户端单例缓存 ────────────────────────────────────────────────────────
_client_registry: Dict[str, Any] = {}


def get_or_create_client(key: str, factory: Callable) -> Any:
    """同一进程内复用同一个 HTTP 客户端实例，避免重复建立连接。"""
    if key not in _client_registry:
        _client_registry[key] = factory()
        logger.debug(f"[client_cache] 创建客户端: {key}")
    return _client_registry[key]


# ── LRU 内存缓存装饰器 ────────────────────────────────────────────────────────
def lru_result(maxsize: int = 32):
    """对函数返回值做 in-process LRU 缓存（参数须可 JSON 序列化）。"""
    from functools import lru_cache
    def decorator(fn):
        @lru_cache(maxsize=maxsize)
        def _cached(*args, **kwargs_tuple):
            kwargs = dict(kwargs_tuple)
            return fn(*args, **kwargs)

        @wraps(fn)
        def wrapper(*args, **kwargs):
            kwargs_tuple = tuple(sorted(kwargs.items()))
            return _cached(*args, **kwargs_tuple)

        wrapper.cache_clear = _cached.cache_clear
        wrapper.cache_info  = _cached.cache_info
        return wrapper
    return decorator


# ── 全局缓存清理 ──────────────────────────────────────────────────────────────
def clear_all_caches():
    """清理所有磁盘缓存目录（用于调试/重置）。"""
    import shutil
    if _CACHE_ROOT.exists():
        shutil.rmtree(_CACHE_ROOT)
        logger.info(f"[cache] 已删除缓存目录: {_CACHE_ROOT}")
    _client_registry.clear()
