#!/usr/bin/env python3
"""
Cortex3d TRELLIS Runner
Uses Microsoft TRELLIS for high-quality image-to-3D generation.

Usage:
    python run_trellis.py <input_image> [options]
    
Example:
    python run_trellis.py test_images/character_front.png --output outputs/trellis
"""

import argparse
import os
import sys
from pathlib import Path

# Set environment before imports
os.environ['SPCONV_ALGO'] = 'native'  # Faster for single runs
os.environ['ATTN_BACKEND'] = 'xformers'  # Force xformers to avoid flash_attn dependency logic check

# Add TRELLIS to path
TRELLIS_ROOT = Path("/opt/trellis")
if TRELLIS_ROOT.exists():
    sys.path.insert(0, str(TRELLIS_ROOT))

import torch
from PIL import Image


def setup_device():
    """Setup compute device."""
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"[INFO] Using GPU: {torch.cuda.get_device_name(0)}")
        print(f"[INFO] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        device = torch.device("cpu")
        print("[WARNING] CUDA not available, using CPU (will be slow)")
    return device


def load_trellis_pipeline(device):
    """Load TRELLIS pipeline from HuggingFace."""
    print("[INFO] Loading TRELLIS model from HuggingFace...")
    
    try:
        from trellis.pipelines import TrellisImageTo3DPipeline
        from trellis.utils import postprocessing_utils
        
        pipeline = TrellisImageTo3DPipeline.from_pretrained("microsoft/TRELLIS-image-large")
        pipeline.cuda()
        
        print("[INFO] TRELLIS pipeline loaded successfully!")
        return pipeline, postprocessing_utils
        
    except ImportError as e:
        print(f"[ERROR] Failed to import TRELLIS: {e}")
        raise RuntimeError(
            "TRELLIS loading failed. Please ensure the TRELLIS repository "
            "is correctly installed and the model weights are available."
        )


def preprocess_image(image_path: str):
    """Load and preprocess input image."""
    print(f"[INFO] Loading image: {image_path}")
    
    img = Image.open(image_path).convert("RGBA")
    
    # Create white background for transparent images
    if img.mode == "RGBA":
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img).convert("RGB")
    
    # 2. Pad to square to preserve aspect ratio
    # If we don't do this, the pipeline might force-resize to 512x512, squashing the character.
    w, h = img.size
    if w != h:
        print(f"[INFO] Image is non-square ({w}x{h}). Padding to square to preserve proportions.")
        max_dim = max(w, h)
        new_img = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
        # Center the image
        paste_x = (max_dim - w) // 2
        paste_y = (max_dim - h) // 2
        new_img.paste(img, (paste_x, paste_y))
        img = new_img
        
    print(f"[INFO] Final Image size: {img.size}")
    return img



def patch_trellis_render():
    """
    Monkey-patch TRELLIS Gaussian renderer to fix compatibility issues 
    with standard diff-gaussian-rasterization.
    """
    print("[INFO] Patching TRELLIS renderer for compatibility...")
    
    try:
        import trellis.renderers.gaussian_render as gaussian_render_module
        from trellis.representations.gaussian import Gaussian
        from easydict import EasyDict as edict
        import math
        import torch
        import numpy as np
        
        # We need to redefine the standalone 'render' function in gaussian_render.py
        def patched_render(viewpoint_camera, pc : Gaussian, pipe, bg_color : torch.Tensor, scaling_modifier = 1.0, override_color = None):
            """
            Render the scene. 
            Background tensor (bg_color) must be on GPU!
            """
            # lazy import
            if 'GaussianRasterizer' not in globals():
                from diff_gaussian_rasterization import GaussianRasterizer, GaussianRasterizationSettings

            # Create zero tensor. We will use it to make pytorch return gradients of the 2D (screen-space) means
            screenspace_points = torch.zeros_like(pc.get_xyz, dtype=pc.get_xyz.dtype, requires_grad=True, device="cuda") + 0
            try:
                screenspace_points.retain_grad()
            except:
                pass
            
            # Set up rasterization configuration
            tanfovx = math.tan(viewpoint_camera.FoVx * 0.5)
            tanfovy = math.tan(viewpoint_camera.FoVy * 0.5)

            # PATCH: Remove kernel_size and subpixel_offset which are causing issues
            # kernel_size = pipe.kernel_size
            # subpixel_offset ...

            raster_settings = GaussianRasterizationSettings(
                image_height=int(viewpoint_camera.image_height),
                image_width=int(viewpoint_camera.image_width),
                tanfovx=tanfovx,
                tanfovy=tanfovy,
                # PATCH: Removed kernel_size and subpixel_offset
                bg=bg_color,
                scale_modifier=scaling_modifier,
                viewmatrix=viewpoint_camera.world_view_transform,
                projmatrix=viewpoint_camera.full_proj_transform,
                sh_degree=pc.active_sh_degree,
                campos=viewpoint_camera.camera_center,
                prefiltered=False,
                debug=pipe.debug
            )

            rasterizer = GaussianRasterizer(raster_settings=raster_settings)

            means3D = pc.get_xyz
            means2D = screenspace_points
            opacity = pc.get_opacity

            scales = None
            rotations = None
            cov3D_precomp = None
            if pipe.compute_cov3D_python:
                cov3D_precomp = pc.get_covariance(scaling_modifier)
            else:
                scales = pc.get_scaling
                rotations = pc.get_rotation

            shs = None
            colors_precomp = None
            if override_color is None:
                if pipe.convert_SHs_python:
                    from .sh_utils import eval_sh
                    shs_view = pc.get_features.transpose(1, 2).view(-1, 3, (pc.max_sh_degree+1)**2)
                    dir_pp = (pc.get_xyz - viewpoint_camera.camera_center.repeat(pc.get_features.shape[0], 1))
                    dir_pp_normalized = dir_pp/dir_pp.norm(dim=1, keepdim=True)
                    sh2rgb = eval_sh(pc.active_sh_degree, shs_view, dir_pp_normalized)
                    colors_precomp = torch.clamp_min(sh2rgb + 0.5, 0.0)
                else:
                    shs = pc.get_features
            else:
                colors_precomp = override_color

            # Rasterize visible Gaussians to image, obtain their radii (on screen).
            # PATCH: Handle multiple return values (image, radii, depth, alpha)
            render_pkg = rasterizer(
                means3D = means3D,
                means2D = means2D,
                shs = shs,
                colors_precomp = colors_precomp,
                opacities = opacity,
                scales = scales,
                rotations = rotations,
                cov3D_precomp = cov3D_precomp
            )
            
            # Take only the first two values (image, radii)
            rendered_image = render_pkg[0]
            radii = render_pkg[1]

            # Those Gaussians that were frustum culled or had a radius of 0 were not visible.
            return edict({"render": rendered_image,
                    "viewspace_points": screenspace_points,
                    "visibility_filter" : radii > 0,
                    "radii": radii})

        # Apply the patch
        gaussian_render_module.render = patched_render
        print("[INFO] Patch applied successfully!")
        
    except Exception as e:
        print(f"[ERROR] Failed to patch TRELLIS renderer: {e}")
        # Assuming we might not need it if things are fixed upstream, but preventing crash
        pass


def main():
    parser = argparse.ArgumentParser(description="TRELLIS Image-to-3D Generation")
    parser.add_argument("image", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/trellis", help="Output directory")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument("--simplify", type=float, default=0.5, help="Mesh simplification ratio (0.5 = REMOVE 50%%, keep 50%%)")
    parser.add_argument("--texture_size", type=int, default=2048, help="Texture resolution")
    parser.add_argument("--ss_steps", type=int, default=50, help="Structure sampling steps")
    parser.add_argument("--slat_steps", type=int, default=50, help="Structure latent sampling steps")
    parser.add_argument("--ss_guidance", type=float, default=7.5, help="Structure guidance strength")
    parser.add_argument("--slat_guidance", type=float, default=7.5, help="Structure latent guidance strength")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Cortex3d TRELLIS 3D Generation")
    print("=" * 60)
    
    # Setup
    device = setup_device()
    
    # Patch TRELLIS
    patch_trellis_render()
    
    # Check VRAM
    if device.type == "cuda":

        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        if vram < 16:
            print(f"[WARNING] Low VRAM ({vram:.1f}GB). TRELLIS requires 16-24GB for best results.")
    
    # Load pipeline
    pipeline, postprocessing_utils = load_trellis_pipeline(device)
    
    # Preprocess image
    image = preprocess_image(args.image)
    
    # Generate 3D
    print(f"\n[INFO] Generating 3D model (Steps: SS={args.ss_steps}, SLAT={args.slat_steps})...")
    outputs = pipeline.run(
        image,
        seed=args.seed,
        formats=["gaussian", "mesh"],
        preprocess_image=False, # We already preprocessed
        sparse_structure_sampler_params={
            "steps": args.ss_steps,
            "cfg_strength": args.ss_guidance,
        },
        slat_sampler_params={
            "steps": args.slat_steps,
            "cfg_strength": args.slat_guidance,
        },
    )
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_name = Path(args.image).stem
    
    # Export GLB
    glb_path = output_dir / f"{image_name}.glb"
    print(f"[INFO] Exporting GLB to {glb_path}...")
    
    glb = postprocessing_utils.to_glb(
        outputs['gaussian'][0],
        outputs['mesh'][0],
        simplify=args.simplify,
        texture_size=args.texture_size,
    )
    
    # =========================================================================
    # POST-PROCESSING: Enhance Texture Quality
    # =========================================================================
    print("[INFO] Post-processing texture for photo-realism...")
    try:
        from PIL import ImageEnhance
        
        # Helper to process a PIL image
        def process_texture(pil_img):
            # 1. Brightness (Fix dark bake - CRITICAL)
            enhancer = ImageEnhance.Brightness(pil_img)
            pil_img = enhancer.enhance(1.35) # +35% Brightness (was 10%)
            
            # 2. Color/Saturation (Restore vibrancy - CRITICAL)
            enhancer = ImageEnhance.Color(pil_img)
            pil_img = enhancer.enhance(1.45) # +45% Saturation (was 20%)
            
            # 3. Contrast (Pop details)
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(1.15) # +15% Contrast (was 10%)
            
            # 4. Sharpening (Crucial for detail)
            enhancer = ImageEnhance.Sharpness(pil_img)
            pil_img = enhancer.enhance(1.3) # +30% Sharpness (was 50%)
            
            return pil_img

        # Handle both trimesh.Trimesh (single mesh) and trimesh.Scene
        # TRELLIS to_glb() returns a trimesh.Trimesh, not a Scene
        def enhance_material(mat, source_name="mesh"):
            if hasattr(mat, 'baseColorTexture') and mat.baseColorTexture is not None:
                print(f"[INFO] Enhancing baseColorTexture for: {source_name}")
                mat.baseColorTexture = process_texture(mat.baseColorTexture)
                return True
            elif hasattr(mat, 'image') and mat.image is not None:
                print(f"[INFO] Enhancing texture image for: {source_name}")
                mat.image = process_texture(mat.image)
                return True
            return False
        
        enhanced = False
        # Case 1: Single Trimesh object (returned by TRELLIS to_glb)
        if hasattr(glb, 'visual') and hasattr(glb.visual, 'material'):
            enhanced = enhance_material(glb.visual.material, "main_mesh")
        
        # Case 2: Scene with multiple geometries
        if hasattr(glb, 'geometry'):
            for geom_name, geom in glb.geometry.items():
                if hasattr(geom, 'visual') and hasattr(geom.visual, 'material'):
                    if enhance_material(geom.visual.material, geom_name):
                        enhanced = True
        
        if not enhanced:
            print("[WARNING] No texture found to enhance")
                        
    except Exception as e:
        print(f"[WARNING] Texture enhancement failed: {e}")

    glb.export(str(glb_path))
    
    # Export OBJ mesh
    obj_path = output_dir / f"{image_name}.obj"
    print(f"[INFO] Exporting OBJ to {obj_path}...")
    
    # Save mesh using trimesh
    mesh = outputs['mesh'][0]
    if hasattr(mesh, 'export'):
        mesh.export(str(obj_path))
    else:
        # Use trimesh to save
        import trimesh
        if hasattr(mesh, 'vertices') and hasattr(mesh, 'faces'):
            verts = mesh.vertices.cpu().numpy() if torch.is_tensor(mesh.vertices) else mesh.vertices
            faces = mesh.faces.cpu().numpy() if torch.is_tensor(mesh.faces) else mesh.faces
            tri_mesh = trimesh.Trimesh(vertices=verts, faces=faces)
            tri_mesh.export(str(obj_path))
    
    # Export PLY (Gaussian splatting)
    ply_path = output_dir / f"{image_name}.ply"
    print(f"[INFO] Exporting PLY to {ply_path}...")
    outputs['gaussian'][0].save_ply(str(ply_path))
    
    print("\n" + "=" * 60)
    print(f"[SUCCESS] 3D model generated!")
    print(f"  - GLB: {glb_path}")
    print(f"  - OBJ: {obj_path}")  
    print(f"  - PLY: {ply_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
