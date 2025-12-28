#!/usr/bin/env python3
"""
Cortex3d Stage 4 - Blender Geometry Factory
Wrapper script to launch Blender in headless mode and run the refinement script.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCRIPT_DIR = Path(__file__).parent.absolute()
BLENDER_SCRIPT_DIR = SCRIPT_DIR / "blender"
REFINEMENT_SCRIPT = BLENDER_SCRIPT_DIR / "refinement.py"

def check_blender():
    """Check if blender is in PATH"""
    try:
        subprocess.run(["blender", "--version"], check=True, capture_output=True)
        return "blender"
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Try common paths if not in PATH
        candidates = [
            "/usr/local/bin/blender",
            "/opt/blender/blender",
            "/Applications/Blender.app/Contents/MacOS/Blender",  # Mac local
            "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe" # Windows
        ]
        for c in candidates:
            if Path(c).exists():
                return c
        return None

def main():
    parser = argparse.ArgumentParser(description="Stage 4: Blender Geometry Refinement")
    parser.add_argument("--mesh", type=Path, required=True, help="Input mesh (.obj/.glb)")
    parser.add_argument("--displacement", type=Path, required=True, help="Input displacement map (.exr/.png)")
    parser.add_argument("--output", type=Path, required=True, help="Output STL path")
    parser.add_argument("--strength", type=float, default=0.15, help="Displacement strength")
    parser.add_argument("--voxel_size", type=float, default=0.2, help="Voxel remesh size (mm) - technically blender units, adjusted in script")
    
    args = parser.parse_args()
    
    executable = check_blender()
    if not executable:
        logging.error("Blender executable not found in PATH or standard locations.")
        sys.exit(1)
        
    logging.info(f"Using Blender: {executable}")
    
    if not args.mesh.exists():
        logging.error(f"Mesh not found: {args.mesh}")
        sys.exit(1)
        
    if not args.displacement.exists():
        logging.error(f"Displacement map not found: {args.displacement}")
        sys.exit(1)
        
    # Construct Blender command
    # blender -b -P refinement.py -- --mesh ...
    cmd = [
        executable,
        "--background",  # Headless
        "--python", str(REFINEMENT_SCRIPT),
        "--",  # Pass args to python script
        "--mesh", str(args.mesh.absolute()),
        "--displacement", str(args.displacement.absolute()),
        "--output", str(args.output.absolute()),
        "--strength", str(args.strength),
        "--voxel_size", str(args.voxel_size)
    ]
    
    logging.info("Starting Blender process...")
    try:
        subprocess.run(cmd, check=True)
        logging.info("Blender process completed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Blender process failed with exit code {e.returncode}")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
