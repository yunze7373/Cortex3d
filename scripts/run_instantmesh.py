#!/usr/bin/env python3
"""
InstantMesh 调用封装器
支持本地调用和 Hugging Face API 调用

使用方法:
    # Hugging Face Spaces (推荐用于快速测试)
    python run_instantmesh.py --mode hf --input outputs/character_front.png

    # 本地调用 (需要 NVIDIA GPU)
    python run_instantmesh.py --mode local --input outputs/ --instantmesh-dir /path/to/InstantMesh

依赖:
    pip install gradio_client pillow
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, List
import shutil
import tempfile


def run_local_instantmesh(
    input_path: str,
    instantmesh_dir: str,
    output_dir: str,
    config: str = "instant-mesh-large",
    save_video: bool = True
) -> str:
    """
    调用本地部署的 InstantMesh
    
    Args:
        input_path: 输入图片路径
        instantmesh_dir: InstantMesh 安装目录
        output_dir: 输出目录
        config: 使用的配置文件名
        save_video: 是否保存视频
    
    Returns:
        生成的模型文件路径
    """
    import subprocess
    
    instantmesh_path = Path(instantmesh_dir)
    if not instantmesh_path.exists():
        raise ValueError(f"InstantMesh 目录不存在: {instantmesh_dir}")
    
    run_script = instantmesh_path / "run.py"
    config_file = instantmesh_path / "configs" / f"{config}.yaml"
    
    if not run_script.exists():
        raise ValueError(f"未找到 run.py: {run_script}")
    
    cmd = [
        sys.executable, str(run_script),
        str(config_file),
        str(input_path),
    ]
    
    if save_video:
        cmd.append("--save_video")
    
    print(f"[INFO] 运行命令: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        cwd=str(instantmesh_path),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"[ERROR] InstantMesh 执行失败:")
        print(result.stderr)
        raise RuntimeError("InstantMesh 执行失败")
    
    print(result.stdout)
    
    # 查找输出文件 (通常在 outputs/ 目录)
    output_pattern = instantmesh_path / "outputs"
    # 返回最新生成的模型文件
    return str(output_pattern)


def run_huggingface_instantmesh(
    input_image_path: str,
    output_dir: str = "outputs"
) -> Optional[str]:
    """
    使用 Hugging Face Spaces 的 InstantMesh Demo
    
    注意: 这是通过 Gradio Client 调用公共 Space
    
    Args:
        input_image_path: 输入图片路径
        output_dir: 输出目录
    
    Returns:
        下载的模型文件路径
    """
    try:
        from gradio_client import Client, handle_file
    except ImportError:
        raise ImportError(
            "请安装 gradio_client: pip install gradio_client"
        )
    
    print(f"\n{'='*50}")
    print("[InstantMesh via Hugging Face]")
    print(f"{'='*50}")
    print(f"[INFO] 输入图片: {input_image_path}")
    
    # 连接到 Hugging Face Space
    # 官方 Space: TencentARC/InstantMesh
    try:
        client = Client("TencentARC/InstantMesh")
    except Exception as e:
        print(f"[ERROR] 无法连接到 Hugging Face Space: {e}")
        print("[TIP] 请检查网络连接，或访问 https://huggingface.co/spaces/TencentARC/InstantMesh")
        return None
    
    print("[INFO] 已连接到 TencentARC/InstantMesh Space")
    print("[INFO] 开始处理... (可能需要几分钟)")
    
    try:
        # 调用预处理 (check_input_image)
        preprocessed = client.predict(
            input_image=handle_file(input_image_path),
            api_name="/check_input_image"
        )
        print(f"[INFO] 预处理完成")
        
        # 生成多视图 (generate_mvs)
        # 参数: image, sample_steps, sample_seed
        mvs_result = client.predict(
            input_image=handle_file(input_image_path),
            sample_steps=75,  # 采样步数
            sample_seed=42,   # 随机种子
            api_name="/generate_mvs"
        )
        print(f"[INFO] 多视图生成完成")
        
        # 生成 3D 模型 (make3d)
        result = client.predict(
            api_name="/make3d"
        )
        print(f"[INFO] 3D 模型生成完成")
        
        # 处理结果
        # result 通常是一个包含文件路径的元组
        if isinstance(result, (list, tuple)):
            model_path = result[0] if result else None
        else:
            model_path = result
        
        if model_path and os.path.exists(model_path):
            # 复制到输出目录
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            input_stem = Path(input_image_path).stem
            dest_filename = f"{input_stem}_mesh.obj"
            dest_path = output_path / dest_filename
            
            shutil.copy(model_path, dest_path)
            print(f"[保存] 模型已保存到: {dest_path}")
            return str(dest_path)
        else:
            print(f"[WARNING] 未能获取模型文件")
            print(f"[DEBUG] 返回结果: {result}")
            return None
            
    except Exception as e:
        print(f"[ERROR] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def print_manual_instructions():
    """打印手动使用 Hugging Face Demo 的说明"""
    instructions = """
╔══════════════════════════════════════════════════════════════════════╗
║               InstantMesh 手动测试指南                                ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  由于 Mac 没有 NVIDIA GPU，推荐使用 Hugging Face 在线 Demo:           ║
║                                                                      ║
║  1. 打开浏览器访问:                                                   ║
║     https://huggingface.co/spaces/TencentARC/InstantMesh            ║
║                                                                      ║
║  2. 上传处理好的单个视图图片 (推荐使用正面图 front.png)                ║
║                                                                      ║
║  3. 点击 "Generate" 按钮                                             ║
║                                                                      ║
║  4. 等待生成完成后，下载 OBJ 或 GLB 格式的 3D 模型                    ║
║                                                                      ║
║  ⚠️  注意事项:                                                        ║
║  - InstantMesh 设计为单图输入，它会自动生成多视图                     ║
║  - 如果你有 Gemini 生成的多视图，建议使用正面图作为输入               ║
║  - 处理时间约 1-3 分钟，取决于队列情况                                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""
    print(instructions)


def main():
    parser = argparse.ArgumentParser(
        description="InstantMesh 3D 模型生成调用封装"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "hf", "manual"],
        default="manual",
        help="运行模式: local=本地, hf=Hugging Face API, manual=打印手动说明"
    )
    parser.add_argument(
        "--input", "-i",
        help="输入图片路径"
    )
    parser.add_argument(
        "--output", "-o",
        default="outputs",
        help="输出目录"
    )
    parser.add_argument(
        "--instantmesh-dir",
        help="InstantMesh 安装目录 (仅 local 模式需要)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "manual":
        print_manual_instructions()
        return
    
    if not args.input:
        parser.error("--input 参数是必需的")
    
    if args.mode == "local":
        if not args.instantmesh_dir:
            parser.error("local 模式需要指定 --instantmesh-dir")
        run_local_instantmesh(
            args.input,
            args.instantmesh_dir,
            args.output
        )
    elif args.mode == "hf":
        run_huggingface_instantmesh(
            args.input,
            args.output
        )


if __name__ == "__main__":
    main()
