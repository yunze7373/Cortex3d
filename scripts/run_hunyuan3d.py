#!/usr/bin/env python3
"""
Cortex3d Hunyuan3D-2.0 Runner
Uses Tencent Hunyuan3D-2.0 for high-quality image-to-3D generation.

Supports both single-view and multi-view input:
- Single-view: Uses one front image
- Multi-view: Uses multiple images (front, back, left, right) for better accuracy

Usage:
    # Single view
    python run_hunyuan3d.py test_images/character_front.png --output outputs/hunyuan3d
    
    # Multi-view (auto-detect)
    python run_hunyuan3d.py test_images/character --multiview --output outputs/hunyuan3d
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

# Set environment before imports
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'

# Add Hunyuan3D to path
HUNYUAN3D_ROOT = Path(os.environ.get("HUNYUAN3D_ROOT", "/opt/hunyuan3d"))
if HUNYUAN3D_ROOT.exists():
    sys.path.insert(0, str(HUNYUAN3D_ROOT))

import torch
import numpy as np
from PIL import Image


def setup_device():
    """Setup compute device."""
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"[INFO] Using GPU: {torch.cuda.get_device_name(0)}")
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"[INFO] VRAM: {vram:.1f} GB")
        
        if vram < 12:
            print("[WARNING] Less than 12GB VRAM detected. Texture generation may be limited.")
    else:
        device = torch.device("cpu")
        print("[WARNING] CUDA not available, using CPU (will be very slow)")
    return device


def load_hunyuan3d_pipeline(model_type="lite", multiview=False):
    """
    Load Hunyuan3D-2.0 pipeline.
    
    Args:
        model_type: "lite" (shape only, 6GB) or "full" (shape+texture, 12-16GB)
        multiview: If True, load the multi-view model (hunyuan3d-dit-v2-mv)
    
    Returns:
        (shape_pipeline, texture_pipeline)
    """
    mv_suffix = " [Multi-View]" if multiview else " [Single-View]"
    print(f"[INFO] Loading Hunyuan3D-2.0 model (type: {model_type}){mv_suffix}...")
    
    try:
        # Import Hunyuan3D components
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
        
        # Select model path and subfolder based on multiview
        if multiview:
            # Multi-view model is in separate repo
            model_path = 'tencent/Hunyuan3D-2mv'
            subfolder = 'hunyuan3d-dit-v2-mv'
            print(f"[INFO] Using multi-view model: {model_path}/{subfolder}")
        else:
            # Single-view model
            model_path = 'tencent/Hunyuan3D-2'
            subfolder = 'hunyuan3d-dit-v2-0'
            print(f"[INFO] Using single-view model: {model_path}/{subfolder}")
        
        # Load shape generator
        print("[INFO] Loading shape generation pipeline...")
        shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            model_path,
            subfolder=subfolder
        )
        print("[INFO] Shape pipeline loaded!")
        
        texture_pipeline = None
        if model_type == "full":
            try:
                from hy3dgen.texgen import Hunyuan3DPaintPipeline
                print("[INFO] Loading texture generation pipeline...")
                # Texture models (delight, paint) are in main Hunyuan3D-2 repo, not 2mv
                texture_model_path = 'tencent/Hunyuan3D-2'
                texture_pipeline = Hunyuan3DPaintPipeline.from_pretrained(texture_model_path)
                print("[INFO] Texture pipeline loaded!")
            except Exception as e:
                print(f"[WARNING] Could not load texture pipeline: {e}")
                print("[INFO] Will generate shape only.")
        
        print("[INFO] Hunyuan3D-2.0 pipeline loaded successfully!")
        return shape_pipeline, texture_pipeline
        
    except ImportError as e:
        print(f"[ERROR] Failed to import Hunyuan3D: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(
            "Hunyuan3D loading failed. Please ensure the repository "
            "is correctly installed at /opt/hunyuan3d"
        )


def find_multiview_images(input_prefix: str) -> dict:
    """
    Find multi-view images based on input prefix.
    
    Args:
        input_prefix: Path prefix like "test_images/xxx" or "test_images/xxx_front.png"
    
    Returns:
        Dict with keys 'front', 'back', 'left', 'right' and PIL Image values
    """
    prefix = input_prefix.replace('_front.png', '').replace('_front', '')
    prefix_path = Path(prefix)
    parent = prefix_path.parent
    stem = prefix_path.name
    
    views = {}
    view_names = ['front', 'back', 'left', 'right']
    
    for view in view_names:
        # Try different patterns
        patterns = [
            parent / f"{stem}_{view}.png",
            parent / f"{stem}_{view}.jpg",
            parent / f"{stem}_{view}.jpeg",
        ]
        
        for pattern in patterns:
            if pattern.exists():
                views[view] = pattern
                break
    
    print(f"[INFO] Found {len(views)} views: {list(views.keys())}")
    return views


def preprocess_image(image_path: str) -> Image.Image:
    """Load and preprocess input image."""
    print(f"[INFO] Loading image: {image_path}")
    
    img = Image.open(image_path).convert("RGBA")
    
    # Remove background if needed (for RGB images)
    if img.mode == 'RGB':
        try:
            from hy3dgen.rembg import BackgroundRemover
            print("[INFO] Removing background...")
            rembg = BackgroundRemover()
            img = rembg(img)
        except Exception as e:
            print(f"[WARNING] Background removal failed: {e}")
            background = Image.new("RGBA", img.size, (255, 255, 255, 255))
            background.paste(img)
            img = background
    
    return img


def preprocess_multiview_images(view_paths: dict) -> dict:
    """
    Load and preprocess multiple view images.
    Returns dict with view tags as keys (required by Hunyuan3D-2mv API).
    """
    images = {}
    
    for view, path in view_paths.items():
        img = preprocess_image(str(path))
        images[view] = img
        print(f"[INFO] Loaded {view} view: {path}")
    
    if len(images) < 2:
        raise ValueError(f"Multi-view requires at least 2 views, but only found {len(images)}")
    
    print(f"[INFO] Total views loaded: {len(images)}")
    return images


def generate_3d(
    shape_pipeline,
    texture_pipeline,
    images,  # Single image or list of images
    output_dir: Path,
    output_name: str,
    seed: int = 42,
    multiview: bool = False
):
    """
    Generate 3D model from image(s).
    
    Args:
        shape_pipeline: Hunyuan3D shape pipeline
        texture_pipeline: Hunyuan3D texture pipeline (optional)
        images: Single PIL image or list of PIL images for multi-view
        output_dir: output directory
        output_name: base name for output files
        seed: random seed
        multiview: Whether using multi-view mode
    
    Returns:
        Path to generated GLB file
    """
    mode_str = "multi-view" if multiview else "single-view"
    print(f"[INFO] Generating 3D shape ({mode_str})...")
    
    # Set seed for reproducibility
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    try:
        # Generate shape
        if multiview and isinstance(images, dict):
            # Multi-view: pass dict of images with view tags
            print(f"[INFO] Using {len(images)} views for generation: {list(images.keys())}")
            mesh = shape_pipeline(image=images)[0]
        else:
            # Single-view: pass single image
            mesh = shape_pipeline(image=images)[0]
        
        print(f"[INFO] Shape generated!")
        
        # Apply texture if available
        if texture_pipeline is not None:
            print("[INFO] Generating texture...")
            # For texture, use the front view
            ref_image = images.get('front', list(images.values())[0]) if isinstance(images, dict) else images
            mesh = texture_pipeline(mesh, image=ref_image)
            print("[INFO] Texture applied!")
        
        # Export
        output_dir.mkdir(parents=True, exist_ok=True)
        glb_path = output_dir / f"{output_name}.glb"
        obj_path = output_dir / f"{output_name}.obj"
        
        print(f"[INFO] Exporting GLB to {glb_path}...")
        mesh.export(str(glb_path))
        
        # Also export OBJ
        print(f"[INFO] Exporting OBJ to {obj_path}...")
        try:
            mesh.export(str(obj_path))
        except Exception as e:
            print(f"[WARNING] OBJ export failed: {e}")
        
        # Print mesh statistics
        if hasattr(mesh, 'vertices') and hasattr(mesh, 'faces'):
            print(f"[INFO] Mesh statistics:")
            print(f"       Vertices: {len(mesh.vertices)}")
            print(f"       Faces: {len(mesh.faces)}")
        
        return glb_path
        
    except Exception as e:
        print(f"[ERROR] 3D generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    parser = argparse.ArgumentParser(description="Hunyuan3D-2.0 Image-to-3D Generation")
    parser.add_argument("image", type=str, help="Input image path (or prefix for multi-view)")
    parser.add_argument("--output", "-o", type=str, default="outputs/hunyuan3d", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--model", choices=["lite", "full"], default="full", 
                        help="Model type: lite (shape only, 6GB) or full (shape+texture, 12-16GB)")
    parser.add_argument("--multiview", "-mv", action="store_true",
                        help="Enable multi-view mode: use front/back/left/right images")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Cortex3d Hunyuan3D-2.0 3D Generation")
    print("=" * 60)
    
    # Setup
    device = setup_device()
    
    # Determine if multi-view based on available images
    multiview = args.multiview
    
    if multiview:
        # Find multi-view images
        view_paths = find_multiview_images(args.image)
        if len(view_paths) < 2:
            print("[WARNING] Not enough views found for multi-view. Falling back to single-view.")
            multiview = False
    
    # Load pipeline
    shape_pipeline, texture_pipeline = load_hunyuan3d_pipeline(args.model, multiview=multiview)
    
    # Preprocess images
    if multiview and len(view_paths) >= 2:
        images = preprocess_multiview_images(view_paths)
    else:
        images = preprocess_image(args.image)
    
    # Generate 3D
    output_dir = Path(args.output)
    output_name = Path(args.image).stem.replace('_front', '')
    
    glb_path = generate_3d(
        shape_pipeline, texture_pipeline,
        images, output_dir, output_name,
        seed=args.seed,
        multiview=multiview
    )
    
    print("=" * 60)
    print(f"[SUCCESS] 3D model generated: {glb_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
