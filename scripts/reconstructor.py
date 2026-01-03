#!/usr/bin/env python3
"""
Cortex3d Unified Reconstructor (Stage 2)
负责调度 InstantMesh 和 TripoSR，提供统一的调用接口。
"""

import argparse
import logging
import os
import subprocess
import sys
import shutil
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# DEBUG: Check environment versions
try:
    import torch
    import transformers
    logging.info(f"ENVIRONMENT CHECK: Torch={torch.__version__}, Transformers={transformers.__version__}")
except ImportError:
    logging.warning("Could not import torch/transformers for version check.")

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

def run_command(cmd, cwd=None, env=None):
    """运行外部命令并实时打印输出"""
    try:
        logging.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}")
        return False

def run_instantmesh(image_path, output_dir, quality="balanced"):
    """
    调用 InstantMesh 生成
    quality: balanced (default), high (more steps)
    """
    logging.info(f"Starting InstantMesh reconstruction... (Quality: {quality})")
    
    # 构造 run_instantmesh.py 的命令
    # 注意: instantmesh_client.py 主要是为了 Docker/Client 分离设计的，
    # 这里我们直接调用底层的 run_instantmesh.py (如果存在) 或者直接调用 InstantMesh/run.py
    # 为了保持架构整洁，我们复用 instantmesh_client.py 的逻辑，或者直接调用 run_instantmesh.py (如果它封装得好的话)
    # 查看之前的记录，我们有 scripts/run_instantmesh.py
    
    script_path = SCRIPT_DIR / "run_instantmesh.py"
    if not script_path.exists():
        # Fallback to direct submodule call if wrapper missing, but we expect wrapper
        logging.error(f"Wrapper script not found: {script_path}")
        return False

    IM_CONFIG = PROJECT_ROOT / "InstantMesh" / "configs" / "instant-mesh-large.yaml"
    if quality == "high":
        IM_CONFIG = PROJECT_ROOT / "configs" / "instant-mesh-hq.yaml" # Assuming this exists or using large as base

    cmd = [
        sys.executable, str(script_path),
        str(IM_CONFIG),
        str(image_path),
        "--output_path", str(output_dir),
        "--export_texmap"
    ]
    
    if quality == "high":
        cmd.extend(["--diffusion_steps", "200", "--texture_resolution", "2048"])
        
    return run_command(cmd, cwd=PROJECT_ROOT)

def copy_to_latest(source_path, output_dir):
    """Copy the generated mesh to a predictable path for the next stage"""
    latest_obj = output_dir / "latest.obj"
    latest_glb = output_dir / "latest.glb"
    
    # Clean up previous
    if latest_obj.exists(): latest_obj.unlink()
    if latest_glb.exists(): latest_glb.unlink()
    
    if source_path.suffix == '.obj':
        shutil.copy(source_path, latest_obj)
        # Try to copy texture if it exists/is needed, but usually .obj needs .mtl and images.
        # Ideally we'd copy the whole folder or just point the next stage to the result.
        # For simplicty, let's copy the .obj. If it has dependencies, this might be brittle.
        # Better approach: The next stage should know the path. 
        # But if we want a unified pipeline, a symlink or copy is good.
        # Actually, let's just log the path and let the caller handle it?
        # No, the Makefile has hardcoded paths. We need a reliable path.
        logging.info(f"Updated latest mesh link: {latest_obj}")
    return latest_obj
    

def run_triposr(image_path, output_dir, quality="balanced"):
    """
    调用 TripoSR 生成
    quality: balanced (default), high (1024 resolution + chunking)
    """
    logging.info(f"Starting TripoSR reconstruction... (Quality: {quality})")
    
    script_path = SCRIPT_DIR / "run_triposr.py"
    
    cmd = [
        sys.executable, str(script_path),
        str(image_path),
        "--output-dir", str(output_dir),
        "--bake-texture"
    ]
    
    # TripoSR 特定参数
    if quality == "high":
        cmd.extend([
            "--mc-resolution", "1024",  # 使用我们 patch 过的 chunking 逻辑
            "--texture-resolution", "2048"
        ])
    else:
        cmd.extend([
            "--mc-resolution", "256",
            "--texture-resolution", "1024"
        ])

    return run_command(cmd, cwd=PROJECT_ROOT)

def run_multiview(image_prefix, output_dir, quality="balanced"):
    """
    调用 InstantMesh Multi-View 生成 (使用用户提供的4视角图片)
    image_prefix: 图片前缀，如 "test_images/character_20251226_013442"，
                  会自动查找 *_front.png, *_back.png, *_left.png, *_right.png
    """
    logging.info(f"Starting Multi-View InstantMesh reconstruction... (Quality: {quality})")
    
    script_path = SCRIPT_DIR / "run_instantmesh_multiview.py"
    if not script_path.exists():
        logging.error(f"Multi-view script not found: {script_path}")
        return False

    IM_CONFIG = PROJECT_ROOT / "InstantMesh" / "configs" / "instant-mesh-large.yaml"
    if quality == "high":
        IM_CONFIG = PROJECT_ROOT / "configs" / "instant-mesh-hq.yaml"

    cmd = [
        sys.executable, str(script_path),
        str(IM_CONFIG),
        str(image_prefix),
        "--output_path", str(output_dir),
        "--export_texmap"
    ]
    
    if quality == "high":
        cmd.extend(["--texture_resolution", "2048"])
        
    return run_command(cmd, cwd=PROJECT_ROOT)

def run_trellis(image_path, output_dir, quality="balanced"):
    """
    调用 TRELLIS 生成 (微软高质量图转3D模型)
    会自动检测环境：如果在本地运行，则通过 Docker Compose 调用容器。
    """
    logging.info(f"Starting TRELLIS reconstruction... (Quality: {quality})")
    
    # 检测是否在 Docker 容器内
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("AM_I_IN_A_DOCKER_CONTAINER", False)
    
    if in_docker:
        # 容器内直接运行
        script_path = SCRIPT_DIR / "run_trellis.py"
        if not script_path.exists():
            logging.error(f"TRELLIS script not found: {script_path}")
            return False
            
        cmd = [sys.executable, str(script_path)]
        # 路径直接使用传入的路径 (假设容器内路径一致)
        img_arg = str(image_path)
        out_arg = str(output_dir)
        
    else:
        # 本地运行 -> 调用 Docker Compose
        logging.info("Running locally, dispatching to 'trellis' container...")
        
        # 转换路径为容器内路径 (假设挂载了 . -> /workspace)
        # image_path 是绝对路径或相对路径。我们需要相对于 PROJECT_ROOT 的路径。
        try:
            rel_image = image_path.absolute().relative_to(PROJECT_ROOT.absolute())
            container_image = f"/workspace/{rel_image}"
            
            rel_output = output_dir.absolute().relative_to(PROJECT_ROOT.absolute())
            container_output = f"/workspace/{rel_output}"
        except ValueError:
            logging.warning("Path is outside project root, trying to use as-is...")
            container_image = str(image_path)
            container_output = str(output_dir)

        cmd = [
            "docker", "compose", "exec", "-T", # -T 避免 TTY 错误
            "trellis",
            "python3", "/workspace/scripts/run_trellis.py"
        ]
        img_arg = container_image
        out_arg = container_output

    # 组装参数
    cmd.append(img_arg)
    cmd.extend(["--output", out_arg])

    # Note: scripts/run_trellis.py does not expose a resolution flag.
    # Use texture size + simplify as quality controls.
    if quality == "high":
        cmd.extend([
            "--texture_size", "2048",
            # Simplify 0.5 keeps 50% of faces. 0.98 kept only 2%.
            "--simplify", "0.5",
            "--ss_steps", "50",
            "--slat_steps", "50",
        ])
    else:
        # Default/Balanced
        cmd.extend([
            "--simplify", "0.90", # Slightly less aggressive than 0.95
        ])
        
    return run_command(cmd, cwd=PROJECT_ROOT)


def main():
    parser = argparse.ArgumentParser(description="Cortex3d Unified Reconstructor (Stage 2)")
    parser.add_argument("image", type=Path, help="Path to input image (front view) OR prefix for multi-view images")
    parser.add_argument("--algo", choices=["instantmesh", "triposr", "auto", "multiview", "trellis"], default="instantmesh", help="Reconstruction algorithm")
    parser.add_argument("--quality", choices=["balanced", "high"], default="balanced", help="Quality preset")
    parser.add_argument("--output_dir", type=Path, default=OUTPUTS_DIR, help="Output directory")
    
    args = parser.parse_args()
    
    if not args.image.exists():
        logging.error(f"Image not found: {args.image}")
        sys.exit(1)
        
    args.output_dir.mkdir(parents=True, exist_ok=True)
    algo_output_dir = args.output_dir / args.algo if args.algo != "auto" else args.output_dir / "instantmesh"

    success = False
    result_mesh = None
    
    # Helper to find result mesh
    image_name = args.image.stem
    
    # Auto mode: Try InstantMesh first.
    # DISABLE FALLBACK for debugging to ensure we get InstantMesh quality.
    if args.algo == "auto":
        logging.info("Mode: AUTO. Running InstantMesh...")
        if run_instantmesh(args.image, algo_output_dir, args.quality):
            success = True
            # InstantMesh output structure: <out_dir>/instant-mesh-large/meshes/<name>.obj
            # or instant-mesh-hq depending on config used.
            config_name = "instant-mesh-hq" if args.quality == "high" else "instant-mesh-large"
            result_mesh = algo_output_dir / config_name / "meshes" / f"{image_name}.obj"
        else:
            logging.error("InstantMesh failed. Fallback disabled to debug quality.")
            sys.exit(1)
            
            # logging.warning("InstantMesh failed. Falling back to TripoSR...")
            # fallback_dir = args.output_dir / "triposr"
            # if run_triposr(args.image, fallback_dir, args.quality):
            #     success = True
            #     result_mesh = fallback_dir / image_name / f"{image_name}.obj"
            #     logging.info(f"Fallback to TripoSR successful. Result in {fallback_dir}")
            # else:
            #     logging.error("Both algorithms failed.")
    
    elif args.algo == "instantmesh":
        if run_instantmesh(args.image, algo_output_dir, args.quality):
            success = True
            config_name = "instant-mesh-hq" if args.quality == "high" else "instant-mesh-large"
            result_mesh = algo_output_dir / config_name / "meshes" / f"{image_name}.obj"
        
    elif args.algo == "triposr":
        if run_triposr(args.image, algo_output_dir, args.quality):
            success = True
            result_mesh = algo_output_dir / image_name / f"{image_name}.obj"
    
    elif args.algo == "multiview":
        # For multiview, the "image" arg is actually a prefix
        # e.g., test_images/character_20251226_013442 -> look for *_front.png, etc.
        image_prefix = str(args.image).replace('_front.png', '').replace('_front', '')
        algo_output_dir = args.output_dir / "multiview"
        if run_multiview(image_prefix, algo_output_dir, args.quality):
            success = True
            config_name = "instant-mesh-hq-multiview" if args.quality == "high" else "instant-mesh-large-multiview"
            # For multiview, the mesh name is the base prefix (without _front suffix)
            multiview_name = Path(image_prefix).name
            result_mesh = algo_output_dir / config_name / "meshes" / f"{multiview_name}.obj"
    
    elif args.algo == "trellis":
        algo_output_dir = args.output_dir / "trellis"
        if run_trellis(args.image, algo_output_dir, args.quality):
            success = True
            result_mesh = algo_output_dir / f"{image_name}.obj"
        
    if success and result_mesh and result_mesh.exists():
        logging.info(f"Reconstruction completed successfully. Mesh: {result_mesh}")
        # Copy to a Latest location for stage4 to pick up easily
        latest_path = args.output_dir / "latest.obj"
        try:
            if latest_path.exists():
                latest_path.unlink()
            shutil.copy(result_mesh, latest_path)
            logging.info(f"Updated latest mesh: {latest_path}")
        except PermissionError:
            logging.warning(f"Permission denied: Cannot update {latest_path}. (Owned by root?)")
            logging.warning("To fix, run: sudo rm output/latest.obj")
            # Don't exit 1, because generation IS successful
        except Exception as e:
            logging.warning(f"Failed to update latest.obj: {e}")
            
        sys.exit(0)
    else:
        logging.error("Reconstruction failed or mesh not found.")
        sys.exit(1)

if __name__ == "__main__":
    main()
