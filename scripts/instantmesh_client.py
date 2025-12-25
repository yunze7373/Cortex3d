#!/usr/bin/env python3
"""
InstantMesh 3D 模型生成客户端

支持两种模式:
1. 本地模式 - 在本机运行 InstantMesh (需要 NVIDIA GPU)
2. 远程模式 - 调用远程 InstantMesh 服务

使用方法:
    # 本地模式 (需要先安装 InstantMesh)
    python instantmesh_client.py front.png --mode local --instantmesh-dir /path/to/InstantMesh
    
    # 远程模式 (需要远程服务器运行 InstantMesh 服务)
    python instantmesh_client.py front.png --mode remote --server http://your-gpu-server:8000
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
import shutil

# 导入共享配置
try:
    from config import IMAGE_MODEL
except ImportError:
    IMAGE_MODEL = "models/nano-banana-pro-preview"


def run_local_instantmesh(
    image_path: str,
    instantmesh_dir: str,
    output_dir: str = "outputs",
    conda_env: str = "instantmesh"
) -> Optional[str]:
    """
    本地运行 InstantMesh 生成 3D 模型
    
    Args:
        image_path: 输入图片路径 (front view)
        instantmesh_dir: InstantMesh 安装目录
        output_dir: 输出目录
        conda_env: Conda 环境名称
    
    Returns:
        生成的 3D 模型路径 或 None
    """
    instantmesh_path = Path(instantmesh_dir)
    run_script = instantmesh_path / "run.py"
    
    if not run_script.exists():
        print(f"[ERROR] InstantMesh 未找到: {run_script}")
        print("请先克隆 InstantMesh: git clone https://github.com/TencentARC/InstantMesh.git")
        return None
    
    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 构建命令
    image_abs_path = Path(image_path).absolute()
    output_abs_path = output_path.absolute()
    
    print("="*60)
    print("InstantMesh 3D 模型生成")
    print("="*60)
    print(f"[输入] {image_abs_path}")
    print(f"[输出] {output_abs_path}")
    print(f"[环境] {conda_env}")
    print("-"*60)
    
    # 检测操作系统
    if sys.platform == "win32":
        # Windows
        cmd = f'conda activate {conda_env} && python run.py "{image_abs_path}" --output_dir "{output_abs_path}"'
        shell = True
    else:
        # Linux/macOS
        cmd = [
            "conda", "run", "-n", conda_env,
            "python", str(run_script),
            str(image_abs_path),
            "--output_dir", str(output_abs_path)
        ]
        shell = False
    
    print(f"[CMD] {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    print("[INFO] 正在生成 3D 模型... (可能需要 2-5 分钟)")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(instantmesh_path),
            shell=shell,
            capture_output=True,
            text=True,
            timeout=600  # 10 分钟超时
        )
        
        if result.returncode != 0:
            print(f"[ERROR] InstantMesh 执行失败:")
            print(result.stderr)
            return None
        
        print(result.stdout)
        
        # 查找生成的模型文件
        model_files = list(output_path.glob("*.obj")) + list(output_path.glob("*.glb"))
        if model_files:
            latest_model = max(model_files, key=lambda f: f.stat().st_mtime)
            print(f"\n[完成] 3D 模型: {latest_model}")
            return str(latest_model)
        else:
            print("[WARNING] 未找到生成的模型文件")
            return None
            
    except subprocess.TimeoutExpired:
        print("[ERROR] InstantMesh 执行超时")
        return None
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}")
        return None


def print_installation_guide():
    """打印 InstantMesh 安装指南"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           InstantMesh 安装指南 (Windows GPU)                 ║
╚══════════════════════════════════════════════════════════════╝

1. 安装 Miniconda:
   https://docs.conda.io/en/latest/miniconda.html

2. 打开 PowerShell，运行:

   # 克隆仓库
   git clone https://github.com/TencentARC/InstantMesh.git
   cd InstantMesh
   
   # 创建环境
   conda create -n instantmesh python=3.10 -y
   conda activate instantmesh
   
   # 安装 PyTorch (CUDA 11.8)
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   
   # 安装依赖
   pip install -r requirements.txt

3. 测试运行:
   python run.py path\\to\\front.png --output_dir outputs

4. 集成到 Cortex3d:
   python instantmesh_client.py front.png --mode local --instantmesh-dir C:\\path\\to\\InstantMesh
""")


def main():
    parser = argparse.ArgumentParser(
        description="InstantMesh 3D 模型生成客户端"
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="输入图片路径 (front view)"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "remote", "guide"],
        default="guide",
        help="运行模式: local=本地GPU, remote=远程服务, guide=显示安装指南"
    )
    parser.add_argument(
        "--instantmesh-dir",
        default=os.environ.get("INSTANTMESH_DIR", ""),
        help="InstantMesh 安装目录 (本地模式)"
    )
    parser.add_argument(
        "--server",
        default=os.environ.get("INSTANTMESH_SERVER", ""),
        help="远程 InstantMesh 服务地址 (远程模式)"
    )
    parser.add_argument(
        "--output", "-o",
        default="outputs",
        help="输出目录"
    )
    parser.add_argument(
        "--conda-env",
        default="instantmesh",
        help="Conda 环境名称"
    )
    
    args = parser.parse_args()
    
    if args.mode == "guide" or not args.image:
        print_installation_guide()
        return 0
    
    if args.mode == "local":
        if not args.instantmesh_dir:
            print("[ERROR] 请指定 InstantMesh 目录: --instantmesh-dir /path/to/InstantMesh")
            return 1
        
        result = run_local_instantmesh(
            image_path=args.image,
            instantmesh_dir=args.instantmesh_dir,
            output_dir=args.output,
            conda_env=args.conda_env
        )
        
        if result:
            print("\n✅ 3D 模型生成成功!")
            return 0
        else:
            print("\n❌ 3D 模型生成失败")
            return 1
    
    elif args.mode == "remote":
        print("[INFO] 远程模式暂未实现")
        print("请使用本地模式: --mode local --instantmesh-dir /path/to/InstantMesh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
