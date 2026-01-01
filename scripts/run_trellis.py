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
    
    print(f"[INFO] Image size: {img.size}")
    return img


def main():
    parser = argparse.ArgumentParser(description="TRELLIS Image-to-3D Generation")
    parser.add_argument("image", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/trellis", help="Output directory")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument("--simplify", type=float, default=0.95, help="Mesh simplification ratio")
    parser.add_argument("--texture_size", type=int, default=1024, help="Texture resolution")
    
    args = parser.parse_args()
    
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
    pipeline, postprocessing_utils = load_trellis_pipeline(device)
    
    # Preprocess image
    image = preprocess_image(args.image)
    
    # Generate 3D
    print("\n[INFO] Generating 3D model...")
    outputs = pipeline.run(
        image,
        seed=args.seed,
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
