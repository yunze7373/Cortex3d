#!/usr/bin/env python3
"""Mesh printability validator (Stage 2.5)

Goal: quickly score whether a generated mesh is usable for resin 28–35mm minis.

This script is intentionally conservative: it does not attempt heavy repairs.
It reports key diagnostics and an overall PASS/FAIL recommendation.

Usage:
  python scripts/mesh_validator.py path/to/mesh.obj
  python scripts/mesh_validator.py path/to/model.glb --json outputs/report.json

Exit codes:
  0: PASS
  2: FAIL
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

try:
    import trimesh
except ImportError as e:
    raise SystemExit(
        "Missing dependency: trimesh. Install with: pip install trimesh\n"
        f"Original error: {e}"
    )


@dataclass
class MeshReport:
    path: str
    file_type: str

    vertices: int
    faces: int
    components: int

    watertight: bool
    winding_consistent: bool
    euler_number: Optional[int]

    bounds_mm: Dict[str, float]
    volume_mm3: Optional[float]

    nonmanifold_edges: Optional[int]
    degenerate_faces: Optional[int]

    recommendation: str
    reasons: list[str]


def _to_single_mesh(scene_or_mesh: trimesh.Trimesh | trimesh.Scene) -> trimesh.Trimesh:
    if isinstance(scene_or_mesh, trimesh.Trimesh):
        return scene_or_mesh

    # Scene: concatenate geometry into one mesh (best-effort)
    geometries = []
    for geom in scene_or_mesh.geometry.values():
        if isinstance(geom, trimesh.Trimesh) and geom.vertices.size and geom.faces.size:
            geometries.append(geom)

    if not geometries:
        raise ValueError("No mesh geometry found in file")

    return trimesh.util.concatenate(geometries)


def _edge_nonmanifold_count(mesh: trimesh.Trimesh) -> int:
    # An edge should belong to exactly 2 faces for a watertight manifold surface.
    # edges_face is (n_edges, 2) with -1 for missing face.
    edges_face = mesh.edges_face
    if edges_face is None or len(edges_face) == 0:
        return 0

    # Count edges with missing adjacency or >2 adjacency (trimesh stores only 2, so
    # for >2 we approximate via unique_edges + faces adjacency below).
    missing = int(np.sum(np.any(edges_face < 0, axis=1)))

    # Approximate over-shared edges: use edge->face incidence counts from faces_unique_edges
    # This is a fast heuristic.
    unique_edges = mesh.edges_unique
    inv = mesh.edges_unique_inverse
    counts = np.bincount(inv, minlength=len(unique_edges))
    overshared = int(np.sum(counts > 2))

    return missing + overshared


def _degenerate_face_count(mesh: trimesh.Trimesh) -> int:
    # Degenerate faces have near-zero area.
    areas = mesh.area_faces
    if areas is None or len(areas) == 0:
        return 0
    return int(np.sum(areas <= 1e-12))


def validate_mesh(path: Path) -> MeshReport:
    loaded = trimesh.load(path, force="mesh")
    mesh = _to_single_mesh(loaded)

    # Ensure triangles (some pipelines emit quads)
    if not mesh.is_watertight and mesh.faces.shape[1] != 3:
        try:
            mesh = mesh.triangulate()
        except Exception:
            pass

    # Basic counts
    vertices = int(mesh.vertices.shape[0])
    faces = int(mesh.faces.shape[0])

    # Connected components
    try:
        components = int(len(mesh.split(only_watertight=False)))
    except Exception:
        components = 1

    # Bounds in mm (assume mesh units are meters? Actually most generators output unitless.
    # We report raw bounds and also mm-assumed by treating 1 unit = 1 meter is wrong.
    # Instead, we report bounds in "scene units" and also mm by assuming 1 unit = 1 meter.
    # BUT: in this repo, Blender stage scales to target height anyway. So bounds here are
    # mainly for sanity.
    bounds = mesh.bounds
    extents = mesh.extents

    # Convert: assume units are meters -> mm
    extents_mm = (extents * 1000.0).astype(float)

    watertight = bool(mesh.is_watertight)
    winding_consistent = bool(mesh.is_winding_consistent)

    euler_number: Optional[int]
    try:
        euler_number = int(mesh.euler_number)
    except Exception:
        euler_number = None

    volume_mm3: Optional[float]
    try:
        # volume assumes closed mesh; if not watertight it can be nonsense
        volume_mm3 = float(mesh.volume * 1e9) if watertight else None
    except Exception:
        volume_mm3 = None

    nonmanifold_edges: Optional[int]
    degenerate_faces: Optional[int]
    try:
        nonmanifold_edges = _edge_nonmanifold_count(mesh)
    except Exception:
        nonmanifold_edges = None

    try:
        degenerate_faces = _degenerate_face_count(mesh)
    except Exception:
        degenerate_faces = None

    # Recommendation logic (conservative)
    reasons: list[str] = []

    if vertices == 0 or faces == 0:
        reasons.append("empty mesh")

    if not watertight:
        reasons.append("not watertight (may fail slicing / cause leaks)")

    if nonmanifold_edges is not None and nonmanifold_edges > 0:
        reasons.append(f"non-manifold edges detected: {nonmanifold_edges}")

    if degenerate_faces is not None and degenerate_faces > 0:
        reasons.append(f"degenerate faces detected: {degenerate_faces}")

    if components > 5:
        reasons.append(f"too many disconnected components: {components}")

    # Resin mini heuristic: super huge meshes are hard to edit, but sliceable.
    if faces > 3_000_000:
        reasons.append(f"very high face count: {faces} (slow in Blender/slicer)")

    recommendation = "PASS" if len(reasons) == 0 else "FAIL"

    return MeshReport(
        path=str(path),
        file_type=path.suffix.lower().lstrip("."),
        vertices=vertices,
        faces=faces,
        components=components,
        watertight=watertight,
        winding_consistent=winding_consistent,
        euler_number=euler_number,
        bounds_mm={
            "x": float(extents_mm[0]),
            "y": float(extents_mm[1]),
            "z": float(extents_mm[2]),
        },
        volume_mm3=volume_mm3,
        nonmanifold_edges=nonmanifold_edges,
        degenerate_faces=degenerate_faces,
        recommendation=recommendation,
        reasons=reasons,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate mesh printability (quick heuristics)")
    parser.add_argument("mesh", type=Path, help="Path to .obj/.glb/.gltf/.ply")
    parser.add_argument("--json", dest="json_path", type=Path, default=None, help="Write JSON report to path")

    args = parser.parse_args()

    if not args.mesh.exists():
        raise SystemExit(f"Mesh not found: {args.mesh}")

    report = validate_mesh(args.mesh)

    print("=" * 60)
    print("Cortex3d Mesh Validator")
    print("=" * 60)
    print(f"Path: {report.path}")
    print(f"Vertices: {report.vertices:,}")
    print(f"Faces:    {report.faces:,}")
    print(f"Parts:    {report.components}")
    print(f"Watertight: {report.watertight}")
    if report.nonmanifold_edges is not None:
        print(f"Non-manifold edges: {report.nonmanifold_edges}")
    if report.degenerate_faces is not None:
        print(f"Degenerate faces:   {report.degenerate_faces}")
    print(f"Bounds (mm, assuming meters): X={report.bounds_mm['x']:.1f} Y={report.bounds_mm['y']:.1f} Z={report.bounds_mm['z']:.1f}")
    if report.volume_mm3 is not None:
        print(f"Volume (mm^3): {report.volume_mm3:.1f}")

    print("-" * 60)
    print(f"Recommendation: {report.recommendation}")
    if report.reasons:
        for r in report.reasons:
            print(f"- {r}")

    if args.json_path is not None:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[INFO] Wrote JSON report to: {args.json_path}")

    raise SystemExit(0 if report.recommendation == "PASS" else 2)


if __name__ == "__main__":
    main()
