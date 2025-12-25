#!/usr/bin/env python3
"""
完整的端到端生成脚本
从角色描述 → 四视图图片 → 切割后的独立视图

使用方法:
    # 设置 API Key
    export GEMINI_API_KEY="your-api-key"
    
    # 交互模式
    python generate_character.py
    
    # 直接指定描述
    python generate_character.py "赛博朋克女战士，穿着霓虹色装甲"

这是主入口脚本，整合了:
- gemini_generator.py: Gemini API 图像生成
- image_processor.py: 四视图切割和去背景
"""

import argparse
import os
import sys
from pathlib import Path

# 添加 scripts 目录到 path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))


def main():
    parser = argparse.ArgumentParser(
        description="Cortex3d - 从描述生成多视角角色图像"
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="角色描述"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="Gemini API Key"
    )
    parser.add_argument(
        "--output", "-o",
        default="test_images",
        help="输出目录"
    )
    
    args = parser.parse_args()
    
    # Banner
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    Cortex3d 角色生成器                         ║
║         Gemini AI → 四视图图片 → 切割 → 去背景                 ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # 检查 API Key
    if not args.api_key:
        print("[!] 未设置 Gemini API Key")
        print("    请运行: export GEMINI_API_KEY='your-key'")
        print("    或使用: --api-key 参数")
        sys.exit(1)
    
    # 获取角色描述
    if args.description:
        description = args.description
    else:
        print("请输入角色描述 (按 Enter 使用示例):")
        print("示例: 末日幸存者，穿着破旧定制西装的商人，携带手枪")
        print("-" * 50)
        description = input("\n角色描述: ").strip()
        
        if not description:
            description = "末日幸存者，穿着破烂的定制西装，白衬衫沾满血迹和污垢，肩部皮质枪套，表情坚毅疲惫"
            print(f"[使用示例描述] {description}")
    
    # 调用生成器
    from gemini_generator import generate_character_views
    
    result = generate_character_views(
        character_description=description,
        api_key=args.api_key,
        output_dir=args.output,
        auto_cut=True
    )
    
    if result:
        print("\n" + "═" * 50)
        print("✅ 完成!")
        print("═" * 50)
        
        # 列出生成的文件
        output_path = Path(args.output)
        if output_path.exists():
            files = list(output_path.glob("*.png"))
            if files:
                print("\n生成的文件:")
                for f in sorted(files)[-5:]:  # 显示最新的5个
                    print(f"  📷 {f.name}")
        
        print("\n下一步:")
        print("  1. 查看 test_images/ 目录中的图片")
        print("  2. 使用 *_front.png 在 InstantMesh 生成 3D 模型:")
        print("     https://huggingface.co/spaces/TencentARC/InstantMesh")
    else:
        print("\n❌ 生成失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
