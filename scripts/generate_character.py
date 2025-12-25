#!/usr/bin/env python3
"""
Cortex3d - 完整的多视角角色图像生成脚本
支持两种模式:
  1. AiProxy 模式 (推荐) - 通过 bot.bigjj.click/aiproxy 调用 NanoBanana
  2. 直连模式 - 直接调用 Google Gemini API

使用方法:
    # AiProxy 模式 (推荐)
    export AIPROXY_TOKEN="your-token"
    python generate_character.py "赛博朋克女战士"
    
    # 直连 Gemini API 模式
    export GEMINI_API_KEY="your-key"
    python generate_character.py "末日幸存者" --mode direct
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
        "--mode",
        choices=["proxy", "direct"],
        default="proxy",
        help="生成模式: proxy=AiProxy服务, direct=直连Gemini API"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("AIPROXY_TOKEN"),
        help="AiProxy 令牌 (proxy模式)"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="Gemini API Key (direct模式)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="模型名称 (默认: proxy模式用nano-banana-pro, direct模式用gemini-2.0-flash-exp)"
    )
    parser.add_argument(
        "--output", "-o",
        default="test_images",
        help="输出目录"
    )
    parser.add_argument(
        "--no-cut",
        action="store_true",
        help="不自动切割"
    )
    
    args = parser.parse_args()
    
    # Banner
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    Cortex3d 角色生成器                         ║
║         AI 多视角图像生成 → 切割 → 去背景                      ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # 检查认证
    if args.mode == "proxy":
        if not args.token:
            print("[!] 未设置 AiProxy 令牌")
            print("    请运行: export AIPROXY_TOKEN='your-token'")
            print("    或使用: --mode direct 直连 Gemini API")
            sys.exit(1)
        model = args.model or "models/nano-banana-pro-preview"
        print(f"[模式] AiProxy (bot.bigjj.click/aiproxy)")
    else:
        if not args.api_key:
            print("[!] 未设置 Gemini API Key")
            print("    请运行: export GEMINI_API_KEY='your-key'")
            sys.exit(1)
        model = args.model or "gemini-2.0-flash-exp"
        print(f"[模式] 直连 Gemini API")
    
    print(f"[模型] {model}")
    
    # 获取角色描述
    if args.description:
        description = args.description
    else:
        print("\n请输入角色描述 (按 Enter 使用示例):")
        print("示例: 末日幸存者，穿着破旧定制西装的商人，携带手枪")
        print("-" * 50)
        description = input("\n角色描述: ").strip()
        
        if not description:
            description = "末日幸存者，穿着破烂的定制西装，白衬衫沾满血迹和污垢，肩部皮质枪套，表情坚毅疲惫"
            print(f"[使用示例描述] {description}")
    
    # 调用生成器
    if args.mode == "proxy":
        from aiproxy_client import generate_character_multiview
        result = generate_character_multiview(
            character_description=description,
            token=args.token,
            output_dir=args.output,
            auto_cut=not args.no_cut,
            model=model
        )
    else:
        from gemini_generator import generate_character_views
        result = generate_character_views(
            character_description=description,
            api_key=args.api_key,
            model_name=model,
            output_dir=args.output,
            auto_cut=not args.no_cut
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
                for f in sorted(files)[-5:]:
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
