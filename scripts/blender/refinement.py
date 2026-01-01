import bpy
import argparse
import sys
import bmesh
import math


def resolve_profile(profile: str | None, height_mm: float, voxel_size_mm: float):
    # Keep backward-compatible defaults unless a profile is explicitly selected.
    if profile is None or profile == "default":
        return height_mm, voxel_size_mm

    if profile == "resin-mini":
        # 28–35mm resin minis: aim ~32mm height, fairly fine voxel remesh.
        # Note: very small voxel sizes explode face count; this is a practical default.
        return 32.0, 0.05

    raise ValueError(f"Unknown profile: {profile}")

def cleanup_scene():
    """Remove all objects from the scene to start fresh."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def process_mesh(mesh_path, output_path, target_height_mm=100.0, voxel_size_mm=0.1, profile: str | None = None, decimate_ratio: float | None = None, skip_remesh: bool = False):
    """
    Imports a mesh, scales it to a specific height, remeshes it for printing, and exports to STL.
    """
    print(f"[INFO] Processing: {mesh_path}")

    target_height_mm, voxel_size_mm = resolve_profile(profile, target_height_mm, voxel_size_mm)
    
    # 1. Import Mesh
    if mesh_path.lower().endswith('.obj'):
        bpy.ops.wm.obj_import(filepath=mesh_path)
    elif mesh_path.lower().endswith('.glb') or mesh_path.lower().endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=mesh_path)
    else:
        print(f"[ERROR] Unsupported mesh format: {mesh_path}")
        sys.exit(1)
        
    # Select the imported object
    # usually the first selected object is the one we want
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj
    
    # 2. Geometry Cleanup (Pre-optimization)
    # Join if multiple objects were imported (unlikely for InstantMesh but good practice)
    if len(bpy.context.selected_objects) > 1:
        bpy.ops.object.join()
        
    # 3. Standardize Scale (Crucial for Voxel Remesh)
    # We want the Z-height to be exactly target_height_mm (e.g., 100mm)
    # Blender's default unit is usually Meters. 100mm = 0.1m.
    
    # First, apply all transforms so we get real dimensions
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    dims = obj.dimensions
    current_z = dims.z
    if current_z == 0:
        print("[ERROR] Object has 0 height.")
        sys.exit(1)
        
    # Calculate scale factor
    # target_height_mm is in mm. Convert to meters (Blender units).
    target_height_m = target_height_mm / 1000.0
    scale_factor = target_height_m / current_z
    
    obj.scale = (scale_factor, scale_factor, scale_factor)
    bpy.ops.object.transform_apply(scale=True)
    
    print(f"[INFO] Scaled model to {target_height_mm}mm height (Factor: {scale_factor:.4f})")
    
    # 3.5 Pre-Smooth (Crucial for removing source noise)
    # TripoSR/InstantMesh raw output can be noisy. Smooth it before remeshing.
    mod_smooth_pre = obj.modifiers.new(name="Pre_Smooth", type='LAPLACIANSMOOTH')
    mod_smooth_pre.iterations = 5
    mod_smooth_pre.lambda_factor = 0.1
    bpy.ops.object.modifier_apply(modifier="Pre_Smooth")

    # 4. Voxel Remesh
    if not skip_remesh:
        # This fuses the geometry and makes it water-tight.
        # Voxel size input is in mm. Convert to meters.
        voxel_size_m = voxel_size_mm / 1000.0
        
        mod_remesh = obj.modifiers.new(name="Remesh", type='REMESH')
        mod_remesh.mode = 'VOXEL'
        mod_remesh.voxel_size = voxel_size_m
        mod_remesh.adaptivity = 0.0 # Uniform voxels for best quality
        
        try:
            bpy.ops.object.modifier_apply(modifier="Remesh")
        except Exception as e:
            print(f"[WARNING] Remesh failed (mesh might be empty or too small): {e}")

        # 5. Post-Smooth (Only if remeshed, to remove voxel aliasing)
        mod_smooth = obj.modifiers.new(name="Smooth", type='SMOOTH')
        mod_smooth.factor = 0.5
        mod_smooth.iterations = 10
        bpy.ops.object.modifier_apply(modifier="Smooth")

        # Recalculate normals after remesh/smooth
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.normals_make_consistent(inside=False)
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception as e:
            print(f"[WARNING] Failed to recalculate normals: {e}")
    else:
        print("[INFO] Skipping Voxel Remesh (preserving original topology)")

    # 6. Decimate (Optimize for printing/slicing)
    # Use a conservative, size-aware default: only decimate if face count is huge.
    face_count = len(obj.data.polygons)
    if decimate_ratio is None:
        if profile == "resin-mini":
            # Keep more detail for minis; decimate only when extremely dense.
            decimate_ratio = 0.35 if face_count > 2_000_000 else None
        else:
            decimate_ratio = 0.2

    if decimate_ratio is not None:
        mod_dec = obj.modifiers.new(name="Decimate", type='DECIMATE')
        mod_dec.ratio = float(decimate_ratio)
        bpy.ops.object.modifier_apply(modifier="Decimate")
    
    print(f"[INFO] Final Vertex Count: {len(obj.data.vertices)}")
    
    # 7. Export STL
    # Using the new Blender 4.2+ API
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=output_path, export_selected_objects=True)
    else:
        # Fallback for older versions if needed, though we know user has 4.2
        bpy.ops.export_mesh.stl(filepath=output_path, use_selection=True)
        
    print(f"[SUCCESS] Exported to {output_path}")

if __name__ == "__main__":
    # Handle args
    try:
        idx = sys.argv.index("--")
        args_list = sys.argv[idx+1:]
    except ValueError:
        args_list = []
        
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--height_mm", type=float, default=100.0, help="Target height in mm")
    parser.add_argument("--voxel_size_mm", type=float, default=0.1, help="Voxel detail size in mm")
    parser.add_argument(
        "--profile",
        type=str,
        default="default",
        choices=["default", "resin-mini"],
        help="Print profile preset. 'resin-mini' targets 28–35mm resin minis.",
    )
    parser.add_argument(
        "--decimate_ratio",
        type=float,
        default=None,
        help="Override decimate ratio (0-1). Default depends on profile and face count.",
    )
    parser.add_argument("--skip_remesh", action="store_true", help="Skip voxel remeshing (preserve original topology)")
    
    args = parser.parse_args(args_list)
    
    cleanup_scene()
    process_mesh(args.mesh, args.output, args.height_mm, args.voxel_size_mm, profile=args.profile, decimate_ratio=args.decimate_ratio, skip_remesh=args.skip_remesh)
