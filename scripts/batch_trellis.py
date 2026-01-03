#!/usr/bin/env python3
"""
Cortex3d Batch Processor
Scans the input directory for *_front.png images and generates 3D models for those that haven't been processed yet.
"""

import argparse
import sys
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Batch process 3D generation (TRELLIS)")
    parser.add_argument("--input", default="test_images", help="Input directory containing *_front.png")
    parser.add_argument("--output", default="outputs/trellis", help="Output directory for 3D models")
    parser.add_argument("--dry-run", action="store_true", help="Only list prompt status, do not generate")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        sys.exit(1)
        
    # Find all front views
    front_images = list(input_dir.glob("*_front.png"))
    if not front_images:
        print(f"[INFO] No *_front.png images found in {input_dir}")
        sys.exit(0)
        
    print(f"[INFO] Found {len(front_images)} candidate images in {input_dir}")
    
    to_process = []
    
    print("\nStatus Report:")
    print("-" * 60)
    print(f"{'Image':<40} | {'Status':<15} | {'Output'}")
    print("-" * 60)
    
    for img_path in sorted(front_images):
        # Expected output name: stem of the image (without _front) + .glb?
        # Typically generate_character.py creates names like "character_TIMESTAMP_front.png"
        # reconstructor.py outputs "character_TIMESTAMP.glb" (or input stem .glb)
        
        # reconstructor (TRELLIS) typically uses the image stem as the output name
        # So inputs/foo_front.png -> outputs/foo_front.glb
        # Wait, let's verify run_trellis behavior.
        # run_trellis: image_name = Path(args.image).stem -> output_dir / f"{image_name}.glb"
        # So output is "character_TIMESTAMP_front.glb"
        
        expected_glb = output_dir / f"{img_path.stem}.glb"
        
        if expected_glb.exists():
            status = "✅ DONE"
            print(f"{img_path.name:<40} | {status:<15} | {expected_glb.name}")
        else:
            status = "⏳ PENDING"
            print(f"{img_path.name:<40} | {status:<15} | -")
            to_process.append(img_path)
            
    print("-" * 60)
    
    if not to_process:
        print("\n[INFO] All images have been processed! 🎉")
        return
        
    if args.dry_run:
        print(f"\n[INFO] Dry run complete. {len(to_process)} images pending.")
        return
        
    print(f"\n[INFO] Starting batch processing for {len(to_process)} images...")
    
    reconstructor_script = Path("scripts/reconstructor.py")
    if not reconstructor_script.exists():
        print(f"[ERROR] Reconstructor script not found: {reconstructor_script}")
        sys.exit(1)
        
    for i, img_path in enumerate(to_process):
        print("\n" + "=" * 60)
        print(f"[{i+1}/{len(to_process)}] Processing: {img_path.name}")
        print("=" * 60)
        
        cmd = [
            sys.executable,
            str(reconstructor_script),
            str(img_path),
            "--algo", "trellis",
            "--quality", "high",
            "--output_dir", "outputs" # reconstructor puts output in outputs/trellis
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"[SUCCESS] Processed {img_path.name}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to process {img_path.name}: {e}")
            # Continue to next?
            choice = input("Continue to next? [Y/n] ").lower()
            if choice == 'n':
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n[INFO] Batch processing interrupted.")
            sys.exit(0)

if __name__ == "__main__":
    main()
