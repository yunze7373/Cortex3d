#!/usr/bin/env python3
"""
Cortex3d Stage 3 - Semantic Detail Generation
Use Marigold (LCM) to generate high-precision 16-bit Displacement Maps.
"""

import argparse
import logging
import os
import sys
import torch
import numpy as np
from PIL import Image
from pathlib import Path

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_pipeline():
    """Load Marigold Pipeline"""
    logging.info("Loading Marigold Depth LCM Pipeline...")
    try:
        from diffusers import MarigoldDepthPipeline
        
        # Use LCM version for speed (1-4 steps instead of 50)
        pipe = MarigoldDepthPipeline.from_pretrained(
            "prs-eth/marigold-depth-lcm-v1-0",
            torch_dtype=torch.float16
        )
        if torch.cuda.is_available():
            pipe.to("cuda")
            logging.info("Pipeline loaded on CUDA")
        elif torch.backends.mps.is_available():
            pipe.to("mps")
            logging.info("Pipeline loaded on MPS (Mac)")
        else:
            pipe.to("cpu")
            logging.warning("Pipeline loaded on CPU (Slow!)")
            
        return pipe
    except ImportError as e:
        logging.error(f"Failed to import diffusers or Marigold pipeline: {e}")
        logging.error("Check if 'diffusers' >= 0.28.0 is installed.")
        # Try to debug imports
        try:
            import diffusers
            logging.info(f"Diffusers version: {diffusers.__version__}")
        except ImportError:
            logging.error("Diffusers package not found at all.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during pipeline loading: {e}")
        sys.exit(1)

def process_image(pipe, image_path, output_dir):
    """Run Inference"""
    logging.info(f"Processing {image_path}...")
    
    image = Image.open(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run Marigold
    # LCM version usually good with 4 steps
    pipeline_output = pipe(
        image,
        num_inference_steps=4,
        ensemble_size=1,
        match_input_resolution=False,
        output_type="np",  # Request numpy output directly
    )
    
    # Marigold output attribute is 'prediction'
    if hasattr(pipeline_output, "prediction"):
        depth_pred = pipeline_output.prediction
    else:
        # Fallback/Debug
        logging.error(f"Unknown output format. Attributes: {dir(pipeline_output)}")
        sys.exit(1)
        
    # Squeeze dimensions: (1, 1, H, W) -> (H, W)
    depth_pred = depth_pred.squeeze()
    
    # Ensure it's 2D
    if len(depth_pred.shape) != 2:
        logging.error(f"Unexpected depth map shape: {depth_pred.shape}")
        sys.exit(1)
    
    # Save as 16-bit PNG (or EXR if needed, but PNG is easier for Blender)
    # Marigold output is normalized 0-1.
    # To save as 16-bit PNG: scale to 0-65535 and cast to uint16
    
    depth_uint16 = (depth_pred * 65535.0).astype(np.uint16)
    
    filename = image_path.stem
    output_path = output_dir / f"{filename}_displacement.png"
    
    Image.fromarray(depth_uint16).save(output_path, mode="I;16")
    logging.info(f"Saved 16-bit displacement map: {output_path}")

    # Optional: Save visualization if available
    if hasattr(pipeline_output, "depth_colored"):
         vis_path = output_dir / f"{filename}_vis.png"
         pipeline_output.depth_colored.save(vis_path)
         logging.info(f"Saved visualization: {vis_path}")

def main():
    parser = argparse.ArgumentParser(description="Stage 3: Detail Generation (Marigold)")
    parser.add_argument("image", type=Path, help="Input image path")
    parser.add_argument("--output_dir", type=Path, default="outputs/stage3", help="Output directory")
    
    args = parser.parse_args()
    
    if not args.image.exists():
        logging.error(f"File not found: {args.image}")
        sys.exit(1)
        
    pipe = setup_pipeline()
    process_image(pipe, args.image, args.output_dir)

if __name__ == "__main__":
    main()
