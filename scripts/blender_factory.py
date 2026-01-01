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
    parser.add_argument("--output", type=Path, required=True, help="Output STL path")
    parser.add_argument("--height_mm", type=float, default=100.0, help="Target height in mm")
    parser.add_argument("--voxel_size_mm", type=float, default=0.1, help="Voxel remesh size (mm)")
    parser.add_argument(
        "--profile",
        type=str,
        default="default",
        choices=["default", "resin-mini"],
        help="Print profile preset passed to refinement script.",
    )
    parser.add_argument(
        "--decimate_ratio",
        type=float,
        default=None,
        help="Override decimate ratio (0-1). Default depends on profile and face count.",
    )
    parser.add_argument("--skip_remesh", action="store_true", help="Skip voxel remeshing (preserve original topology)")
    
    args = parser.parse_args()
    
    executable = check_blender()
    if not executable:
        logging.error("Blender executable not found in PATH or standard locations.")
        sys.exit(1)
        
    logging.info(f"Using Blender: {executable}")
    
    if not args.mesh.exists():
        logging.error(f"Mesh not found: {args.mesh}")
        sys.exit(1)
        
    # Construct Blender command
    # blender -b -P refinement.py -- --mesh ...
    cmd = [
        executable,
        "--background",  # Headless
        "--python", str(REFINEMENT_SCRIPT),
        "--",  # Pass args to python script
        "--mesh", str(args.mesh.absolute()),
        "--output", str(args.output.absolute()),
        "--height_mm", str(args.height_mm),
        "--voxel_size_mm", str(args.voxel_size_mm),
        "--profile", str(args.profile),
    ]

    if args.decimate_ratio is not None:
        cmd.extend(["--decimate_ratio", str(args.decimate_ratio)])
        
    if args.skip_remesh:
        cmd.append("--skip_remesh")
    
    logging.info("Starting Blender process...")
    try:
        subprocess.run(cmd, check=True)
        logging.info("Blender process completed successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Blender process failed with exit code {e.returncode}")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
