import bpy
import argparse
import sys
import bmesh
import math

def cleanup_scene():
    """Remove all objects from the scene to start fresh."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def process_mesh(mesh_path, output_path, target_height_mm=100.0, voxel_size_mm=0.1):
    """
    Imports a mesh, scales it to a specific height, remeshes it for printing, and exports to STL.
    """
    print(f"[INFO] Processing: {mesh_path}")
    
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

    # 5. Post-Smooth (To remove voxel aliasing)
    mod_smooth = obj.modifiers.new(name="Smooth", type='CORRECTIVE_SMOOTH')
    mod_smooth.iterations = 20
    mod_smooth.smooth_type = 'LENGTH_WEIGHTED'
    mod_smooth.rest_source = 'BIND' # Keep volume
    bpy.ops.object.modifier_apply(modifier="Smooth")

    # 6. Decimate (Optimize for printing/slicing)
    # Target ~500k faces or ratio 0.5 depending on density
    mod_dec = obj.modifiers.new(name="Decimate", type='DECIMATE')
    # If the mesh is super dense after remesh (0.1mm), we might need strong reduction
    # Let's target a face count if possible, or use a ratio.
    # For simplicity, ratio 0.2 usually keeps shape well after high-res remesh.
    mod_dec.ratio = 0.2 
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
    
    args = parser.parse_args(args_list)
    
    cleanup_scene()
    process_mesh(args.mesh, args.output, args.height_mm, args.voxel_size_mm)
