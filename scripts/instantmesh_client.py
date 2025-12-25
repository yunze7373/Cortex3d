#!/usr/bin/env python3
"""
InstantMesh 3D 模型生成客户端

集成到 Cortex3d 项目中，自动检测 InstantMesh 子模块并运行

使用方法:
    # 使用最新生成的 front.png
    python scripts/instantmesh_client.py
    
    # 指定图片
    python scripts/instantmesh_client.py test_images/character_xxx_front.png
    
    # 使用所有 4 个视角（将 front 发送给 InstantMesh）
    python scripts/instantmesh_client.py --latest
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional
import subprocess
import glob

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
INSTANTMESH_DIR = PROJECT_ROOT / "InstantMesh"
TEST_IMAGES_DIR = PROJECT_ROOT / "test_images"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def find_latest_front_image() -> Optional[Path]:
    """查找最新生成的 front 视图图片"""
    pattern = str(TEST_IMAGES_DIR / "character_*_front.png")
    files = glob.glob(pattern)
    if files:
        return Path(max(files, key=os.path.getmtime))
    return None


def check_instantmesh() -> bool:
    """检查 InstantMesh 是否已安装"""
    run_script = INSTANTMESH_DIR / "run.py"
    if not run_script.exists():
        print(f"[ERROR] InstantMesh 未找到: {INSTANTMESH_DIR}")
        print("\n请运行以下命令初始化子模块:")
        print("  git submodule update --init --recursive")
        return False
    return True


def check_dependencies() -> bool:
    """检查 InstantMesh 依赖是否已安装"""
    try:
        import torch
        import diffusers
        print(f"[INFO] PyTorch 版本: {torch.__version__}")
        print(f"[INFO] CUDA 可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"[INFO] GPU: {torch.cuda.get_device_name(0)}")
        return True
    except ImportError as e:
        print(f"[ERROR] 缺少依赖: {e}")
        print("\n请安装 InstantMesh 依赖:")
        print(f"  cd {INSTANTMESH_DIR}")
        print("  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
        print("  pip install -r requirements.txt")
        return False


def run_instantmesh(image_path: Path, output_dir: Path = OUTPUTS_DIR) -> Optional[Path]:
    """
    运行 InstantMesh 生成 3D 模型
    
    Args:
        image_path: 输入图片路径 (front view)
        output_dir: 输出目录
    
    Returns:
        生成的 3D 模型路径
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("InstantMesh 3D 模型生成")
    print("="*60)
    print(f"[输入] {image_path}")
    print(f"[输出] {output_dir}")
    print("-"*60)
    
    # 构建命令 - 直接使用当前 Python 环境
    run_script = INSTANTMESH_DIR / "run.py"
    
    cmd = [
        sys.executable,  # 使用当前 Python
        str(run_script),
        str(image_path.absolute()),
        "--output_dir", str(output_dir.absolute())
    ]
    
    print(f"[CMD] {' '.join(cmd)}")
    print("[INFO] 正在生成 3D 模型... (可能需要 2-5 分钟)")
    
    try:
        # 添加 InstantMesh 到 Python 路径
        env = os.environ.copy()
        env["PYTHONPATH"] = str(INSTANTMESH_DIR) + os.pathsep + env.get("PYTHONPATH", "")
        
        result = subprocess.run(
            cmd,
            cwd=str(INSTANTMESH_DIR),
            env=env,
            capture_output=False,  # 实时显示输出
            timeout=600  # 10 分钟超时
        )
        
        if result.returncode != 0:
            print(f"[ERROR] InstantMesh 执行失败 (exit code: {result.returncode})")
            return None
        
        # 查找生成的模型文件
        model_files = list(output_dir.glob("*.obj")) + list(output_dir.glob("*.glb"))
        if model_files:
            latest_model = max(model_files, key=lambda f: f.stat().st_mtime)
            print(f"\n[完成] 3D 模型: {latest_model}")
            return latest_model
        else:
            print("[WARNING] 未找到生成的模型文件")
            print(f"[DEBUG] 输出目录内容: {list(output_dir.iterdir())}")
            return None
            
    except subprocess.TimeoutExpired:
        print("[ERROR] InstantMesh 执行超时 (10分钟)")
        return None
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Cortex3d - InstantMesh 3D 模型生成"
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="输入图片路径 (front view)，不指定则使用最新生成的图片"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="使用最新生成的 front 视图图片"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUTS_DIR),
        help=f"输出目录 (默认: {OUTPUTS_DIR})"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查依赖，不运行生成"
    )
    
    args = parser.parse_args()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║           Cortex3d - InstantMesh 3D 模型生成                 ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 检查 InstantMesh
    if not check_instantmesh():
        return 1
    
    # 只检查模式
    if args.check:
        check_dependencies()
        return 0
    
    # 确定输入图片
    if args.image:
        image_path = Path(args.image)
    else:
        image_path = find_latest_front_image()
        if not image_path:
            print("[ERROR] 未找到 front 视图图片")
            print(f"请先运行 generate_character.py 生成图片，或指定图片路径")
            return 1
        print(f"[INFO] 使用最新图片: {image_path}")
    
    if not image_path.exists():
        print(f"[ERROR] 图片不存在: {image_path}")
        return 1
    
    # 运行 InstantMesh
    output_dir = Path(args.output)
    result = run_instantmesh(image_path, output_dir)
    
    if result:
        print("\n" + "="*60)
        print("✅ 3D 模型生成成功!")
        print("="*60)
        print(f"模型文件: {result}")
        print(f"\n使用 Blender 或 3D 查看器打开查看")
        return 0
    else:
        print("\n❌ 3D 模型生成失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
