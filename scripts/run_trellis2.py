#!/usr/bin/env python3
"""
Cortex3d TRELLIS Runner
Uses Microsoft TRELLIS for high-quality image-to-3D generation.

Key Features:
- Structured Latent (SLatent) representation
- Multi-format output (mesh, gaussian, radiance field)
- High-quality geometry and texture

Usage:
    python run_trellis2.py <input_image> [options]
    
Example:
    python run_trellis2.py test_images/character_front.png --output outputs/trellis2

Note: Despite the filename 'run_trellis2.py', this uses the official TRELLIS repository.
"""

import os
import sys
import argparse
from pathlib import Path

# Memory optimization - must be set before torch import
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"

import torch
import numpy as np
from PIL import Image

# TRELLIS.2 imports (Microsoft's official TRELLIS.2 with O-Voxel)
try:
    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    from trellis2.utils import render_utils
    from trellis2.renderers import EnvMap
    from trellis2.representations import MeshWithVoxel
    import o_voxel
    TRELLIS2_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] TRELLIS.2 not available: {e}")
    TRELLIS2_AVAILABLE = False


def setup_device():
    """Setup compute device."""
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"[INFO] Using CUDA device: {torch.cuda.get_device_name(0)}")
        print(f"[INFO] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        device = torch.device("cpu")
        print("[WARNING] CUDA not available, using CPU (will be very slow)")
    return device


def load_pipeline(model_name: str = "microsoft/TRELLIS.2-4B"):
    """Load TRELLIS.2 pipeline (Image-to-3D with O-Voxel)."""
    print(f"[INFO] Loading TRELLIS.2 pipeline: {model_name}")
    print("[INFO] This may take a while on first run (downloading model weights)...")
    
    pipeline = Trellis2ImageTo3DPipeline.from_pretrained(model_name)
    pipeline.cuda()
    
    print("[INFO] Pipeline loaded successfully!")
    return pipeline


def load_envmap(hdri_path: str = None):
    """Load environment map for PBR rendering."""
    import cv2
    
    # Default HDRI paths to try (TRELLIS may not include HDRI assets)
    hdri_paths = [
        hdri_path,
        "/workspace/assets/hdri/forest.exr",
        "/opt/trellis2/assets/example_image/T.png",  # Fallback to example
        "assets/hdri/forest.exr",
    ]
    
    for path in hdri_paths:
        if path and os.path.exists(path):
            print(f"[INFO] Loading environment map: {path}")
            hdri = cv2.imread(path, cv2.IMREAD_UNCHANGED)
            if hdri is not None:
                hdri = cv2.cvtColor(hdri, cv2.COLOR_BGR2RGB)
                envmap = EnvMap(torch.tensor(hdri, dtype=torch.float32, device='cuda'))
                return envmap
    
    print("[WARNING] No environment map found, PBR rendering may look different")
    return None


def preprocess_image(image_path: str) -> Image.Image:
    """Load and preprocess input image."""
    print(f"[INFO] Loading image: {image_path}")
    
    image = Image.open(image_path)
    
    # Convert to RGBA if needed
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    
    # Resize if too large (memory constraint)
    max_size = 1024
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.LANCZOS)
        print(f"[INFO] Resized to {new_size}")
    
    return image


def generate_3d(
    pipeline,
    image: Image.Image,
    output_dir: Path,
    output_name: str,
    envmap=None,
    decimation_target: int = 500000,
    texture_size: int = 2048,
    seed: int = 42
):
    """
    Generate 3D model from image using TRELLIS.2.
    
    Args:
        pipeline: TRELLIS.2 pipeline
        image: Input PIL image
        output_dir: Output directory
        output_name: Base name for output files
        envmap: Environment map for PBR rendering
        decimation_target: Target face count for mesh simplification
        texture_size: Texture resolution
        seed: Random seed
    
    Returns:
        Path to generated GLB file
    """
    print(f"[INFO] Generating 3D model with TRELLIS.2...")
    
    # Set seed
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    # Generate (using TRELLIS.2 pipeline API)
    with torch.inference_mode():
        mesh = pipeline.run(
            image,
            seed=seed,
            preprocess_image=False  # We already preprocessed
        )[0]  # Returns list of MeshWithVoxel
    
    print(f"[INFO] 3D model generated!")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export to GLB using TRELLIS.2 O-Voxel postprocessing
    glb_path = output_dir / f"{output_name}.glb"
    print(f"[INFO] Exporting GLB to {glb_path}...")
    
    # Simplify mesh (nvdiffrast limit)
    mesh.simplify(16777216)
    
    # Use TRELLIS.2's O-Voxel GLB export
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices,
        faces=mesh.faces,
        attr_volume=mesh.attrs,
        coords=mesh.coords,
        attr_layout=mesh.layout,
        voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=decimation_target,
        texture_size=texture_size,
        remesh=True,
        remesh_band=1,
        remesh_project=0,
        verbose=True
    )
    glb.export(str(glb_path), extension_webp=True)
    print(f"[INFO] GLB exported: {glb_path}")
    
    # Also export OBJ for compatibility
    obj_path = output_dir / f"{output_name}.obj"
    try:
        import trimesh
        # Load the GLB we just exported
        scene = trimesh.load(str(glb_path))
        if isinstance(scene, trimesh.Scene):
            # Combine all meshes
            combined = trimesh.util.concatenate(list(scene.geometry.values()))
        else:
            combined = scene
        combined.export(str(obj_path))
        print(f"[INFO] OBJ exported: {obj_path}")
    except Exception as e:
        print(f"[WARNING] OBJ export failed: {e}")
    
    # Render preview video with PBR materials
    try:
        import imageio
        video_path = output_dir / f"{output_name}_preview.mp4"
        print(f"[INFO] Rendering preview video with PBR materials...")
        
        # Render with environment map if available
        if envmap is not None:
            video_frames = render_utils.render_video(mesh, envmap=envmap)
            video = render_utils.make_pbr_vis_frames(video_frames)
        else:
            video_frames = render_utils.render_video(mesh)
            video = video_frames['color']
        
        imageio.mimsave(str(video_path), video, fps=15)
        print(f"[INFO] Preview video saved: {video_path}")
    except Exception as e:
        print(f"[WARNING] Video rendering failed: {e}")
    
    # Print stats
    print(f"\n[INFO] Output Statistics:")
    print(f"  GLB: {glb_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    return glb_path


def main():
    parser = argparse.ArgumentParser(description="TRELLIS.2 Image-to-3D Generation")
    parser.add_argument("image", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/trellis2",
                        help="Output directory")
    parser.add_argument("--model", type=str, default="microsoft/TRELLIS.2-4B",
                        help="Model name/path (e.g., microsoft/TRELLIS-image-large)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--decimation", type=int, default=500000,
                        help="Target face count for mesh simplification")
    parser.add_argument("--texture-size", type=int, default=2048,
                        help="Texture resolution (1024, 2048, 4096)")
    parser.add_argument("--hdri", type=str, default=None,
                        help="Path to HDRI for PBR rendering")
    
    args = parser.parse_args()
    
    if not TRELLIS2_AVAILABLE:
        print("[ERROR] TRELLIS is not installed. Please run in the trellis2 Docker container.")
        sys.exit(1)
    
    print("=" * 60)
    print("Cortex3d TRELLIS 3D Generation")
    print("High Quality | Structured Latents | Multi-Format Output")
    print("=" * 60)
    
    # Setup
    device = setup_device()
    
    # Load pipeline
    pipeline = load_pipeline(args.model)
    
    # Load environment map
    envmap = load_envmap(args.hdri)
    
    # Load image
    image = preprocess_image(args.image)
    
    # Generate
    output_dir = Path(args.output)
    output_name = Path(args.image).stem
    if output_name.endswith('_front'):
        output_name = output_name[:-6]
    
    glb_path = generate_3d(
        pipeline, image, output_dir, output_name,
        envmap=envmap,
        decimation_target=args.decimation,
        texture_size=args.texture_size,
        seed=args.seed
    )
    
    print("=" * 60)
    print(f"[SUCCESS] 3D model generated: {glb_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
