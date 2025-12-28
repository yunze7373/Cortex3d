import bpy
import argparse
import sys
import bmesh

def cleanup_scene():
    """Remove all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def process_mesh(mesh_path, displacement_path, output_path, strength=0.15, voxel_size_mm=0.2):
    # 1. Import Mesh
    if mesh_path.lower().endswith('.obj'):
        bpy.ops.wm.obj_import(filepath=mesh_path)
    elif mesh_path.lower().endswith('.glb') or mesh_path.lower().endswith('.gltf'):
        bpy.ops.import_scene.gltf(filepath=mesh_path)
    else:
        print(f"[ERROR] Unsupported mesh format: {mesh_path}")
        sys.exit(1)
        
    obj = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = obj
    
    # Ensure Scale is applied (Unit scale is crucial for displacement)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    # 2. Add Subdivision Surface (Multires is better for sculpting, Subsurf for simple displace)
    # We use Subsurf + Displace modifier stack
    mod_sub = obj.modifiers.new(name="Subdivision", type='SUBSURF')
    mod_sub.levels = 4
    mod_sub.render_levels = 4
    mod_sub.subdivision_type = 'SIMPLE' # Keep shape, just add geometry
    
    # 3. Add Displacement
    # Load Texture
    try:
        img = bpy.data.images.load(displacement_path)
    except Exception as e:
        print(f"[ERROR] Could not load displacement map: {e}")
        sys.exit(1)
        
    tex = bpy.data.textures.new("DisplacementTex", 'IMAGE')
    tex.image = img
    tex.extension = 'EXTEND' 
    
    mod_disp = obj.modifiers.new(name="Displace", type='DISPLACE')
    mod_disp.texture = tex
    mod_disp.mid_level = 0.5
    mod_disp.strength = strength
    
    # 4. Remesh (Voxel) to fuse everything
    # Cortex3d logic: "Sandwich Fix" -> Displace -> Remesh -> Displace (Optional)
    # For now, we apply modifiers first
    
    # Apply modifiers
    bpy.ops.object.modifier_apply(modifier="Subdivision")
    bpy.ops.object.modifier_apply(modifier="Displace")
    
    # Voxel Remesh
    # Blender Voxel Size is in meters usually (if unit system is metric)
    # We assume model is roughly scaled. 0.2mm = 0.0002m
    # But if model is imported as "100 units = 100mm", then 0.2
    
    # Check dimensions
    dims = obj.dimensions
    z_height = dims.z
    print(f"[INFO] Model Height: {z_height} units")
    
    # Assuming the input model is normalized to ~1.0 or ~100.0
    # Cortex3d auto-scale sets it to 100mm (if using run_triposr).
    # If height is ~100, then 0.2mm is 0.2 units.
    
    target_voxel_size = voxel_size_mm
    if z_height < 5.0: # Likely normalized to 1.0
         target_voxel_size = voxel_size_mm / 100.0
         
    mod_remesh = obj.modifiers.new(name="Remesh", type='REMESH')
    mod_remesh.mode = 'VOXEL'
    mod_remesh.voxel_size = target_voxel_size
    mod_remesh.adaptivity = 0.01
    
    bpy.ops.object.modifier_apply(modifier="Remesh")
    
    # 5. Decimate (Reduce file size for printing)
    # Target ~500k faces
    mod_dec = obj.modifiers.new(name="Decimate_Final", type='DECIMATE')
    mod_dec.ratio = 0.5 # Aggressive reduction
    # Or use face count
    # mod_dec.ratio = 500000 / len(obj.data.polygons)
    
    bpy.ops.object.modifier_apply(modifier="Decimate_Final")
    
    # 6. Export STL
    bpy.ops.wm.stl_export(filepath=output_path, export_selected_objects=True)
    print(f"[SUCCESS] Exported to {output_path}")

if __name__ == "__main__":
    # Remove all args up to "--"
    try:
        idx = sys.argv.index("--")
        args_list = sys.argv[idx+1:]
    except ValueError:
        args_list = []
        
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--displacement", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--strength", type=float, default=0.15)
    parser.add_argument("--voxel_size", type=float, default=0.2)
    
    args = parser.parse_args(args_list)
    
    cleanup_scene()
    process_mesh(args.mesh, args.displacement, args.output, args.strength, args.voxel_size)
