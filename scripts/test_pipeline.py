#!/usr/bin/env python3
"""
端到端测试脚本
测试完整的 Gemini 多视图 → InstantMesh 3D 模型流程

使用方法:
    python test_pipeline.py test_images/gemini_output.png
"""

import argparse
import os
import sys
from pathlib import Path

# 添加 scripts 目录到 path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from image_processor import process_quadrant_image
from run_instantmesh import print_manual_instructions


def run_pipeline_test(input_image: str, output_dir: str = "outputs"):
    """
    运行完整的测试流程
    
    Args:
        input_image: Gemini 生成的四宫格图片路径
        output_dir: 输出目录
    """
    print("="*60)
    print("Cortex3d 技术测试 - Gemini + InstantMesh Pipeline")
    print("="*60)
    
    # 检查输入文件
    if not os.path.exists(input_image):
        print(f"[错误] 输入文件不存在: {input_image}")
        print("\n请先准备一张 Gemini 生成的四宫格图片，然后重新运行此脚本。")
        print("你可以使用项目中的提示词在 Gemini 中生成四视图图片。")
        return False
    
    # Step 1: 图像处理
    print("\n" + "-"*40)
    print("Step 1: 图像预处理 (切割 + 去背景)")
    print("-"*40)
    
    try:
        output_files = process_quadrant_image(
            input_path=input_image,
            output_dir=output_dir,
            remove_bg_flag=True,
            margin=5
        )
        print(f"\n✅ Step 1 完成! 生成了 {len(output_files)} 个视图文件")
    except Exception as e:
        print(f"\n❌ Step 1 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: InstantMesh 说明
    print("\n" + "-"*40)
    print("Step 2: 使用 InstantMesh 生成 3D 模型")
    print("-"*40)
    
    # 找到正面图 (推荐用于 InstantMesh)
    front_image = None
    for f in output_files:
        if "front" in f.lower():
            front_image = f
            break
    
    if front_image:
        print(f"\n推荐使用正面图进行 3D 生成:")
        print(f"  📷 {front_image}")
    
    print_manual_instructions()
    
    # 生成结果摘要
    print("\n" + "="*60)
    print("测试结果摘要")
    print("="*60)
    print(f"\n📁 输出目录: {os.path.abspath(output_dir)}")
    print("\n生成的视图文件:")
    for f in output_files:
        print(f"  - {os.path.basename(f)}")
    
    print("\n下一步操作:")
    print("  1. 访问 https://huggingface.co/spaces/TencentARC/InstantMesh")
    print(f"  2. 上传 {os.path.basename(front_image) if front_image else '正面图'}")
    print("  3. 点击 Generate 生成 3D 模型")
    print("  4. 下载 OBJ/GLB 模型文件")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Cortex3d 端到端测试脚本"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Gemini 生成的四宫格图片路径"
    )
    parser.add_argument(
        "--output", "-o",
        default="outputs",
        help="输出目录 (默认: outputs)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="使用示例模式 (显示使用说明)"
    )
    
    args = parser.parse_args()
    
    if args.demo or not args.input:
        print("\n" + "="*60)
        print("Cortex3d 技术测试 - 使用说明")
        print("="*60)
        print("""
使用步骤:

1. 使用 Gemini (NanoBanana Pro) 生成四视图图片
   - 使用 2d图生成提示词/ 文件夹中的提示词模板
   - 将生成的四宫格图片保存到 test_images/ 目录

2. 运行此测试脚本:
   python scripts/test_pipeline.py test_images/your_image.png

3. 按照输出的说明使用 InstantMesh 生成 3D 模型

示例:
   python scripts/test_pipeline.py test_images/gemini_survivor.png -o outputs/survivor

""")
        # 列出 test_images 目录下的现有图片
        test_images_dir = script_dir.parent / "test_images"
        if test_images_dir.exists():
            images = list(test_images_dir.glob("*.png")) + list(test_images_dir.glob("*.jpg"))
            if images:
                print("检测到的测试图片:")
                for img in images:
                    print(f"  - {img.name}")
            else:
                print("test_images/ 目录为空，请先添加测试图片。")
        else:
            print("test_images/ 目录不存在，将在首次运行时自动创建。")
        return
    
    success = run_pipeline_test(args.input, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
