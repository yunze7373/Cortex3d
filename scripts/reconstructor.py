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
    会自动检测环境：如果在本地运行，则通过 Docker Compose 调用容器。
    """
    logging.info(f"Starting Multi-View InstantMesh reconstruction... (Quality: {quality})")
    
    # 检测是否在 Docker 容器内
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("AM_I_IN_A_DOCKER_CONTAINER", False)
    
    # 配置文件
    if quality == "high":
        config_name = "instant-mesh-hq.yaml"
        config_path = "/workspace/configs/instant-mesh-hq.yaml" if not in_docker else str(PROJECT_ROOT / "configs" / "instant-mesh-hq.yaml")
    else:
        config_name = "instant-mesh-large.yaml"
        config_path = "/workspace/InstantMesh/configs/instant-mesh-large.yaml" if not in_docker else str(PROJECT_ROOT / "InstantMesh" / "configs" / "instant-mesh-large.yaml")
    
    if in_docker:
        # 容器内直接运行
        script_path = SCRIPT_DIR / "run_instantmesh_multiview.py"
        if not script_path.exists():
            logging.error(f"Multi-view script not found: {script_path}")
            return False
            
        cmd = [
            sys.executable, str(script_path),
            config_path,
            str(image_prefix),
            "--output_path", str(output_dir),
            "--export_texmap"
        ]
        
    else:
        # 本地运行 -> 调用 Docker Compose
        logging.info("Running locally, dispatching to 'instantmesh' container...")
        
        # 转换路径为容器内路径
        try:
            # image_prefix 可能是 "test_images/xxx" 或绝对路径
            prefix_path = Path(image_prefix)
            if prefix_path.is_absolute():
                rel_prefix = prefix_path.relative_to(PROJECT_ROOT.absolute())
            else:
                rel_prefix = prefix_path
            container_prefix = f"/workspace/{rel_prefix}"
            
            rel_output = output_dir.absolute().relative_to(PROJECT_ROOT.absolute())
            container_output = f"/workspace/{rel_output}"
        except ValueError:
            logging.warning("Path is outside project root, trying to use as-is...")
            container_prefix = str(image_prefix)
            container_output = str(output_dir)

        cmd = [
            "docker", "compose", "exec", "-T",
            "instantmesh",
            "python3", "/workspace/scripts/run_instantmesh_multiview.py",
            config_path,
            container_prefix,
            "--output_path", container_output,
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
    # Simplify parameter: ratio of faces to REMOVE (0.05 = remove 5%, keep 95%)
    if quality == "ultra":
        cmd.extend([
            "--texture_size", "4096",
            "--simplify", "0.02",  # Remove only 2%, keep 98% of faces for maximum detail
            "--ss_steps", "100",   # Maximum structure sampling steps
            "--slat_steps", "100", # Maximum latent sampling steps
            "--ss_guidance", "10.0",   # Higher guidance for detail
            "--slat_guidance", "10.0",
        ])
    elif quality == "high":
        cmd.extend([
            "--texture_size", "2048",
            "--simplify", "0.05",  # Remove only 5%, keep 95% of faces
            "--ss_steps", "75",    # Higher steps for better structure
            "--slat_steps", "75",  # Higher steps for better latent detail
            "--ss_guidance", "8.5",    # Slightly higher guidance
            "--slat_guidance", "8.5",
        ])
    else:
        # Default/Balanced
        cmd.extend([
            "--simplify", "0.5", 
        ])
        
    return run_command(cmd, cwd=PROJECT_ROOT)


def run_hunyuan3d(image_path, output_dir, quality="balanced", no_texture=False, sharpen=False, sharpen_strength=1.0):
    """
    调用 Hunyuan3D-2.0 生成 (腾讯高质量图转3D模型)
    会自动检测环境：如果在本地运行，则通过 Docker Compose 调用容器。
    """
    logging.info(f"Starting Hunyuan3D-2.0 reconstruction... (Quality: {quality})")
    
    # 检测是否在 Docker 容器内
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("AM_I_IN_A_DOCKER_CONTAINER", False)
    
    # 根据质量选择模型类型和参数
    model_type = "full" if quality in ["high", "ultra"] else "lite"
    
    # 质量预设：基于腾讯官方网站 (3d.hunyuan.tencent.com) 的参数
    # octree_resolution: 越高mesh细节越锐利
    # 注意: RTX 3070 (16GB) 用 octree=1024 会导致 100+ 小时生成时间
    # 所以对于消费级 GPU，ultra 使用 768
    quality_presets = {
        "balanced": {"octree": 512, "guidance": 5.5, "steps": 50},   # ~15-30分钟
        "high":     {"octree": 640, "guidance": 6.0, "steps": 60},   # ~30-60分钟
        "ultra":    {"octree": 768, "guidance": 6.5, "steps": 75}    # ~60-120分钟 (之前1024太慢)
    }
    preset = quality_presets.get(quality, quality_presets["balanced"])
    
    if in_docker:
        # 容器内直接运行
        script_path = SCRIPT_DIR / "run_hunyuan3d.py"
        if not script_path.exists():
            logging.error(f"Hunyuan3D script not found: {script_path}")
            return False
        
        # Enable multi-view for ultra quality
        use_multiview = quality == "ultra"
            
        cmd = [
            sys.executable, str(script_path),
            str(image_path),
            "--output", str(output_dir),
            "--model", model_type,
            "--octree", str(preset["octree"]),
            "--guidance", str(preset["guidance"]),
            "--steps", str(preset["steps"])
        ]
        if use_multiview:
            cmd.append("--multiview")
        if no_texture:
            cmd.append("--no-texture")
        if sharpen:
            cmd.extend(["--sharpen", "--sharpen-strength", str(sharpen_strength)])
        
    else:
        # 本地运行 -> 调用 Docker Compose
        logging.info("Running locally, dispatching to 'hunyuan3d' container...")
        
        # Enable multi-view for ultra quality
        use_multiview = quality == "ultra"
        
        # 转换路径为容器内路径
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
            "docker", "compose", "exec", "-T",
            "hunyuan3d",
            "python3", "/workspace/scripts/run_hunyuan3d.py",
            container_image,
            "--output", container_output,
            "--model", model_type,
            "--octree", str(preset["octree"]),
            "--guidance", str(preset["guidance"]),
            "--steps", str(preset["steps"])
        ]
        if use_multiview:
            cmd.append("--multiview")
        if no_texture:
            cmd.append("--no-texture")
        if sharpen:
            cmd.extend(["--sharpen", "--sharpen-strength", str(sharpen_strength)])
        
    return run_command(cmd, cwd=PROJECT_ROOT)


def run_hunyuan3d_21(image_path, output_dir, quality="balanced", no_texture=False, sharpen=False, sharpen_strength=1.0):
    """
    调用 Hunyuan3D-2.1 生成 (腾讯最新版，10x几何精度提升 + PBR材质)
    会自动检测环境：如果在本地运行，则通过 Docker Compose 调用容器。
    """
    logging.info(f"Starting Hunyuan3D-2.1 reconstruction... (Quality: {quality})")
    
    # 检测是否在 Docker 容器内
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("AM_I_IN_A_DOCKER_CONTAINER", False)
    
    # 根据质量选择模型类型和参数
    model_type = "full" if quality in ["high", "ultra"] else "lite"
    
    # 质量预设：基于腾讯官方参数，2.1 版本优化
    quality_presets = {
        "balanced": {"octree": 512, "guidance": 5.5, "steps": 50},
        "high":     {"octree": 768, "guidance": 6.5, "steps": 75},
        "ultra":    {"octree": 1024, "guidance": 7.0, "steps": 100}
    }
    preset = quality_presets.get(quality, quality_presets["balanced"])
    
    if in_docker:
        # 容器内直接运行
        script_path = SCRIPT_DIR / "run_hunyuan3d.py"
        if not script_path.exists():
            logging.error(f"Hunyuan3D script not found: {script_path}")
            return False
            
        cmd = [
            sys.executable, str(script_path),
            str(image_path),
            "--output", str(output_dir),
            "--model", model_type,
            "--octree", str(preset["octree"]),
            "--guidance", str(preset["guidance"]),
            "--steps", str(preset["steps"])
        ]
        if no_texture:
            cmd.append("--no-texture")
        if sharpen:
            cmd.extend(["--sharpen", "--sharpen-strength", str(sharpen_strength)])
    else:
        # 本地运行，通过 Docker Compose 调用 hunyuan3d-2.1 容器
        logging.info("Running locally, dispatching to 'hunyuan3d-2.1' container...")
        
        # 转换为容器内路径
        container_image_path = f"/workspace/{image_path}"
        container_output_dir = f"/workspace/{output_dir}"
        
        cmd = [
            "docker", "compose", "exec", "-T", "hunyuan3d-2.1",
            "python3", "/workspace/scripts/run_hunyuan3d.py",
            container_image_path,
            "--output", container_output_dir,
            "--model", model_type,
            "--octree", str(preset["octree"]),
            "--guidance", str(preset["guidance"]),
            "--steps", str(preset["steps"])
        ]
        if no_texture:
            cmd.append("--no-texture")
        if sharpen:
            cmd.extend(["--sharpen", "--sharpen-strength", str(sharpen_strength)])
        
        logging.info(f"Executing: {' '.join(cmd)}")
        
    return run_command(cmd, cwd=PROJECT_ROOT)


def run_trellis2(image_path, output_dir, quality="balanced"):
    """
    调用 TRELLIS.2 生成 (微软最新，锐利边缘保留)
    会自动检测环境：如果在本地运行，则通过 Docker Compose 调用容器。
    
    Args:
        image_path: 输入图像路径
        output_dir: 输出目录
        quality: 质量预设 (balanced, high, ultra)
        
    Returns:
        bool: 是否成功
    """
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info(f"[TRELLIS.2] Sharp Edge 3D Generation...")
    logging.info(f"[TRELLIS.2] Input: {image_path}")
    logging.info(f"[TRELLIS.2] Quality: {quality}")
    
    # Quality presets for decimation and texture
    quality_presets = {
        "balanced": {"decimation": 500000, "texture_size": 2048},
        "high":     {"decimation": 1000000, "texture_size": 4096},
        "ultra":    {"decimation": 2000000, "texture_size": 4096}
    }
    preset = quality_presets.get(quality, quality_presets["balanced"])
    
    # Check if running inside container
    in_container = os.path.exists("/.dockerenv") or os.path.exists("/opt/trellis2")
    
    if in_container:
        # Running inside trellis2 container -> call script directly
        logging.info("Running inside TRELLIS.2 container...")
        cmd = [
            "python3", "/workspace/scripts/run_trellis2.py",
            str(image_path),
            "--output", str(output_dir),
            "--decimation", str(preset["decimation"]),
            "--texture-size", str(preset["texture_size"])
        ]
    else:
        # Running locally -> use Docker Compose
        logging.info("Running locally, dispatching to 'trellis2' container...")
        
        # Convert paths to container paths
        try:
            rel_image = image_path.absolute().relative_to(PROJECT_ROOT.absolute())
            rel_output = output_dir.absolute().relative_to(PROJECT_ROOT.absolute())
        except ValueError:
            logging.error("Image path must be within project root for Docker mount")
            return False
        
        container_image = f"/workspace/{rel_image.as_posix()}"
        container_output = f"/workspace/{rel_output.as_posix()}"
        
        cmd = [
            "docker", "compose", "exec", "-T", "trellis2",
            "python3", "/workspace/scripts/run_trellis2.py",
            container_image,
            "--output", container_output,
            "--decimation", str(preset["decimation"]),
            "--texture-size", str(preset["texture_size"])
        ]
    
    return run_command(cmd, cwd=PROJECT_ROOT)

def main():
    parser = argparse.ArgumentParser(description="Cortex3d Unified Reconstructor (Stage 2)")
    parser.add_argument("image", type=Path, help="Path to input image (front view) OR prefix for multi-view images")
    parser.add_argument("--algo", choices=["instantmesh", "triposr", "auto", "multiview", "trellis", "trellis2", "hunyuan3d", "hunyuan3d-2.1"], default="trellis", help="Reconstruction algorithm")
    parser.add_argument("--quality", choices=["balanced", "high", "ultra"], default="balanced", help="Quality preset")
    parser.add_argument("--output_dir", type=Path, default=OUTPUTS_DIR, help="Output directory")
    parser.add_argument("--enhance", action="store_true", help="Enhance input image with Real-ESRGAN + GFPGAN before 3D generation")
    parser.add_argument("--no-texture", "--fast", dest="no_texture", action="store_true", 
                        help="Skip texture generation for faster results (Hunyuan3D only)")
    parser.add_argument("--sharpen", action="store_true",
                        help="Apply mesh sharpening post-processing to enhance edge details (Hunyuan3D only)")
    parser.add_argument("--sharpen-strength", type=float, default=1.0,
                        help="Mesh sharpening strength multiplier (0.5-2.0)")
    
    args = parser.parse_args()
    
    if not args.image.exists():
        logging.error(f"Image not found: {args.image}")
        sys.exit(1)
        
    args.output_dir.mkdir(parents=True, exist_ok=True)
    algo_output_dir = args.output_dir / args.algo if args.algo != "auto" else args.output_dir / "instantmesh"

    # Apply image enhancement if requested
    input_image = args.image
    if args.enhance:
        logging.info("Applying image enhancement (Real-ESRGAN + GFPGAN)...")
        try:
            from image_enhancer import enhance_for_trellis
            enhanced_path = args.image.parent / f"{args.image.stem}_enhanced.png"
            enhance_for_trellis(str(args.image), str(enhanced_path))
            if enhanced_path.exists():
                input_image = enhanced_path
                logging.info(f"Using enhanced image: {input_image}")
            else:
                logging.warning("Enhancement failed, using original image")
        except ImportError as e:
            logging.warning(f"Image enhancer not available: {e}")
            logging.warning("Install dependencies: pip install realesrgan gfpgan basicsr")
        except Exception as e:
            logging.warning(f"Image enhancement failed: {e}")
            logging.warning("Continuing with original image...")

    success = False
    result_mesh = None
    
    # Helper to find result mesh
    image_name = args.image.stem  # Keep original name for output
    
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
        if run_instantmesh(input_image, algo_output_dir, args.quality):
            success = True
            config_name = "instant-mesh-hq" if args.quality == "high" else "instant-mesh-large"
            result_mesh = algo_output_dir / config_name / "meshes" / f"{image_name}.obj"
        
    elif args.algo == "triposr":
        if run_triposr(input_image, algo_output_dir, args.quality):
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
        if run_trellis(input_image, algo_output_dir, args.quality):
            success = True
            result_mesh = algo_output_dir / f"{image_name}.obj"
    
    elif args.algo == "hunyuan3d":
        algo_output_dir = args.output_dir / "hunyuan3d"
        # Hunyuan3D output name removes _front suffix
        output_name = image_name.replace('_front', '')
        no_texture = getattr(args, 'no_texture', False)
        sharpen = getattr(args, 'sharpen', False)
        sharpen_strength = getattr(args, 'sharpen_strength', 1.0)
        if run_hunyuan3d(input_image, algo_output_dir, args.quality, 
                         no_texture=no_texture, sharpen=sharpen, sharpen_strength=sharpen_strength):
            success = True
            result_mesh = algo_output_dir / f"{output_name}.glb"
    
    elif args.algo == "hunyuan3d-2.1":
        algo_output_dir = args.output_dir / "hunyuan3d-2.1"
        # Hunyuan3D output name removes _front suffix
        output_name = image_name.replace('_front', '')
        no_texture = getattr(args, 'no_texture', False)
        sharpen = getattr(args, 'sharpen', False)
        sharpen_strength = getattr(args, 'sharpen_strength', 1.0)
        if run_hunyuan3d_21(input_image, algo_output_dir, args.quality, 
                           no_texture=no_texture, sharpen=sharpen, sharpen_strength=sharpen_strength):
            success = True
            result_mesh = algo_output_dir / f"{output_name}.glb"
    
    elif args.algo == "trellis2":
        algo_output_dir = args.output_dir / "trellis2"
        # TRELLIS.2 output name removes _front suffix
        output_name = image_name.replace('_front', '')
        if run_trellis2(input_image, algo_output_dir, args.quality):
            success = True
            result_mesh = algo_output_dir / f"{output_name}.glb"
        
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
