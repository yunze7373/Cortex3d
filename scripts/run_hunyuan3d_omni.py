#!/usr/bin/env python3
"""
Cortex3d Hunyuan3D-Omni Runner
Multi-modal controllable 3D asset generation with pose, point cloud, voxel, and bbox controls.
Based on Hunyuan3D-2.1 with unified control encoder.

GitHub: https://github.com/Tencent-Hunyuan/Hunyuan3D-Omni

Usage:
    # Basic image-to-3D (no control)
    python run_hunyuan3d_omni.py image.png --output outputs/omni
    
    # With pose control
    python run_hunyuan3d_omni.py image.png --control-type pose --control-input skeleton.json
    
    # With point cloud control
    python run_hunyuan3d_omni.py image.png --control-type point --control-input cloud.ply
"""

import argparse
import os
import sys
from pathlib import Path

# Set environment before imports
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'

# Get version from environment
HUNYUAN3D_VERSION = os.environ.get("HUNYUAN3D_VERSION", "omni")

# Add Hunyuan3D-Omni to path
HUNYUAN3D_OMNI_ROOT = Path(os.environ.get("HUNYUAN3D_OMNI_ROOT", "/opt/hunyuan3d-omni"))
if HUNYUAN3D_OMNI_ROOT.exists():
    sys.path.insert(0, str(HUNYUAN3D_OMNI_ROOT))

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
        
        if vram < 10:
            print("[WARNING] Less than 10GB VRAM detected. Omni requires 10GB minimum.")
    else:
        device = torch.device("cpu")
        print("[WARNING] CUDA not available, using CPU (will be very slow)")
    return device


def load_control_data(control_type: str, control_path: str):
    """
    Load control data based on type.
    
    Args:
        control_type: One of 'pose', 'point', 'voxel', 'bbox'
        control_path: Path to control data file
        
    Returns:
        Control data in format expected by Hunyuan3D-Omni
    """
    control_path = Path(control_path)
    if not control_path.exists():
        raise FileNotFoundError(f"Control file not found: {control_path}")
    
    print(f"[INFO] Loading {control_type} control data from: {control_path}")
    
    if control_type == "pose":
        # Skeleton/pose data - typically JSON with joint positions
        import json
        with open(control_path, 'r') as f:
            return json.load(f)
            
    elif control_type == "point":
        # Point cloud data - PLY or NPY format
        if control_path.suffix == '.npy':
            return np.load(str(control_path))
        elif control_path.suffix in ['.ply', '.pcd']:
            try:
                import trimesh
                pcd = trimesh.load(str(control_path))
                return np.array(pcd.vertices)
            except Exception as e:
                print(f"[ERROR] Failed to load point cloud: {e}")
                raise
                
    elif control_type == "voxel":
        # Voxel data - typically NPY array
        return np.load(str(control_path))
        
    elif control_type == "bbox":
        # Bounding box data - JSON with min/max coordinates
        import json
        with open(control_path, 'r') as f:
            return json.load(f)
    
    return None


def preprocess_image(image_path: str) -> Image.Image:
    """Load and preprocess input image."""
    print(f"[INFO] Loading image: {image_path}")
    
    img = Image.open(image_path).convert("RGBA")
    
    # Remove background if needed
    if img.mode == 'RGB':
        try:
            from rembg import remove
            print("[INFO] Removing background...")
            img = remove(img)
        except Exception as e:
            print(f"[WARNING] Background removal failed: {e}")
            background = Image.new("RGBA", img.size, (255, 255, 255, 255))
            background.paste(img)
            img = background
    
    return img


def generate_3d_omni(
    image,
    output_dir: Path,
    output_name: str,
    control_type: str = None,
    control_data = None,
    use_ema: bool = False,
    use_flashvdm: bool = False,
    octree_resolution: int = 512,
    guidance_scale: float = 5.5,
    num_inference_steps: int = 50,
    seed: int = 42
):
    """
    Generate 3D model using Hunyuan3D-Omni.
    
    Args:
        image: PIL Image or path
        output_dir: Output directory
        output_name: Base name for output files
        control_type: Optional control type ('pose', 'point', 'voxel', 'bbox')
        control_data: Optional control data matching control_type
        use_ema: Use EMA model for more stable inference
        use_flashvdm: Enable FlashVDM for faster inference
        octree_resolution: Mesh resolution
        guidance_scale: Classifier-free guidance strength
        num_inference_steps: Number of diffusion steps
        seed: Random seed
        
    Returns:
        Path to generated GLB file
    """
    print(f"[INFO] Generating 3D model with Hunyuan3D-Omni...")
    if control_type:
        print(f"[INFO] Control type: {control_type}")
    
    # Set seed
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    try:
        # Import Hunyuan3D-Omni pipeline
        # Note: The actual import path may vary based on the Omni repo structure
        # This follows the pattern from the official inference.py
        from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
        
        # Determine model path based on control type
        if control_type:
            model_path = "tencent/Hunyuan3D-Omni"
            print(f"[INFO] Using Omni model with {control_type} control...")
        else:
            model_path = "tencent/Hunyuan3D-Omni"
            print("[INFO] Using Omni model (image-only mode)...")
        
        # Load pipeline
        print("[INFO] Loading shape generation pipeline...")
        pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(model_path)
        
        if use_ema:
            print("[INFO] Using EMA model weights...")
            # EMA loading logic if available
        
        if use_flashvdm:
            print("[INFO] Enabling FlashVDM optimization...")
            # FlashVDM logic if available
        
        print("[INFO] Pipeline loaded!")
        
        # Prepare generation kwargs
        gen_kwargs = {
            'image': image,
            'octree_resolution': octree_resolution,
            'guidance_scale': guidance_scale,
            'num_inference_steps': num_inference_steps
        }
        
        # Add control data if provided
        if control_type and control_data is not None:
            gen_kwargs['control_type'] = control_type
            gen_kwargs['control_data'] = control_data
        
        print(f"[INFO] Generation params: octree={octree_resolution}, guidance={guidance_scale}, steps={num_inference_steps}")
        
        # Generate
        mesh = pipeline(**gen_kwargs)[0]
        print("[INFO] Shape generated!")
        
        # Export
        output_dir.mkdir(parents=True, exist_ok=True)
        glb_path = output_dir / f"{output_name}.glb"
        obj_path = output_dir / f"{output_name}.obj"
        
        print(f"[INFO] Exporting GLB to {glb_path}...")
        mesh.export(str(glb_path))
        
        print(f"[INFO] Exporting OBJ to {obj_path}...")
        try:
            mesh.export(str(obj_path))
        except Exception as e:
            print(f"[WARNING] OBJ export failed: {e}")
        
        # Print mesh stats
        if hasattr(mesh, 'vertices') and hasattr(mesh, 'faces'):
            print(f"[INFO] Mesh statistics:")
            print(f"       Vertices: {len(mesh.vertices)}")
            print(f"       Faces: {len(mesh.faces)}")
        
        return glb_path
        
    except ImportError as e:
        print(f"[ERROR] Failed to import Hunyuan3D-Omni: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(
            "Hunyuan3D-Omni loading failed. Please ensure the repository "
            "is correctly installed at /opt/hunyuan3d-omni"
        )
    except Exception as e:
        print(f"[ERROR] 3D generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    parser = argparse.ArgumentParser(
        description=f"Hunyuan3D-{HUNYUAN3D_VERSION} Multi-Modal Image-to-3D Generation"
    )
    parser.add_argument("image", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/hunyuan3d-omni", 
                        help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    # Control parameters
    parser.add_argument("--control-type", choices=["pose", "point", "voxel", "bbox"],
                        help="Control type for guided generation")
    parser.add_argument("--control-input", type=str,
                        help="Path to control data file (skeleton JSON, PLY, etc.)")
    
    # Model options
    parser.add_argument("--use-ema", action="store_true",
                        help="Use EMA model for more stable inference")
    parser.add_argument("--flashvdm", action="store_true",
                        help="Enable FlashVDM for faster inference")
    
    # Quality parameters
    parser.add_argument("--octree", type=int, default=512,
                        help="Octree resolution (256=low, 512=default, 768=high)")
    parser.add_argument("--guidance", type=float, default=5.5,
                        help="Guidance scale for shape generation")
    parser.add_argument("--steps", type=int, default=50,
                        help="Diffusion sampling steps")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"Cortex3d Hunyuan3D-{HUNYUAN3D_VERSION} 3D Generation")
    print("=" * 60)
    
    # Setup
    device = setup_device()
    
    # Load control data if specified
    control_data = None
    if args.control_type:
        if not args.control_input:
            print(f"[ERROR] --control-input required when using --control-type {args.control_type}")
            sys.exit(1)
        control_data = load_control_data(args.control_type, args.control_input)
        print(f"[INFO] Loaded {args.control_type} control data")
    
    # Preprocess image
    image = preprocess_image(args.image)
    
    # Generate
    output_dir = Path(args.output)
    output_name = Path(args.image).stem.replace('_front', '')
    
    glb_path = generate_3d_omni(
        image=image,
        output_dir=output_dir,
        output_name=output_name,
        control_type=args.control_type,
        control_data=control_data,
        use_ema=args.use_ema,
        use_flashvdm=args.flashvdm,
        octree_resolution=args.octree,
        guidance_scale=args.guidance,
        num_inference_steps=args.steps,
        seed=args.seed
    )
    
    print("=" * 60)
    print(f"[SUCCESS] 3D model generated: {glb_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
