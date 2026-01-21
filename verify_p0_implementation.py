#!/usr/bin/env python3
"""
P0 阶段实现完成验证清单
验证所有必需的组件是否已正确实现
"""

import sys
import os
from pathlib import Path

def check_file_exists(path, desc):
    """检查文件是否存在"""
    p = Path(path)
    if p.exists():
        size = p.stat().st_size
        print(f"✅ {desc}: {path} ({size} bytes)")
        return True
    else:
        print(f"❌ {desc}: {path} (NOT FOUND)")
        return False

def check_function_exists(file_path, func_name):
    """检查函数是否在文件中定义"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if f'def {func_name}(' in content:
                print(f"✅ 函数 {func_name} 在 {file_path} 中")
                return True
            else:
                print(f"❌ 函数 {func_name} 在 {file_path} 中 (NOT FOUND)")
                return False
    except Exception as e:
        print(f"❌ 无法读取 {file_path}: {e}")
        return False

def check_import_available(module_name, import_name):
    """检查导入是否可用"""
    try:
        exec(f"from {module_name} import {import_name}")
        print(f"✅ 可以导入 {import_name} from {module_name}")
        return True
    except ImportError as e:
        print(f"❌ 无法导入 {import_name} from {module_name}: {e}")
        return False

def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         Cortex3d P0 阶段实现完成验证清单                     ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    
    results = {}
    
    # =========================================================================
    print("[1️⃣ 文件完整性检查]")
    print("-" * 60)
    results['files'] = [
        check_file_exists('scripts/image_editor_utils.py', '图像编辑工具库'),
        check_file_exists('scripts/gemini_generator.py', 'Gemini 生成器'),
        check_file_exists('scripts/generate_character.py', '主 CLI 脚本'),
        check_file_exists('docs/IMAGE_EDITING_QUICKSTART.md', '快速开始文档'),
        check_file_exists('docs/P0_IMPLEMENTATION_SUMMARY.md', 'P0 实现总结'),
        check_file_exists('docs/GEMINI_IMAGE_EDITING_INTEGRATION.md', '完整设计文档'),
        check_file_exists('docs/GEMINI_IMAGE_EDITING_CHEATSHEET.md', '快速参考'),
        check_file_exists('test_edit_routing.py', '路由逻辑测试'),
    ]
    print()
    
    # =========================================================================
    print("[2️⃣ 函数实现检查]")
    print("-" * 60)
    results['functions'] = [
        check_function_exists('scripts/image_editor_utils.py', 'validate_image_input'),
        check_function_exists('scripts/image_editor_utils.py', 'load_image_as_base64'),
        check_function_exists('scripts/image_editor_utils.py', 'compose_edit_prompt'),
        check_function_exists('scripts/image_editor_utils.py', 'compose_refine_prompt'),
        check_function_exists('scripts/gemini_generator.py', 'edit_character_elements'),
        check_function_exists('scripts/gemini_generator.py', 'refine_character_details'),
    ]
    print()
    
    # =========================================================================
    print("[3️⃣ CLI 参数检查]")
    print("-" * 60)
    try:
        with open('scripts/generate_character.py', 'r', encoding='utf-8') as f:
            content = f.read()
            params = {
                '--mode-edit': '--mode-edit' in content,
                '--edit-elements': '--edit-elements' in content,
                '--from-edited': '--from-edited' in content,
                '--mode-refine': '--mode-refine' in content,
                '--refine-details': '--refine-details' in content,
                '--detail-issue': '--detail-issue' in content,
                '--from-refine': '--from-refine' in content,
            }
            
            results['cli_params'] = []
            for param, found in params.items():
                if found:
                    print(f"✅ 参数 {param} 已定义")
                    results['cli_params'].append(True)
                else:
                    print(f"❌ 参数 {param} 未找到")
                    results['cli_params'].append(False)
    except Exception as e:
        print(f"❌ 无法检查 CLI 参数: {e}")
        results['cli_params'] = [False]
    print()
    
    # =========================================================================
    print("[4️⃣ 路由逻辑检查]")
    print("-" * 60)
    try:
        with open('scripts/generate_character.py', 'r', encoding='utf-8') as f:
            content = f.read()
            checks = {
                'if args.mode_edit:': 'args.mode_edit 路由检查' in content or 'if args.mode_edit:' in content,
                'if args.mode_refine:': 'args.mode_refine 路由检查' in content or 'if args.mode_refine:' in content,
                'edit_character_elements': 'edit_character_elements 函数调用' in content or 'edit_character_elements(' in content,
                'refine_character_details': 'refine_character_details 函数调用' in content or 'refine_character_details(' in content,
            }
            
            results['routing'] = []
            for check, desc in zip(checks.keys(), checks.values()):
                if check in content:
                    print(f"✅ {check} 已实现")
                    results['routing'].append(True)
                else:
                    print(f"❌ {check} 未找到")
                    results['routing'].append(False)
    except Exception as e:
        print(f"❌ 无法检查路由逻辑: {e}")
        results['routing'] = [False]
    print()
    
    # =========================================================================
    print("[5️⃣ 导入可用性检查]")
    print("-" * 60)
    
    # 添加 scripts 目录到 path
    sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
    
    results['imports'] = [
        check_import_available('image_editor_utils', 'validate_image_input'),
        check_import_available('image_editor_utils', 'compose_edit_prompt'),
        check_import_available('image_editor_utils', 'EditSession'),
        check_import_available('gemini_generator', 'edit_character_elements'),
        check_import_available('gemini_generator', 'refine_character_details'),
    ]
    print()
    
    # =========================================================================
    print("[6️⃣ 文档完整性检查]")
    print("-" * 60)
    
    docs = {
        'docs/IMAGE_EDITING_QUICKSTART.md': ['编辑模式', '细节修复模式', '使用示例'],
        'docs/P0_IMPLEMENTATION_SUMMARY.md': ['完成情况', '实现的功能', '下一步工作'],
        'docs/GEMINI_IMAGE_EDITING_INTEGRATION.md': ['设计方案', '优先级', '实现路径'],
    }
    
    results['docs'] = []
    for doc, keywords in docs.items():
        try:
            with open(doc, 'r', encoding='utf-8') as f:
                content = f.read()
                found_all = all(kw in content for kw in keywords)
                if found_all:
                    print(f"✅ {doc} 包含所有必需内容")
                    results['docs'].append(True)
                else:
                    print(f"⚠️  {doc} 缺少部分内容")
                    results['docs'].append(False)
        except Exception as e:
            print(f"❌ 无法读取 {doc}: {e}")
            results['docs'].append(False)
    print()
    
    # =========================================================================
    print("[总体评分]")
    print("-" * 60)
    
    all_results = [
        results.get('files', []),
        results.get('functions', []),
        results.get('cli_params', []),
        results.get('routing', []),
        results.get('imports', []),
        results.get('docs', []),
    ]
    
    total_checks = sum(len(r) for r in all_results)
    passed_checks = sum(sum(r) for r in all_results)
    
    categories = [
        ('文件完整性', results.get('files', []), 8),
        ('函数实现', results.get('functions', []), 6),
        ('CLI 参数', results.get('cli_params', []), 7),
        ('路由逻辑', results.get('routing', []), 4),
        ('导入可用性', results.get('imports', []), 5),
        ('文档完整性', results.get('docs', []), 3),
    ]
    
    for name, checks, expected in categories:
        passed = sum(checks) if checks else 0
        total = len(checks) if checks else expected
        percent = (passed / total * 100) if total > 0 else 0
        status = "✅" if passed == total else "⚠️ " if passed >= total * 0.8 else "❌"
        print(f"{status} {name}: {passed}/{total} ({percent:.0f}%)")
    
    print()
    print("="*60)
    overall_percent = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    print(f"总体完成度: {passed_checks}/{total_checks} ({overall_percent:.1f}%)")
    print("="*60)
    print()
    
    if overall_percent >= 95:
        print("🎉 ✅ P0 阶段实现已完成且验证通过！")
        print()
        print("后续可进行:")
        print("  1. 真实 API 测试 (需要有效的 Gemini API Key)")
        print("  2. 批量图像处理")
        print("  3. P1 阶段功能实现 (风格转换、图像合成)")
        return 0
    elif overall_percent >= 80:
        print("⚠️  P0 阶段大部分实现已完成，但有些检查失败")
        print("请检查上面的失败项并修正")
        return 1
    else:
        print("❌ P0 阶段实现不完整")
        print("请完成所有必需的组件")
        return 1

if __name__ == "__main__":
    sys.exit(main())
