#!/usr/bin/env python3
"""mesh_sharpener.py

Industrial Mesh Sharpening Post-Processor for Cortex3d

What this script does
---------------------
Enhances edge and mid-frequency details on smooth meshes using a *stable* post-process:
  1) Inverse Laplacian sharpening (edge-aware, scale-aware, vectorized)
  2) Curvature-based enhancement (scale-aware)
  3) Dihedral edge detection + enhancement (scale-aware)

Key upgrades (vs the original)
------------------------------
- FAST: no O(V*E) per-vertex edge scans; uses sparse adjacency for vectorized updates
- STABLE: per-step displacement clamping (prevents flips/self-intersections in practice)
- INDUSTRIAL: edge-aware masking (preserve flat regions), robust curvature normalization
- CONSISTENT: all distances are normalized by mean edge length (strength is portable)

Usage:
  python3 scripts/mesh_sharpener.py input.glb --output sharpened.glb --strength 1.5

Notes:
- This is a post-process. It will NOT invent micro-geometry (buttons/stitched seams);
  it improves readability of existing mid-scale structure.
- For ultra-fine detail, prefer normal/height baking after this step.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

import numpy as np

# Lazy imports (keep startup fast)
trimesh = None
sp = None  # scipy.sparse


def _ensure_imports():
    global trimesh, sp
    if trimesh is None:
        import trimesh as _trimesh
        import scipy.sparse as _sp
        trimesh = _trimesh
        sp = _sp


@dataclass
class SharpenConfig:
    method: str = "combined"  # laplacian|curvature|edge|combined

    # Base (dimensionless) strengths. Distances are internally scaled by mean edge length.
    laplacian_strength: float = 0.30
    laplacian_iterations: int = 2
    curvature_strength: float = 0.50
    edge_threshold_deg: float = 20.0
    edge_strength: float = 0.015

    # Stability / gating
    clamp_factor: float = 0.25  # max per-step move = clamp_factor * mean_edge_len
    flatness_gamma: float = 1.5  # higher => less change on flat areas
    edge_boost: float = 0.75     # extra weight on dihedral edges
    curvature_percentile: float = 95.0  # robust curvature normalization


# -----------------------------
# Geometry helpers (fast)
# -----------------------------

def _build_adjacency(mesh) -> "scipy.sparse.csr_matrix":
    """Undirected vertex adjacency from unique edges."""
    _ensure_imports()
    n = len(mesh.vertices)
    edges = mesh.edges_unique
    if edges is None or len(edges) == 0:
        return sp.csr_matrix((n, n))

    row = np.concatenate([edges[:, 0], edges[:, 1]])
    col = np.concatenate([edges[:, 1], edges[:, 0]])
    data = np.ones(len(row), dtype=np.float32)

    A = sp.coo_matrix((data, (row, col)), shape=(n, n)).tocsr()
    A.sum_duplicates()
    return A


def _degrees(A) -> np.ndarray:
    deg = np.asarray(A.sum(axis=1)).reshape(-1)
    deg = deg.astype(np.float32)
    deg[deg == 0] = 1.0
    return deg


def _mean_edge_length(mesh) -> float:
    # trimesh provides edges_unique_length
    try:
        el = mesh.edges_unique_length
        if el is not None and len(el) > 0:
            m = float(np.mean(el))
            return m if m > 1e-12 else 1.0
    except Exception:
        pass

    # Fallback
    edges = mesh.edges_unique
    if edges is None or len(edges) == 0:
        return 1.0
    v = mesh.vertices
    d = np.linalg.norm(v[edges[:, 0]] - v[edges[:, 1]], axis=1)
    m = float(np.mean(d))
    return m if m > 1e-12 else 1.0


def _dihedral_edge_vertices(mesh, threshold_deg: float) -> np.ndarray:
    """Return boolean mask (n_vertices,) marking vertices on sharp dihedral edges."""
    # face adjacency arrays are already relatively optimized in trimesh
    face_adjacency = mesh.face_adjacency
    if face_adjacency is None or len(face_adjacency) == 0:
        return np.zeros(len(mesh.vertices), dtype=bool)

    fn = mesh.face_normals
    fae = mesh.face_adjacency_edges

    n1 = fn[face_adjacency[:, 0]]
    n2 = fn[face_adjacency[:, 1]]
    dots = np.einsum("ij,ij->i", n1, n2)
    dots = np.clip(dots, -1.0, 1.0)
    angles = np.degrees(np.arccos(dots))

    sharp = angles >= float(threshold_deg)
    if not np.any(sharp):
        return np.zeros(len(mesh.vertices), dtype=bool)

    sharp_edges = fae[sharp]
    mask = np.zeros(len(mesh.vertices), dtype=bool)
    mask[sharp_edges.reshape(-1)] = True
    return mask


def _curvature_from_normals(A, deg: np.ndarray, normals: np.ndarray, percentile: float) -> np.ndarray:
    """Fast curvature proxy: 1 - mean(dot(n_i, n_j)) over neighbors.

    Returns a [0,1] normalized curvature signal (robustly normalized by percentile).
    """
    # Sum neighbor normals
    neigh_sum = A @ normals  # (n,3)
    # Sum of dot products with self normal
    dot_sum = np.einsum("ij,ij->i", neigh_sum, normals)
    mean_dot = dot_sum / deg
    # curvature proxy
    curv = 1.0 - mean_dot
    curv = np.clip(curv, 0.0, 2.0)

    # Robust normalize
    p = float(np.percentile(curv, percentile)) if curv.size else 1.0
    if p <= 1e-12:
        return np.zeros_like(curv, dtype=np.float32)
    curv = (curv / p).astype(np.float32)
    curv = np.clip(curv, 0.0, 1.0)
    return curv


def _clamp_displacement(disp: np.ndarray, max_step: float) -> np.ndarray:
    """Clamp per-vertex displacement magnitude."""
    if max_step <= 0:
        return disp
    mag = np.linalg.norm(disp, axis=1)
    too_big = mag > max_step
    if np.any(too_big):
        scale = (max_step / (mag[too_big] + 1e-12)).astype(np.float32)
        disp[too_big] *= scale[:, None]
    return disp


# -----------------------------
# Sharpen passes
# -----------------------------

def laplacian_sharpen_industrial(mesh, A, deg, cfg: SharpenConfig, overall_strength: float = 1.0):
    """Inverse Laplacian sharpening with edge-aware gating + clamping.

    Update rule (vectorized):
      neighbor_mean = (A V) / deg
      delta = V - neighbor_mean
      V <- V + s * w * delta

    where w is an edge-aware weight derived from curvature and dihedral edges.
    """
    _ensure_imports()

    V = mesh.vertices.astype(np.float32).copy()
    mean_el = _mean_edge_length(mesh)
    max_step = cfg.clamp_factor * mean_el

    # Precompute signals on the *original* mesh geometry for stability
    normals = mesh.vertex_normals.astype(np.float32)
    curvature = _curvature_from_normals(A, deg, normals, cfg.curvature_percentile)

    # Flatness gating: emphasize high curvature, suppress flat areas
    # w_curv in [0,1]
    w_curv = np.power(curvature, cfg.flatness_gamma).astype(np.float32)

    # Dihedral edge boost mask
    edge_mask = _dihedral_edge_vertices(mesh, cfg.edge_threshold_deg)
    w_edge = np.zeros(len(V), dtype=np.float32)
    w_edge[edge_mask] = 1.0

    # Combine weights: base 0.15 ensures some sharpening everywhere (very mild)
    w = 0.15 + 0.85 * w_curv
    w = w * (1.0 + cfg.edge_boost * w_edge)
    w = np.clip(w, 0.0, 2.0).astype(np.float32)

    s = float(cfg.laplacian_strength) * float(overall_strength)

    print(f"[INFO] Applying Laplacian sharpening (vectorized) (strength={s:.4f}, iterations={cfg.laplacian_iterations})")
    print(f"  Scale: mean_edge_len={mean_el:.6f}, max_step={max_step:.6f}")

    for it in range(int(cfg.laplacian_iterations)):
        neigh_mean = (A @ V) / deg[:, None]
        delta = V - neigh_mean
        disp = (s * w)[:, None] * delta
        disp = _clamp_displacement(disp, max_step)
        V = V + disp
        print(f"  Iteration {it+1}/{cfg.laplacian_iterations} complete")

    out = trimesh.Trimesh(vertices=V, faces=mesh.faces.copy(), process=False)
    if hasattr(mesh, "visual") and mesh.visual is not None:
        out.visual = mesh.visual
    return out


def curvature_sharpen_industrial(mesh, A, deg, cfg: SharpenConfig, overall_strength: float = 1.0):
    """Push vertices along normals based on curvature proxy (scale-aware + clamped)."""
    _ensure_imports()

    V = mesh.vertices.astype(np.float32).copy()
    mean_el = _mean_edge_length(mesh)
    max_step = cfg.clamp_factor * mean_el

    normals = mesh.vertex_normals.astype(np.float32)
    curvature = _curvature_from_normals(A, deg, normals, cfg.curvature_percentile)

    # Use a smaller scale than mean edge length; curvature displacement is subtle
    base = 0.10 * mean_el
    s = float(cfg.curvature_strength) * float(overall_strength)

    print(f"[INFO] Applying curvature sharpening (strength={s:.4f}, base={base:.6f})")

    disp = normals * (curvature[:, None] * (s * base))
    disp = _clamp_displacement(disp, max_step)
    V = V + disp

    out = trimesh.Trimesh(vertices=V, faces=mesh.faces.copy(), process=False)
    if hasattr(mesh, "visual") and mesh.visual is not None:
        out.visual = mesh.visual
    return out


def edge_enhance_industrial(mesh, cfg: SharpenConfig, overall_strength: float = 1.0):
    """Enhance dihedral edges by pushing edge vertices along a stable direction.

    Direction: vertex normal (stable). Strength: scale-aware.
    """
    _ensure_imports()

    V = mesh.vertices.astype(np.float32).copy()
    mean_el = _mean_edge_length(mesh)
    max_step = cfg.clamp_factor * mean_el

    edge_mask = _dihedral_edge_vertices(mesh, cfg.edge_threshold_deg)
    n_edge = int(edge_mask.sum())

    # scale edge push by mean edge length
    s = float(cfg.edge_strength) * float(overall_strength)
    push = (s * mean_el)

    print(f"[INFO] Applying edge enhancement (threshold={cfg.edge_threshold_deg}°, strength={s:.4f}, push={push:.6f})")
    print(f"  Found {n_edge} vertices on sharp edges")

    if n_edge == 0:
        out = trimesh.Trimesh(vertices=V, faces=mesh.faces.copy(), process=False)
        if hasattr(mesh, "visual") and mesh.visual is not None:
            out.visual = mesh.visual
        return out

    normals = mesh.vertex_normals.astype(np.float32)
    disp = np.zeros_like(V, dtype=np.float32)
    disp[edge_mask] = normals[edge_mask] * push
    disp = _clamp_displacement(disp, max_step)
    V = V + disp

    out = trimesh.Trimesh(vertices=V, faces=mesh.faces.copy(), process=False)
    if hasattr(mesh, "visual") and mesh.visual is not None:
        out.visual = mesh.visual
    return out


def sharpen_mesh(mesh, cfg: SharpenConfig, overall_strength: float = 1.0):
    _ensure_imports()

    A = _build_adjacency(mesh)
    deg = _degrees(A)

    result = mesh

    if cfg.method in ["laplacian", "combined"]:
        result = laplacian_sharpen_industrial(result, A, deg, cfg, overall_strength)
        # Recompute adjacency not necessary; topology same

    if cfg.method in ["curvature", "combined"]:
        # Use adjacency from original mesh topology for curvature proxy
        result = curvature_sharpen_industrial(result, A, deg, cfg, overall_strength)

    if cfg.method in ["edge", "combined"]:
        result = edge_enhance_industrial(result, cfg, overall_strength)

    return result


# -----------------------------
# File I/O
# -----------------------------

def process_mesh_file(
    input_path: str,
    output_path: Optional[str] = None,
    cfg: Optional[SharpenConfig] = None,
    strength: float = 1.0,
) -> str:
    _ensure_imports()

    cfg = cfg or SharpenConfig()

    input_path_p = Path(input_path)
    if output_path is None:
        output_path_p = input_path_p.parent / f"{input_path_p.stem}_sharp{input_path_p.suffix}"
    else:
        output_path_p = Path(output_path)

    print("\n" + "=" * 60)
    print("Mesh Sharpener (Industrial)")
    print("=" * 60)
    print(f"Input:  {input_path_p}")
    print(f"Output: {output_path_p}")
    print(f"Method: {cfg.method}")
    print(f"Strength: {strength}")

    print("\n[INFO] Loading mesh...")
    scene = trimesh.load(str(input_path_p))

    if isinstance(scene, trimesh.Scene):
        for name, geom in scene.geometry.items():
            if isinstance(geom, trimesh.Trimesh):
                print(f"  Processing geometry: {name}")
                scene.geometry[name] = sharpen_mesh(geom, cfg, overall_strength=strength)
        result = scene
    else:
        result = sharpen_mesh(scene, cfg, overall_strength=strength)

    print(f"\n[INFO] Saving sharpened mesh to {output_path_p}...")
    result.export(str(output_path_p))

    if isinstance(result, trimesh.Trimesh):
        print("\n[INFO] Mesh stats:")
        print(f"  Vertices: {len(result.vertices)}")
        print(f"  Faces:    {len(result.faces)}")

    print("\n" + "=" * 60)
    print(f"[SUCCESS] Sharpening complete: {output_path_p}")
    print("=" * 60)

    return str(output_path_p)


def main():
    p = argparse.ArgumentParser(description="Industrial Mesh Sharpening Post-Processor")
    p.add_argument("input", type=str, help="Input mesh file (GLB, OBJ, STL)")
    p.add_argument("--output", "-o", type=str, default=None, help="Output file path")
    p.add_argument(
        "--method",
        choices=["laplacian", "curvature", "edge", "combined"],
        default="combined",
        help="Sharpening method",
    )
    p.add_argument("--strength", type=float, default=1.0, help="Overall strength multiplier")

    # Expose core knobs (dimensionless)
    p.add_argument("--laplacian-strength", type=float, default=0.30, help="Inverse Laplacian base strength")
    p.add_argument("--laplacian-iterations", type=int, default=2, help="Inverse Laplacian iterations")
    p.add_argument("--curvature-strength", type=float, default=0.50, help="Curvature enhancement strength")
    p.add_argument("--edge-threshold", type=float, default=20.0, help="Dihedral edge angle threshold (deg)")
    p.add_argument("--edge-strength", type=float, default=0.015, help="Edge enhancement strength")

    # Stability knobs
    p.add_argument("--clamp-factor", type=float, default=0.25, help="Max step as fraction of mean edge length")
    p.add_argument("--flatness-gamma", type=float, default=1.5, help="Suppress sharpening on flat areas")
    p.add_argument("--edge-boost", type=float, default=0.75, help="Extra weight on dihedral edges")
    p.add_argument(
        "--curvature-percentile",
        type=float,
        default=95.0,
        help="Percentile used to normalize curvature (robust)",
    )

    args = p.parse_args()

    cfg = SharpenConfig(
        method=args.method,
        laplacian_strength=args.laplacian_strength,
        laplacian_iterations=args.laplacian_iterations,
        curvature_strength=args.curvature_strength,
        edge_threshold_deg=args.edge_threshold,
        edge_strength=args.edge_strength,
        clamp_factor=args.clamp_factor,
        flatness_gamma=args.flatness_gamma,
        edge_boost=args.edge_boost,
        curvature_percentile=args.curvature_percentile,
    )

    process_mesh_file(args.input, args.output, cfg=cfg, strength=float(args.strength))


if __name__ == "__main__":
    main()
