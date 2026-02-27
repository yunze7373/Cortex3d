"""CortexConfig — 算法质量配置数据类型"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict


# ── 内置质量预设参数表 ─────────────────────────────────────────────────────

QUALITY_PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "instantmesh": {
        "fast":     {"diffusion_steps": 30, "texture_resolution": 512},
        "balanced": {"diffusion_steps": 75, "texture_resolution": 1024},
        "high":     {"diffusion_steps": 100, "texture_resolution": 2048},
        "ultra":    {"diffusion_steps": 150, "texture_resolution": 4096},
    },
    "triposr": {
        "fast":     {"mc_resolution": 128, "texture_resolution": 1024},
        "balanced": {"mc_resolution": 256, "texture_resolution": 2048},
        "high":     {"mc_resolution": 384, "texture_resolution": 4096},
        "ultra":    {"mc_resolution": 512, "texture_resolution": 4096},
    },
    "trellis2": {
        "fast":     {"ss_steps": 5,  "slat_steps": 5,  "decimation": 200000, "texture_size": 1024},
        "balanced": {"ss_steps": 12, "slat_steps": 12, "decimation": 500000, "texture_size": 2048},
        "high":     {"ss_steps": 25, "slat_steps": 25, "decimation": 1000000, "texture_size": 4096},
        "ultra":    {"ss_steps": 50, "slat_steps": 50, "decimation": 2000000, "texture_size": 4096},
    },
    "hunyuan3d": {
        "fast":     {"no_texture": True},
        "balanced": {"no_texture": False},
        "high":     {"no_texture": False},
        "ultra":    {"no_texture": False},
    },
    "hunyuan3d-omni": {
        "fast":     {"steps": 20, "octree": 512, "guidance": 5.5, "flashvdm": True},
        "balanced": {"steps": 50, "octree": 512, "guidance": 5.5, "flashvdm": False},
        "high":     {"steps": 75, "octree": 768, "guidance": 7.0, "flashvdm": False},
        "ultra":    {"steps": 100, "octree": 1024, "guidance": 7.0, "flashvdm": False},
    },
    "ultrashape": {
        "lowmem":   {"preset": "lowmem"},
        "fast":     {"preset": "fast"},
        "balanced": {"preset": "balanced"},
        "high":     {"preset": "high"},
        "ultra":    {"preset": "ultra"},
    },
}


@dataclass
class CortexConfig:
    """算法质量配置，在 QualityPreset 节点和重建节点之间传递。

    Attributes:
        algorithm: 算法名称，如 "trellis2"。
        quality:   质量等级，"fast" | "balanced" | "high" | "ultra"。
        params:    实际叶子参数字典（可直接传给脚本）。
    """

    algorithm: str
    quality: str = "balanced"
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.params:
            self.params = self._resolve_params()

    def _resolve_params(self) -> Dict[str, Any]:
        algo_presets = QUALITY_PRESETS.get(self.algorithm, {})
        return dict(algo_presets.get(self.quality, {}))

    @classmethod
    def for_algorithm(cls, algorithm: str, quality: str = "balanced") -> "CortexConfig":
        return cls(algorithm=algorithm, quality=quality)

    def get(self, key: str, default=None):
        return self.params.get(key, default)

    def __repr__(self) -> str:
        return f"CortexConfig(algo={self.algorithm!r}, quality={self.quality!r}, params={self.params})"
