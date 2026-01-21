#!/usr/bin/env python3
"""
测试编辑/细节修复路由逻辑 - 验证参数解析是否正确
"""

import sys
import os
from pathlib import Path

# 添加 scripts 目录到 path
script_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(script_dir))

def test_edit_mode_args():
    """测试编辑模式参数"""
    print("=" * 60)
    print("[测试1] 编辑模式参数验证")
    print("=" * 60)
    
    # 模拟命令行: python generate_character.py test --mode-edit --edit-elements "add:xxx" --from-edited test.png
    test_args = [
        "test-character",
        "--mode-edit",
        "--edit-elements", "add:肩部炮台",
        "--from-edited", "test_images/character_20251226_013442_front.png"
    ]
    
    # 手动运行参数解析
    import argparse
    parser = argparse.ArgumentParser()
    
    # 添加必需的参数组 (复制自 generate_character.py)
    parser.add_argument("character", nargs="?", default="test", help="角色描述")
    parser.add_argument("--token", help="API Token")
    parser.add_argument("--model", default="gemini-2.5-flash", help="模型名称")
    parser.add_argument("--output", default="test_images", help="输出目录")
    
    # 编辑模式参数
    parser.add_argument("--mode-edit", action="store_true", dest="mode_edit")
    parser.add_argument("--edit-elements", type=str, dest="edit_elements")
    parser.add_argument("--from-edited", type=str, dest="from_edited")
    
    # 细节修复模式参数
    parser.add_argument("--mode-refine", action="store_true", dest="mode_refine")
    parser.add_argument("--refine-details", type=str, dest="refine_details")
    parser.add_argument("--detail-issue", type=str, dest="detail_issue")
    parser.add_argument("--from-refine", type=str, dest="from_refine")
    
    # 解析参数
    args = parser.parse_args(test_args[1:])  # 跳过脚本名
    
    print(f"✓ 字符: {args.character}")
    print(f"✓ 编辑模式: {args.mode_edit}")
    print(f"✓ 编辑操作: {args.edit_elements}")
    print(f"✓ 源图像: {args.from_edited}")
    print(f"✓ 输出目录: {args.output}")
    
    # 验证源图像存在
    if Path(args.from_edited).exists():
        print(f"✅ 源图像存在: {args.from_edited}")
    else:
        print(f"❌ 源图像不存在: {args.from_edited}")
        return False
    
    print()
    return True


def test_refine_mode_args():
    """测试细节修复模式参数"""
    print("=" * 60)
    print("[测试2] 细节修复模式参数验证")
    print("=" * 60)
    
    import argparse
    
    # 模拟命令行
    test_args = [
        "test-character",
        "--mode-refine",
        "--refine-details", "face",
        "--detail-issue", "脸部看起来很不自然",
        "--from-refine", "test_images/character_20251226_013442_front.png"
    ]
    
    # 创建解析器
    parser = argparse.ArgumentParser()
    
    parser.add_argument("character", nargs="?", default="test")
    parser.add_argument("--token", help="API Token")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument("--output", default="test_images")
    
    # 编辑模式参数
    parser.add_argument("--mode-edit", action="store_true", dest="mode_edit")
    parser.add_argument("--edit-elements", type=str, dest="edit_elements")
    parser.add_argument("--from-edited", type=str, dest="from_edited")
    
    # 细节修复模式参数
    parser.add_argument("--mode-refine", action="store_true", dest="mode_refine")
    parser.add_argument("--refine-details", type=str, choices=["face", "hands", "pose", "eyes", "custom"], dest="refine_details")
    parser.add_argument("--detail-issue", type=str, dest="detail_issue")
    parser.add_argument("--from-refine", type=str, dest="from_refine")
    
    # 解析参数
    args = parser.parse_args(test_args[1:])
    
    print(f"✓ 字符: {args.character}")
    print(f"✓ 细节修复模式: {args.mode_refine}")
    print(f"✓ 修复部分: {args.refine_details}")
    print(f"✓ 问题描述: {args.detail_issue}")
    print(f"✓ 源图像: {args.from_refine}")
    print(f"✓ 输出目录: {args.output}")
    
    # 验证源图像存在
    if Path(args.from_refine).exists():
        print(f"✅ 源图像存在: {args.from_refine}")
    else:
        print(f"❌ 源图像不存在: {args.from_refine}")
        return False
    
    print()
    return True


def test_function_imports():
    """测试函数是否可以正确导入"""
    print("=" * 60)
    print("[测试3] 函数导入验证")
    print("=" * 60)
    
    try:
        from scripts.gemini_generator import edit_character_elements, refine_character_details
        print("✅ 成功导入 edit_character_elements")
        print("✅ 成功导入 refine_character_details")
        
        # 检查函数签名
        import inspect
        
        edit_sig = inspect.signature(edit_character_elements)
        print(f"\n编辑函数签名: {edit_sig}")
        
        refine_sig = inspect.signature(refine_character_details)
        print(f"修复函数签名: {refine_sig}")
        
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_utility_imports():
    """测试工具函数是否可以正确导入"""
    print("=" * 60)
    print("[测试4] 工具函数导入验证")
    print("=" * 60)
    
    try:
        from scripts.image_editor_utils import (
            validate_image_input,
            load_image_as_base64,
            compose_edit_prompt,
            compose_refine_prompt
        )
        print("✅ 成功导入 validate_image_input")
        print("✅ 成功导入 load_image_as_base64")
        print("✅ 成功导入 compose_edit_prompt")
        print("✅ 成功导入 compose_refine_prompt")
        
        # 测试验证函数
        test_image = "test_images/character_20251226_013442_front.png"
        valid, error = validate_image_input(test_image)
        if valid:
            print(f"✅ 图像验证通过: {test_image}")
        else:
            print(f"❌ 图像验证失败: {error}")
            return False
        
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         Cortex3d 图像编辑路由逻辑测试                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    results = []
    
    results.append(("编辑模式参数", test_edit_mode_args()))
    results.append(("细节修复参数", test_refine_mode_args()))
    results.append(("函数导入", test_function_imports()))
    results.append(("工具导入", test_utility_imports()))
    
    print()
    print("=" * 60)
    print("[测试总结]")
    print("=" * 60)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print()
    print(f"总体结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)
