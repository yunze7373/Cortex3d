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


def load_hunyuan3d_pipeline(device, model_type="lite"):
    """
    Load Hunyuan3D-2.0 pipeline.
    
    Args:
        device: torch device
        model_type: "lite" (shape only, 6GB) or "full" (shape+texture, 12-16GB)
    
    Returns:
        pipeline object
    """
    print(f"[INFO] Loading Hunyuan3D-2.0 model (type: {model_type})...")
    
    try:
        # Import Hunyuan3D components
        from hy3dgen.shapegen import ShapeGenerator
        
        # Load shape generator
        shape_generator = ShapeGenerator.from_pretrained("tencent/Hunyuan3D-2")
        shape_generator.to(device)
        
        texture_generator = None
        if model_type == "full":
            try:
                from hy3dgen.texgen import TextureGenerator
                texture_generator = TextureGenerator.from_pretrained("tencent/Hunyuan3D-2")
                texture_generator.to(device)
                print("[INFO] Texture generator loaded!")
            except Exception as e:
                print(f"[WARNING] Could not load texture generator: {e}")
                print("[INFO] Will generate shape only.")
        
        print("[INFO] Hunyuan3D-2.0 pipeline loaded successfully!")
        return shape_generator, texture_generator
        
    except ImportError as e:
        print(f"[ERROR] Failed to import Hunyuan3D: {e}")
        raise RuntimeError(
            "Hunyuan3D loading failed. Please ensure the repository "
            "is correctly installed at /opt/hunyuan3d"
        )


def preprocess_image(image_path: str, target_size: int = 512):
    """Load and preprocess input image."""
    print(f"[INFO] Loading image: {image_path}")
    
    img = Image.open(image_path).convert("RGBA")
    
    # Create white background for transparent images
    if img.mode == "RGBA":
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img).convert("RGB")
    
    # Resize to target size while maintaining aspect ratio
    w, h = img.size
    if max(w, h) != target_size:
        ratio = target_size / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        print(f"[INFO] Resized to: {new_size}")
    
    # Pad to square
    w, h = img.size
    if w != h:
        size = max(w, h)
        new_img = Image.new("RGB", (size, size), (255, 255, 255))
        new_img.paste(img, ((size - w) // 2, (size - h) // 2))
        img = new_img
        print(f"[INFO] Padded to square: {size}x{size}")
    
    return img


def generate_3d(
    shape_generator,
    texture_generator,
    image: Image.Image,
    output_dir: Path,
    output_name: str,
    seed: int = 42
):
    """
    Generate 3D model from image.
    
    Args:
        shape_generator: Hunyuan3D shape generator
        texture_generator: Hunyuan3D texture generator (optional)
        image: preprocessed PIL image
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
        # Generate shape
        mesh = shape_generator(
            image,
            num_inference_steps=50,
            guidance_scale=7.5,
        )
        
        print(f"[INFO] Shape generated!")
        
        # Apply texture if available
        if texture_generator is not None:
            print("[INFO] Generating texture...")
            mesh = texture_generator(
                mesh,
                image,
                texture_size=2048,
            )
            print("[INFO] Texture applied!")
        
        # Export GLB
        output_dir.mkdir(parents=True, exist_ok=True)
        glb_path = output_dir / f"{output_name}.glb"
        obj_path = output_dir / f"{output_name}.obj"
        
        print(f"[INFO] Exporting GLB to {glb_path}...")
        mesh.export(str(glb_path))
        
        # Also export OBJ
        print(f"[INFO] Exporting OBJ to {obj_path}...")
        mesh.export(str(obj_path))
        
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
    shape_gen, texture_gen = load_hunyuan3d_pipeline(device, args.model)
    
    # Preprocess image
    image = preprocess_image(args.image)
    
    # Generate 3D
    output_dir = Path(args.output)
    output_name = Path(args.image).stem
    
    glb_path = generate_3d(
        shape_gen, texture_gen,
        image, output_dir, output_name,
        seed=args.seed
    )
    
    print("=" * 60)
    print(f"[SUCCESS] 3D model generated: {glb_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
