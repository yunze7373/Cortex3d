#!/usr/bin/env python3
"""
Cortex3d Hunyuan3D-2.0 Runner
Uses Tencent Hunyuan3D-2.0 for high-quality image-to-3D generation.

This model offers significantly better detail than TRELLIS, especially for:
- Face details
- Hand/finger separation
- Fine geometric features

Usage:
    python run_hunyuan3d.py <input_image> [options]
    
Example:
    python run_hunyuan3d.py test_images/character_front.png --output outputs/hunyuan3d
"""

import argparse
import os
import sys
from pathlib import Path

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


def load_hunyuan3d_pipeline(model_type="lite"):
    """
    Load Hunyuan3D-2.0 pipeline.
    
    Args:
        model_type: "lite" (shape only, 6GB) or "full" (shape+texture, 12-16GB)
    
    Returns:
        (shape_pipeline, texture_pipeline)
    """
    print(f"[INFO] Loading Hunyuan3D-2.0 model (type: {model_type})...")
    
    try:
        # Import Hunyuan3D components - correct API from minimal_demo.py
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
        
        model_path = 'tencent/Hunyuan3D-2'
        
        # Load shape generator
        print("[INFO] Loading shape generation pipeline...")
        shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_path)
        print("[INFO] Shape pipeline loaded!")
        
        texture_pipeline = None
        if model_type == "full":
            try:
                from hy3dgen.texgen import Hunyuan3DPaintPipeline
                print("[INFO] Loading texture generation pipeline...")
                texture_pipeline = Hunyuan3DPaintPipeline.from_pretrained(model_path)
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


def preprocess_image(image_path: str):
    """Load and preprocess input image."""
    print(f"[INFO] Loading image: {image_path}")
    
    img = Image.open(image_path).convert("RGBA")
    print(f"[INFO] Original size: {img.size}, mode: {img.mode}")
    
    # Remove background if needed (for RGB images)
    if img.mode == 'RGB':
        try:
            from hy3dgen.rembg import BackgroundRemover
            print("[INFO] Removing background...")
            rembg = BackgroundRemover()
            img = rembg(img)
        except Exception as e:
            print(f"[WARNING] Background removal failed: {e}")
            # Convert to RGBA with white background
            background = Image.new("RGBA", img.size, (255, 255, 255, 255))
            background.paste(img)
            img = background
    
    return img


def generate_3d(
    shape_pipeline,
    texture_pipeline,
    image: Image.Image,
    output_dir: Path,
    output_name: str,
    seed: int = 42
):
    """
    Generate 3D model from image.
    
    Args:
        shape_pipeline: Hunyuan3D shape pipeline
        texture_pipeline: Hunyuan3D texture pipeline (optional)
        image: preprocessed PIL image (RGBA)
        output_dir: output directory
        output_name: base name for output files
        seed: random seed
    
    Returns:
        Path to generated GLB file
    """
    print("[INFO] Generating 3D shape...")
    
    # Set seed for reproducibility
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    try:
        # Generate shape - returns list of meshes
        mesh = shape_pipeline(image=image)[0]
        print(f"[INFO] Shape generated!")
        
        # Apply texture if available
        if texture_pipeline is not None:
            print("[INFO] Generating texture...")
            mesh = texture_pipeline(mesh, image=image)
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
    parser.add_argument("image", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/hunyuan3d", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--model", choices=["lite", "full"], default="full", 
                        help="Model type: lite (shape only, 6GB) or full (shape+texture, 12-16GB)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Cortex3d Hunyuan3D-2.0 3D Generation")
    print("=" * 60)
    
    # Setup
    device = setup_device()
    
    # Load pipeline
    shape_pipeline, texture_pipeline = load_hunyuan3d_pipeline(args.model)
    
    # Preprocess image
    image = preprocess_image(args.image)
    
    # Generate 3D
    output_dir = Path(args.output)
    output_name = Path(args.image).stem
    
    glb_path = generate_3d(
        shape_pipeline, texture_pipeline,
        image, output_dir, output_name,
        seed=args.seed
    )
    
    print("=" * 60)
    print(f"[SUCCESS] 3D model generated: {glb_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
