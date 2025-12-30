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

# Add TRELLIS to path
TRELLIS_ROOT = Path("/opt/trellis")
if TRELLIS_ROOT.exists():
    sys.path.insert(0, str(TRELLIS_ROOT))

import torch
from PIL import Image
import numpy as np


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
        # Try to import TRELLIS modules
        from trellis.pipelines import TrsImageTo3DPipeline
        
        pipeline = TrelsImageTo3DPipeline.from_pretrained(
            "microsoft/TRELLIS-image-large",
            torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
        )
        pipeline = pipeline.to(device)
        print("[INFO] TRELLIS pipeline loaded successfully!")
        return pipeline
        
    except ImportError as e:
        print(f"[ERROR] Failed to import TRELLIS: {e}")
        print("[INFO] Attempting alternative loading method...")
        
        # Alternative: Use HuggingFace diffusers-style loading if available
        try:
            from huggingface_hub import hf_hub_download
            from diffusers import DiffusionPipeline
            
            # This is a placeholder - actual TRELLIS loading may differ
            pipeline = DiffusionPipeline.from_pretrained(
                "microsoft/TRELLIS-image-large",
                torch_dtype=torch.float16,
            )
            pipeline = pipeline.to(device)
            return pipeline
        except Exception as e2:
            print(f"[ERROR] Alternative loading also failed: {e2}")
            raise RuntimeError(
                "TRELLIS loading failed. Please ensure the TRELLIS repository "
                "is correctly installed and the model weights are available."
            )


def preprocess_image(image_path: str, target_size: int = 512):
    """Load and preprocess input image."""
    print(f"[INFO] Loading image: {image_path}")
    
    img = Image.open(image_path).convert("RGBA")
    
    # Create white background for transparent images
    if img.mode == "RGBA":
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img).convert("RGB")
    
    # Resize to target size
    img = img.resize((target_size, target_size), Image.LANCZOS)
    
    print(f"[INFO] Preprocessed image: {img.size}")
    return img


def save_mesh(mesh, output_path: str):
    """Save mesh to file (OBJ or GLB)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine format from extension
    ext = output_path.suffix.lower()
    
    if hasattr(mesh, 'export'):
        # trimesh-like export
        mesh.export(str(output_path))
    elif hasattr(mesh, 'save'):
        mesh.save(str(output_path))
    else:
        # Fallback: try to extract vertices/faces and save manually
        try:
            import trimesh
            if hasattr(mesh, 'vertices') and hasattr(mesh, 'faces'):
                tri_mesh = trimesh.Trimesh(
                    vertices=mesh.vertices.cpu().numpy() if torch.is_tensor(mesh.vertices) else mesh.vertices,
                    faces=mesh.faces.cpu().numpy() if torch.is_tensor(mesh.faces) else mesh.faces,
                )
                tri_mesh.export(str(output_path))
            else:
                raise ValueError("Unknown mesh format")
        except Exception as e:
            print(f"[ERROR] Failed to save mesh: {e}")
            raise
    
    print(f"[SUCCESS] Mesh saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="TRELLIS Image-to-3D Generation")
    parser.add_argument("image", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/trellis", help="Output directory")
    parser.add_argument("--resolution", type=int, default=512, help="Generation resolution")
    parser.add_argument("--format", type=str, default="obj", choices=["obj", "glb"], help="Output format")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    # Set seed
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)
    
    print("=" * 60)
    print("Cortex3d TRELLIS 3D Generation")
    print("=" * 60)
    
    # Setup
    device = setup_device()
    
    # Check VRAM
    if device.type == "cuda":
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        if vram < 16:
            print(f"[WARNING] Low VRAM ({vram:.1f}GB). TRELLIS requires 16-24GB for best results.")
    
    # Load pipeline
    pipeline = load_trellis_pipeline(device)
    
    # Preprocess image
    image = preprocess_image(args.image, args.resolution)
    
    # Generate 3D
    print("\n[INFO] Generating 3D model...")
    with torch.no_grad():
        output = pipeline(image)
    
    # Get mesh from output
    if hasattr(output, 'mesh'):
        mesh = output.mesh
    elif hasattr(output, 'meshes'):
        mesh = output.meshes[0]
    elif isinstance(output, dict) and 'mesh' in output:
        mesh = output['mesh']
    else:
        mesh = output  # Assume output is the mesh itself
    
    # Save
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    image_name = Path(args.image).stem
    output_path = output_dir / f"{image_name}.{args.format}"
    
    save_mesh(mesh, output_path)
    
    print("\n" + "=" * 60)
    print(f"[SUCCESS] 3D model generated: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
