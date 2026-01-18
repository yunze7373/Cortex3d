#!/usr/bin/env python3
"""
Mesh Sharpening Post-Processor for Cortex3d

Enhances edge details on smooth meshes using various sharpening techniques:
1. Inverse Laplacian Sharpening - pushes vertices away from centroid
2. Curvature-based enhancement - amplifies high-curvature regions  
3. Edge detection and enhancement

Usage:
    python mesh_sharpener.py input.glb --output sharpened.glb --strength 0.5
"""

import argparse
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

# Lazy imports
trimesh = None
scipy = None


def _ensure_imports():
    """Lazy import dependencies"""
    global trimesh, scipy
    if trimesh is None:
        import trimesh as _trimesh
        import scipy.sparse as _scipy
        trimesh = _trimesh
        scipy = _scipy


def compute_laplacian_matrix(mesh):
    """
    Compute the graph Laplacian matrix for a mesh.
    L = D - A, where D is degree matrix and A is adjacency matrix.
    
    Returns:
        scipy sparse matrix (n_vertices x n_vertices)
    """
    _ensure_imports()
    
    n_vertices = len(mesh.vertices)
    
    # Build adjacency from edges
    edges = mesh.edges_unique
    
    # Create sparse adjacency matrix
    row = np.concatenate([edges[:, 0], edges[:, 1]])
    col = np.concatenate([edges[:, 1], edges[:, 0]])
    data = np.ones(len(row))
    
    adjacency = scipy.sparse.coo_matrix(
        (data, (row, col)), 
        shape=(n_vertices, n_vertices)
    ).tocsr()
    
    # Degree matrix (diagonal)
    degrees = np.array(adjacency.sum(axis=1)).flatten()
    degree_matrix = scipy.sparse.diags(degrees)
    
    # Laplacian = D - A
    laplacian = degree_matrix - adjacency
    
    return laplacian, degrees


def laplacian_sharpen(mesh, strength: float = 0.3, iterations: int = 1):
    """
    Sharpen mesh using inverse Laplacian method.
    
    Instead of moving vertices towards neighbors (smoothing),
    we move them AWAY from neighbors (sharpening).
    
    Args:
        mesh: trimesh.Trimesh object
        strength: sharpening strength (0.1-1.0 typical, negative for smoothing)
        iterations: number of sharpening iterations
    
    Returns:
        New trimesh.Trimesh with sharpened vertices
    """
    _ensure_imports()
    
    vertices = mesh.vertices.copy()
    n_vertices = len(vertices)
    
    print(f"[INFO] Applying Laplacian sharpening (strength={strength}, iterations={iterations})...")
    
    for i in range(iterations):
        # For each vertex, compute the centroid of its neighbors
        # Then move AWAY from that centroid (opposite of smoothing)
        
        new_vertices = vertices.copy()
        
        # Get vertex neighbors efficiently
        for v_idx in range(n_vertices):
            # Find all edges containing this vertex
            edge_mask = np.any(mesh.edges_unique == v_idx, axis=1)
            neighbor_edges = mesh.edges_unique[edge_mask]
            
            # Get neighbor vertex indices
            neighbors = neighbor_edges[neighbor_edges != v_idx]
            
            if len(neighbors) == 0:
                continue
            
            # Compute centroid of neighbors
            neighbor_positions = vertices[neighbors]
            centroid = neighbor_positions.mean(axis=0)
            
            # Current position
            current = vertices[v_idx]
            
            # Laplacian vector (pointing towards centroid - this is what smoothing uses)
            laplacian_vec = centroid - current
            
            # For sharpening, we move AWAY from centroid (negative direction)
            # new_pos = current - strength * laplacian_vec
            new_vertices[v_idx] = current - strength * laplacian_vec
        
        vertices = new_vertices
        print(f"  Iteration {i+1}/{iterations} complete")
    
    # Create new mesh with sharpened vertices
    sharpened = trimesh.Trimesh(
        vertices=vertices,
        faces=mesh.faces.copy(),
        process=False
    )
    
    # Preserve visual properties if available
    if hasattr(mesh, 'visual') and mesh.visual is not None:
        sharpened.visual = mesh.visual
    
    return sharpened


def curvature_sharpen(mesh, strength: float = 0.5):
    """
    Sharpen mesh based on local curvature.
    Vertices in high-curvature regions are pushed outward along normals.
    
    Args:
        mesh: trimesh.Trimesh object  
        strength: curvature amplification factor
    
    Returns:
        New trimesh.Trimesh with curvature-enhanced vertices
    """
    _ensure_imports()
    
    print(f"[INFO] Applying curvature-based sharpening (strength={strength})...")
    
    vertices = mesh.vertices.copy()
    
    # Get vertex normals
    vertex_normals = mesh.vertex_normals
    
    # Estimate curvature from normal variations
    # High curvature = large angle between vertex normal and neighbor normals
    n_vertices = len(vertices)
    curvature = np.zeros(n_vertices)
    
    for v_idx in range(n_vertices):
        # Find neighbors
        edge_mask = np.any(mesh.edges_unique == v_idx, axis=1)
        neighbor_edges = mesh.edges_unique[edge_mask]
        neighbors = neighbor_edges[neighbor_edges != v_idx]
        
        if len(neighbors) == 0:
            continue
        
        # Compute angle between vertex normal and neighbor normals
        v_normal = vertex_normals[v_idx]
        n_normals = vertex_normals[neighbors]
        
        # Dot product gives cosine of angle
        dots = np.dot(n_normals, v_normal)
        
        # Curvature estimate: 1 - mean(dot) gives higher values for sharper regions
        curvature[v_idx] = 1.0 - np.mean(dots)
    
    # Normalize curvature
    if curvature.max() > 0:
        curvature = curvature / curvature.max()
    
    # Push vertices outward along normals, proportional to curvature
    displacement = vertex_normals * (curvature[:, np.newaxis] * strength * 0.01)
    vertices = vertices + displacement
    
    # Create new mesh
    sharpened = trimesh.Trimesh(
        vertices=vertices,
        faces=mesh.faces.copy(),
        process=False
    )
    
    if hasattr(mesh, 'visual') and mesh.visual is not None:
        sharpened.visual = mesh.visual
    
    return sharpened


def edge_enhance(mesh, angle_threshold: float = 30.0, push_strength: float = 0.02):
    """
    Detect and enhance sharp edges in the mesh.
    
    Finds edges where dihedral angle exceeds threshold,
    then pushes those vertices outward to emphasize the edge.
    
    Args:
        mesh: trimesh.Trimesh object
        angle_threshold: minimum dihedral angle (degrees) to consider as edge
        push_strength: how far to push edge vertices (relative to edge length)
    
    Returns:
        New trimesh.Trimesh with enhanced edges
    """
    _ensure_imports()
    
    print(f"[INFO] Applying edge enhancement (threshold={angle_threshold}°, strength={push_strength})...")
    
    vertices = mesh.vertices.copy()
    
    # Get face adjacency and face normals
    face_normals = mesh.face_normals
    face_adjacency = mesh.face_adjacency
    face_adjacency_edges = mesh.face_adjacency_edges
    
    # Find sharp edges (high dihedral angle)
    edge_vertices_to_enhance = set()
    
    for i, (f1, f2) in enumerate(face_adjacency):
        n1 = face_normals[f1]
        n2 = face_normals[f2]
        
        # Angle between face normals
        dot = np.clip(np.dot(n1, n2), -1, 1)
        angle = np.degrees(np.arccos(dot))
        
        if angle >= angle_threshold:
            # This is a sharp edge - mark its vertices
            edge_verts = face_adjacency_edges[i]
            edge_vertices_to_enhance.add(edge_verts[0])
            edge_vertices_to_enhance.add(edge_verts[1])
    
    print(f"  Found {len(edge_vertices_to_enhance)} vertices on sharp edges")
    
    # Push edge vertices outward along their normals
    vertex_normals = mesh.vertex_normals
    
    for v_idx in edge_vertices_to_enhance:
        vertices[v_idx] += vertex_normals[v_idx] * push_strength
    
    # Create new mesh
    enhanced = trimesh.Trimesh(
        vertices=vertices,
        faces=mesh.faces.copy(),
        process=False
    )
    
    if hasattr(mesh, 'visual') and mesh.visual is not None:
        enhanced.visual = mesh.visual
    
    return enhanced


def sharpen_mesh(
    mesh,
    method: str = "combined",
    laplacian_strength: float = 0.3,
    laplacian_iterations: int = 2,
    curvature_strength: float = 0.5,
    edge_threshold: float = 20.0,
    edge_strength: float = 0.015
):
    """
    Apply mesh sharpening with configurable method.
    
    Args:
        mesh: input trimesh.Trimesh
        method: "laplacian", "curvature", "edge", or "combined"
        laplacian_strength: strength for Laplacian sharpening
        laplacian_iterations: iterations for Laplacian sharpening
        curvature_strength: strength for curvature enhancement
        edge_threshold: angle threshold for edge detection (degrees)
        edge_strength: push strength for edge vertices
    
    Returns:
        Sharpened trimesh.Trimesh
    """
    _ensure_imports()
    
    result = mesh
    
    if method in ["laplacian", "combined"]:
        result = laplacian_sharpen(result, laplacian_strength, laplacian_iterations)
    
    if method in ["curvature", "combined"]:
        result = curvature_sharpen(result, curvature_strength)
    
    if method in ["edge", "combined"]:
        result = edge_enhance(result, edge_threshold, edge_strength)
    
    return result


def process_mesh_file(
    input_path: str,
    output_path: Optional[str] = None,
    method: str = "combined",
    strength: float = 0.5,
    **kwargs
) -> str:
    """
    Load, sharpen, and save a mesh file.
    
    Args:
        input_path: path to input mesh (GLB, OBJ, STL, etc.)
        output_path: path for output (default: adds _sharp suffix)
        method: sharpening method
        strength: overall strength multiplier
        **kwargs: additional parameters for sharpen_mesh
    
    Returns:
        Path to output file
    """
    _ensure_imports()
    
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_sharp{input_path.suffix}"
    else:
        output_path = Path(output_path)
    
    print(f"\n{'='*60}")
    print(f"Mesh Sharpener")
    print(f"{'='*60}")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Method: {method}")
    print(f"Strength: {strength}")
    
    # Load mesh
    print(f"\n[INFO] Loading mesh...")
    scene = trimesh.load(str(input_path))
    
    # Handle scene vs single mesh
    if isinstance(scene, trimesh.Scene):
        # Extract all meshes from scene
        meshes = []
        for name, geom in scene.geometry.items():
            if isinstance(geom, trimesh.Trimesh):
                print(f"  Processing geometry: {name}")
                
                # Apply strength multiplier to all parameters
                sharp_params = {
                    'method': method,
                    'laplacian_strength': kwargs.get('laplacian_strength', 0.3) * strength,
                    'laplacian_iterations': kwargs.get('laplacian_iterations', 2),
                    'curvature_strength': kwargs.get('curvature_strength', 0.5) * strength,
                    'edge_threshold': kwargs.get('edge_threshold', 20.0),
                    'edge_strength': kwargs.get('edge_strength', 0.015) * strength
                }
                
                sharpened = sharpen_mesh(geom, **sharp_params)
                scene.geometry[name] = sharpened
        
        result = scene
    else:
        # Single mesh
        sharp_params = {
            'method': method,
            'laplacian_strength': kwargs.get('laplacian_strength', 0.3) * strength,
            'laplacian_iterations': kwargs.get('laplacian_iterations', 2),
            'curvature_strength': kwargs.get('curvature_strength', 0.5) * strength,
            'edge_threshold': kwargs.get('edge_threshold', 20.0),
            'edge_strength': kwargs.get('edge_strength', 0.015) * strength
        }
        
        result = sharpen_mesh(scene, **sharp_params)
    
    # Save result
    print(f"\n[INFO] Saving sharpened mesh to {output_path}...")
    result.export(str(output_path))
    
    # Print stats
    if isinstance(result, trimesh.Trimesh):
        print(f"\n[INFO] Mesh stats:")
        print(f"  Vertices: {len(result.vertices)}")
        print(f"  Faces: {len(result.faces)}")
    
    print(f"\n{'='*60}")
    print(f"[SUCCESS] Sharpening complete: {output_path}")
    print(f"{'='*60}")
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Mesh Sharpening Post-Processor")
    parser.add_argument("input", type=str, help="Input mesh file (GLB, OBJ, STL)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output file path")
    parser.add_argument("--method", choices=["laplacian", "curvature", "edge", "combined"], 
                        default="combined", help="Sharpening method")
    parser.add_argument("--strength", type=float, default=1.0, 
                        help="Overall strength multiplier (0.1-2.0)")
    parser.add_argument("--laplacian-strength", type=float, default=0.3,
                        help="Laplacian sharpening strength")
    parser.add_argument("--laplacian-iterations", type=int, default=2,
                        help="Laplacian sharpening iterations")
    parser.add_argument("--curvature-strength", type=float, default=0.5,
                        help="Curvature enhancement strength")
    parser.add_argument("--edge-threshold", type=float, default=20.0,
                        help="Edge detection angle threshold (degrees)")
    parser.add_argument("--edge-strength", type=float, default=0.015,
                        help="Edge enhancement push strength")
    
    args = parser.parse_args()
    
    process_mesh_file(
        args.input,
        args.output,
        method=args.method,
        strength=args.strength,
        laplacian_strength=args.laplacian_strength,
        laplacian_iterations=args.laplacian_iterations,
        curvature_strength=args.curvature_strength,
        edge_threshold=args.edge_threshold,
        edge_strength=args.edge_strength
    )


if __name__ == "__main__":
    main()
