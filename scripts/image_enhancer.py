#!/usr/bin/env python3
"""
Cortex3d Image Enhancer
Enhances input images before 3D generation using:
- Real-ESRGAN for super-resolution
- GFPGAN for face enhancement

Usage:
    python image_enhancer.py input.png --output enhanced.png
    
Dependencies:
    pip install realesrgan gfpgan
"""

import argparse
import os
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# Try to import enhancement libraries
REALESRGAN_AVAILABLE = False
GFPGAN_AVAILABLE = False

try:
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet
    REALESRGAN_AVAILABLE = True
except ImportError:
    pass

try:
    from gfpgan import GFPGANer
    GFPGAN_AVAILABLE = True
except ImportError:
    pass


def get_realesrgan_model(scale=4, model_name='RealESRGAN_x4plus'):
    """Initialize Real-ESRGAN model."""
    if not REALESRGAN_AVAILABLE:
        print("[WARNING] Real-ESRGAN not available. Install with: pip install realesrgan")
        return None
    
    print(f"[INFO] Loading Real-ESRGAN model: {model_name}")
    
    # Model architecture
    if model_name == 'RealESRGAN_x4plus':
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        netscale = 4
        model_path = None  # Will be downloaded automatically
    elif model_name == 'RealESRGAN_x2plus':
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
        netscale = 2
        model_path = None
    else:
        print(f"[ERROR] Unknown model: {model_name}")
        return None
    
    upsampler = RealESRGANer(
        scale=netscale,
        model_path=model_path,
        model=model,
        tile=0,  # No tiling for smaller images
        tile_pad=10,
        pre_pad=0,
        half=True  # Use FP16 for speed
    )
    
    return upsampler


def get_gfpgan_model(upscale=2):
    """Initialize GFPGAN model for face enhancement."""
    if not GFPGAN_AVAILABLE:
        print("[WARNING] GFPGAN not available. Install with: pip install gfpgan")
        return None
    
    print("[INFO] Loading GFPGAN model for face enhancement...")
    
    face_enhancer = GFPGANer(
        model_path='https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth',
        upscale=upscale,
        arch='clean',
        channel_multiplier=2,
        bg_upsampler=None  # We handle background separately
    )
    
    return face_enhancer


def enhance_with_pil(img: Image.Image, sharpen=1.5, contrast=1.15):
    """
    Basic enhancement using PIL (fallback when AI models unavailable).
    
    Args:
        img: PIL Image
        sharpen: Sharpness factor (1.0 = original, 1.5 = +50%)
        contrast: Contrast factor (1.0 = original, 1.15 = +15%)
    
    Returns:
        Enhanced PIL Image
    """
    print("[INFO] Applying basic PIL enhancement...")
    
    # 1. Sharpen
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(sharpen)
    
    # 2. Contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    
    # 3. Unsharp mask for edge detail
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=100, threshold=3))
    
    return img


def enhance_image(
    input_path: str,
    output_path: str = None,
    use_realesrgan: bool = True,
    use_gfpgan: bool = True,
    scale: int = 2,
    target_size: int = 1024
) -> str:
    """
    Enhance an image using AI super-resolution and face enhancement.
    
    Args:
        input_path: Path to input image
        output_path: Path to save enhanced image (default: input_enhanced.png)
        use_realesrgan: Whether to use Real-ESRGAN for super-resolution
        use_gfpgan: Whether to use GFPGAN for face enhancement
        scale: Upscaling factor (2 or 4)
        target_size: Target size for the longest edge
    
    Returns:
        Path to the enhanced image
    """
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_enhanced.png"
    else:
        output_path = Path(output_path)
    
    print(f"[INFO] Enhancing image: {input_path}")
    
    # Load image
    img = Image.open(input_path).convert("RGB")
    original_size = img.size
    print(f"[INFO] Original size: {original_size}")
    
    # Convert to numpy for AI models
    img_np = np.array(img)
    
    enhanced = False
    
    # Step 1: Face enhancement with GFPGAN
    if use_gfpgan and GFPGAN_AVAILABLE:
        try:
            face_enhancer = get_gfpgan_model(upscale=scale)
            if face_enhancer is not None:
                print("[INFO] Running GFPGAN face enhancement...")
                _, _, output = face_enhancer.enhance(
                    img_np, 
                    has_aligned=False, 
                    only_center_face=False,
                    paste_back=True
                )
                if output is not None:
                    img_np = output
                    enhanced = True
                    print("[INFO] Face enhancement completed!")
        except Exception as e:
            print(f"[WARNING] GFPGAN failed: {e}")
    
    # Step 2: Super-resolution with Real-ESRGAN (if face enhancement didn't upscale)
    if use_realesrgan and REALESRGAN_AVAILABLE and not enhanced:
        try:
            model_name = f'RealESRGAN_x{scale}plus' if scale in [2, 4] else 'RealESRGAN_x4plus'
            upsampler = get_realesrgan_model(scale=scale, model_name=model_name)
            if upsampler is not None:
                print("[INFO] Running Real-ESRGAN super-resolution...")
                output, _ = upsampler.enhance(img_np, outscale=scale)
                if output is not None:
                    img_np = output
                    enhanced = True
                    print("[INFO] Super-resolution completed!")
        except Exception as e:
            print(f"[WARNING] Real-ESRGAN failed: {e}")
    
    # Convert back to PIL
    img = Image.fromarray(img_np)
    
    # Step 3: Basic PIL enhancement (always apply)
    img = enhance_with_pil(img, sharpen=1.3, contrast=1.1)
    
    # Step 4: Resize to target size if needed
    w, h = img.size
    if max(w, h) > target_size:
        ratio = target_size / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        print(f"[INFO] Resizing from {img.size} to {new_size}")
        img = img.resize(new_size, Image.LANCZOS)
    
    # Save
    img.save(output_path, quality=95)
    print(f"[SUCCESS] Enhanced image saved: {output_path}")
    print(f"[INFO] Final size: {img.size}")
    
    return str(output_path)


def enhance_for_trellis(input_path: str, output_path: str = None) -> str:
    """
    Convenience function to enhance an image specifically for TRELLIS 3D generation.
    Uses optimal settings for character generation.
    
    Args:
        input_path: Path to input image
        output_path: Optional output path
    
    Returns:
        Path to enhanced image
    """
    return enhance_image(
        input_path=input_path,
        output_path=output_path,
        use_realesrgan=True,
        use_gfpgan=True,
        scale=2,  # 2x is usually enough
        target_size=1024  # TRELLIS works best with ~1024 input
    )


def main():
    parser = argparse.ArgumentParser(description="Cortex3d Image Enhancer")
    parser.add_argument("input", type=str, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output image path")
    parser.add_argument("--scale", type=int, default=2, choices=[2, 4], help="Upscaling factor")
    parser.add_argument("--target-size", type=int, default=1024, help="Target size for longest edge")
    parser.add_argument("--no-realesrgan", action="store_true", help="Disable Real-ESRGAN")
    parser.add_argument("--no-gfpgan", action="store_true", help="Disable GFPGAN face enhancement")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Cortex3d Image Enhancer")
    print("=" * 60)
    
    # Check dependencies
    if not REALESRGAN_AVAILABLE and not args.no_realesrgan:
        print("[WARNING] Real-ESRGAN not installed. Install with: pip install realesrgan basicsr")
    if not GFPGAN_AVAILABLE and not args.no_gfpgan:
        print("[WARNING] GFPGAN not installed. Install with: pip install gfpgan")
    
    if not Path(args.input).exists():
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)
    
    enhance_image(
        input_path=args.input,
        output_path=args.output,
        use_realesrgan=not args.no_realesrgan,
        use_gfpgan=not args.no_gfpgan,
        scale=args.scale,
        target_size=args.target_size
    )


if __name__ == "__main__":
    main()
