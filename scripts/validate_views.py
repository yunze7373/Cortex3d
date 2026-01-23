#!/usr/bin/env python3
"""
Cortex3d 视角验证工具 - 独立命令行版本

用于验证已生成的多视角图片是否包含所有期望的视角，
并自动补全缺失的视角。

使用方法:
    # 仅验证（检测视角但不补全）
    python validate_views.py outputs/xxx.png --views front right back left
    
    # 验证并自动补全
    python validate_views.py outputs/xxx.png --auto-complete
    
    # 验证 6 视角图
    python validate_views.py outputs/xxx.png --preset 6-view
    
    # 使用特定参考图进行补全
    python validate_views.py outputs/xxx.png --auto-complete --reference ref.png --style anime
"""

import argparse
import sys
from pathlib import Path

# 添加 scripts 目录到 path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))


def main():
    parser = argparse.ArgumentParser(
        description="Cortex3d 视角验证与补全工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 验证 4 视角图片
  python validate_views.py test_images/output.png --preset 4-view
  
  # 验证自定义视角
  python validate_views.py output.png --views front left back
  
  # 验证并自动补全缺失视角
  python validate_views.py output.png --auto-complete --reference ref.png
  
  # 只分析（仅检测，不与期望比对）
  python validate_views.py output.png --analyze-only
"""
    )
    
    parser.add_argument(
        "image",
        help="要验证的多视角图片路径"
    )
    
    parser.add_argument(
        "--views",
        nargs="+",
        default=None,
        metavar="VIEW",
        help="期望的视角列表。选项: front, front_right, right, back_right, back, back_left, left, front_left, top, bottom"
    )
    
    parser.add_argument(
        "--preset",
        choices=["4-view", "6-view", "8-view"],
        default=None,
        help="使用预设视角组: 4-view(front/right/back/left), 6-view(+45度角), 8-view(+top/bottom)"
    )
    
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        dest="analyze_only",
        help="仅分析图片中的实际视角，不与期望比对"
    )
    
    parser.add_argument(
        "--auto-complete",
        action="store_true",
        dest="auto_complete",
        help="自动补全缺失的视角"
    )
    
    parser.add_argument(
        "--reference",
        default=None,
        help="用于补全生成的参考图片路径（保持角色一致性）"
    )
    
    parser.add_argument(
        "--style",
        default=None,
        help="风格描述或预设名称（用于补全生成）"
    )
    
    parser.add_argument(
        "--output",
        default=None,
        help="输出目录（默认与输入图片同目录）"
    )
    
    parser.add_argument(
        "--asset-id",
        dest="asset_id",
        default=None,
        help="资源 ID（用于统一命名补全文件）。默认自动从图片名提取"
    )
    
    parser.add_argument(
        "--token",
        default=None,
        help="Gemini API Key（默认使用环境变量 GEMINI_API_KEY）"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        dest="max_retries",
        default=3,
        help="补全的最大重试次数（默认: 3）"
    )
    
    parser.add_argument(
        "--mode",
        choices=["proxy", "direct"],
        default="proxy",
        help="API 调用模式: proxy (通过 AiProxy 代理) 或 direct (直连 Google API)。默认: proxy"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="安静模式，减少输出"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="以 JSON 格式输出结果"
    )
    
    args = parser.parse_args()
    
    # 检查图片是否存在
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[错误] 图片不存在: {args.image}")
        sys.exit(1)
    
    # 确定期望视角
    if args.views:
        expected_views = args.views
    elif args.preset == "8-view":
        expected_views = ["front", "front_right", "right", "back", "back_left", "left", "top", "bottom"]
    elif args.preset == "6-view":
        expected_views = ["front", "front_right", "right", "back", "back_left", "left"]
    elif args.preset == "4-view":
        expected_views = ["front", "right", "back", "left"]
    else:
        # 默认 4 视角
        expected_views = ["front", "right", "back", "left"]
    
    # 导入验证器
    try:
        from view_validator import ViewValidator
    except ImportError as e:
        print(f"[错误] 无法导入验证器: {e}")
        print("       请确保已安装: pip install google-generativeai Pillow")
        sys.exit(1)
    
    # 获取 API Key
    import os
    api_key = args.token or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[错误] 需要 Gemini API Key")
        print("       使用 --token 参数或设置 GEMINI_API_KEY 环境变量")
        sys.exit(1)
    
    # 创建验证器 (遵守 proxy/direct 设置)
    validator = ViewValidator(
        api_key=api_key,
        verbose=not args.quiet,
        mode=args.mode
    )
    
    if not args.quiet:
        print("\n" + "=" * 60)
        print("🔍 Cortex3d 视角验证工具")
        print("=" * 60)
        print(f"  图片: {args.image}")
        print(f"  模式: {args.mode.upper()}")
    
    # 包装验证逻辑，添加优雅的错误处理
    try:
        _run_validation(args, validator, image_path, expected_views)
    except Exception as e:
        error_msg = str(e)
        print(f"\n" + "─" * 50)
        print("⚠️ 验证过程出错")
        print("─" * 50)
        
        # 根据错误类型给出友好提示
        if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
            print("  原因: API Key 无效或未配置")
            if args.mode == "proxy":
                print("  解决: 检查 --token 参数或 AiProxy 服务配置")
            else:
                print("  解决: 设置有效的 GEMINI_API_KEY 环境变量")
        elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
            print("  原因: API 配额耗尽或请求频率过高")
            print("  解决: 稍后重试，或升级 API 配额")
        elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            print("  原因: 网络连接超时")
            print("  解决: 检查网络连接，或稍后重试")
        elif "permission" in error_msg.lower() or "403" in error_msg:
            print("  原因: 权限不足")
            print("  解决: 检查 API Key 是否有正确的权限")
        else:
            # 通用错误，显示简化信息
            print(f"  错误: {error_msg[:200]}")
            if len(error_msg) > 200:
                print("  (错误信息已截断)")
        
        sys.exit(1)


def _run_validation(args, validator, image_path, expected_views):
    """执行实际的验证逻辑（从 main 中提取，便于错误处理）"""
    
    # 仅分析模式
    if args.analyze_only:
        if not args.quiet:
            print("  模式: 仅分析（检测实际视角）")
            print("-" * 60)
        
        analysis = validator.analyze_image(str(image_path))
        
        if args.output_json:
            import json
            output = {
                "image": str(image_path),
                "detected_views": analysis.detected_views,
                "panel_analyses": [
                    {
                        "panel_index": p.panel_index,
                        "detected_view": p.detected_view,
                        "confidence": p.confidence,
                        "description": p.description
                    }
                    for p in analysis.panel_analyses
                ]
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(f"\n检测到 {len(analysis.detected_views)} 个面板:")
            for i, panel in enumerate(analysis.panel_analyses):
                conf_bar = "█" * int(panel.confidence * 10) + "░" * (10 - int(panel.confidence * 10))
                print(f"  [{i+1}] {panel.detected_view:<12} [{conf_bar}] {panel.confidence:.0%}")
                if panel.description:
                    print(f"      └─ {panel.description[:60]}...")
        
        sys.exit(0)
    
    # 验证模式
    if not args.quiet:
        print(f"  期望视角: {expected_views}")
        print(f"  模式: {'验证并补全' if args.auto_complete else '仅验证'}")
        print("-" * 60)
    
    if args.auto_complete:
        # 确定输出目录（默认与输入图片同目录）
        output_dir = args.output if args.output else str(image_path.parent)
        
        # 验证并补全
        result = validator.validate_and_complete(
            image_path=str(image_path),
            expected_views=expected_views,
            reference_image=args.reference,
            style=args.style,
            output_dir=output_dir,
            max_iterations=args.max_retries,
            asset_id=args.asset_id
        )
        
        if args.output_json:
            import json
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("\n" + "=" * 60)
            print("📊 验证与补全结果")
            print("=" * 60)
            
            status_icon = {
                "complete": "✅",
                "partial_completion": "⚠️",
                "has_duplicates": "⚠️",
                "failed": "❌"
            }.get(result["final_status"], "❓")
            
            print(f"  状态: {status_icon} {result['final_status']}")
            print(f"  验证通过: {'是' if result['validation_passed'] else '否'}")
            print(f"  迭代次数: {result['iterations']}")
            
            if result['missing_views']:
                print(f"\n⚠️ 缺失视角: {', '.join(result['missing_views'])}")
            
            if result['generated_panels']:
                print(f"\n📁 生成的补全面板 ({len(result['generated_panels'])} 个):")
                for panel in result['generated_panels']:
                    print(f"  ✓ {panel['view']}: {panel['path']}")
            
            if result['validation_passed']:
                print("\n🎉 所有视角验证通过！")
            else:
                print("\n💡 提示: 可使用以下命令单独生成缺失视角:")
                if result['missing_views']:
                    missing_str = " ".join(result['missing_views'])
                    print(f"   python generate_character.py --from-image {args.reference or args.image} --custom-views {missing_str}")
        
        sys.exit(0 if result['validation_passed'] else 1)
    
    else:
        # 仅验证
        validation = validator.validate(str(image_path), expected_views)
        
        if args.output_json:
            import json
            output = {
                "image": str(image_path),
                "is_complete": validation.is_complete,
                "expected_views": validation.expected_views,
                "detected_views": validation.detected_views,
                "missing_views": validation.missing_views,
                "duplicate_views": validation.duplicate_views,
                "suggestions": validation.suggestions
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print("\n" + "=" * 60)
            print("📊 验证结果")
            print("=" * 60)
            
            print(f"\n  期望: {validation.expected_views}")
            print(f"  检测: {validation.detected_views}")
            
            if validation.missing_views:
                print(f"\n  ❌ 缺失: {', '.join(validation.missing_views)}")
            else:
                print(f"\n  ✅ 无缺失")
            
            if validation.duplicate_views:
                print(f"  ⚠️ 重复: {', '.join(validation.duplicate_views)}")
            
            print(f"\n  验证通过: {'✅ 是' if validation.is_complete else '❌ 否'}")
            
            if validation.suggestions:
                print("\n💡 建议:")
                for s in validation.suggestions:
                    print(f"  - {s}")
            
            if not validation.is_complete:
                print("\n💡 使用 --auto-complete 参数自动补全缺失视角")
        
        sys.exit(0 if validation.is_complete else 1)


if __name__ == "__main__":
    main()
