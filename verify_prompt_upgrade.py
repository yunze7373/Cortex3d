#!/usr/bin/env python3
"""
验证四面图提示词改进是否已正确应用的脚本

用法:
    python verify_prompt_upgrade.py
    
检查项:
    - config.py 中的三个模板是否已更新
    - 关键短语是否已包含在提示词中
    - 文件是否已创建
"""

import os
import sys
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DOCS_DIR = PROJECT_ROOT / "docs"
PROMPTS_DIR = PROJECT_ROOT / "2d图生成提示词"

# 关键短语检查列表
KEY_PHRASES = {
    "认知框架": [
        "STATIC OBJECT",
        "GEOMETRIC CAMERA ORBIT TASK",
        "not a character redesign task"
    ],
    "相机约束": [
        "fixed radius and height",
        "Camera target is the subject's original center",
        "The subject does NOT rotate"
    ],
    "空间锁定": [
        "ABSOLUTE SPATIAL LOCK",
        "MUST remain 100% IDENTICAL",
        "NO eye contact correction"
    ],
    "禁止项": [
        "DO NOT adjust pose for visibility",
        "DO NOT rotate body to face the camera",
        "DO NOT \"fix\" anatomy per view"
    ],
    "背景": [
        "Pure neutral gray or white background",
        "Seamless, studio-style environment",
        "No visible floor, horizon, ground texture"
    ],
    "配置参数": [
        "Resolution: 4K",
        "Aspect Ratio: 3:2",
        "Sampling: deterministic"
    ],
    "最终约束": [
        "Failure to follow these rules is unacceptable"
    ]
}

def check_file_content(filepath, phrases_dict, name):
    """检查文件是否包含所有关键短语"""
    print(f"\n📋 检查: {name}")
    print(f"   文件: {filepath}")
    
    if not filepath.exists():
        print(f"   ❌ 文件不存在!")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"   ❌ 无法读取文件: {e}")
        return False
    
    all_found = True
    for category, phrases in phrases_dict.items():
        print(f"\n   📌 {category}:")
        for phrase in phrases:
            if phrase in content:
                print(f"      ✅ 找到: \"{phrase}\"")
            else:
                print(f"      ❌ 缺失: \"{phrase}\"")
                all_found = False
    
    return all_found

def check_template_functions(config_file):
    """检查 config.py 中的三个模板函数"""
    print(f"\n📋 检查模板函数")
    print(f"   文件: {config_file}")
    
    if not config_file.exists():
        print(f"   ❌ 文件不存在!")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"   ❌ 无法读取文件: {e}")
        return False
    
    templates = [
        "_LEGACY_MULTIVIEW_TEMPLATE",
        "_LEGACY_IMAGE_REF_TEMPLATE",
        "_LEGACY_STRICT_COPY_TEMPLATE"
    ]
    
    all_found = True
    for template in templates:
        if template in content:
            print(f"   ✅ 找到模板: {template}")
        else:
            print(f"   ❌ 缺失模板: {template}")
            all_found = False
    
    return all_found

def check_files_exist(files_dict):
    """检查必要的文件是否已创建"""
    print(f"\n📋 检查文件是否存在")
    
    all_exist = True
    for name, filepath in files_dict.items():
        if filepath.exists():
            print(f"   ✅ {name}")
            # 显示文件大小
            size = filepath.stat().st_size
            if size > 1000:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} bytes"
            print(f"      大小: {size_str}")
        else:
            print(f"   ❌ {name} - 不存在")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("🔍 四面图提示词改进验证脚本")
    print("=" * 60)
    
    results = {}
    
    # 1. 检查 config.py 中的模板
    config_file = SCRIPTS_DIR / "config.py"
    results["config.py 模板函数"] = check_template_functions(config_file)
    
    # 2. 检查 config.py 中的关键内容
    results["config.py 内容"] = check_file_content(
        config_file,
        KEY_PHRASES,
        "scripts/config.py 中的提示词内容"
    )
    
    # 3. 检查文件是否存在
    files_to_check = {
        "分析文档": DOCS_DIR / "PROMPT_IMPROVEMENT_ANALYSIS.md",
        "升级指南": DOCS_DIR / "PROMPT_UPGRADE_GUIDE.md",
        "快速参考": DOCS_DIR / "PROMPT_QUICK_REFERENCE.md",
        "英文v3.0样本": PROMPTS_DIR / "英文4视角提示词sample_v3.0.md",
        "中文v3.0样本": PROMPTS_DIR / "中文4视角提示词sample_v3.0.md",
    }
    
    results["文件创建"] = check_files_exist(files_to_check)
    
    # 4. 检查新建文件的内容
    print(f"\n📋 检查新建文件的内容")
    
    v3_english = PROMPTS_DIR / "英文4视角提示词sample_v3.0.md"
    if v3_english.exists():
        print(f"   ✅ 检查英文v3.0样本...")
        results["英文样本内容"] = check_file_content(
            v3_english,
            KEY_PHRASES,
            "英文4视角提示词sample_v3.0.md"
        )
    
    v3_chinese = PROMPTS_DIR / "中文4视角提示词sample_v3.0.md"
    if v3_chinese.exists():
        print(f"   ✅ 检查中文v3.0样本...")
        # 中文版本的关键短语
        cn_phrases = {
            "认知框架": ["静态物体", "几何摄像机环绕任务", "不是角色再设计"],
            "相机约束": ["固定的半径和高度", "摄像机目标是主体的原始中心点"],
            "空间锁定": ["绝对空间锁定"],
            "禁止项": ["不允许为了可见性调整姿态", "不允许旋转身体面向摄像机"],
        }
        results["中文样本内容"] = check_file_content(
            v3_chinese,
            cn_phrases,
            "中文4视角提示词sample_v3.0.md"
        )
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 验证结果总结")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {check_name}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print(f"🎉 所有检查都通过了！({passed}/{total})")
        print("\n✅ 四面图提示词改进已正确应用！")
        print("\n接下来可以:")
        print("   1. 运行 python scripts/gemini_generator.py 生成四面图")
        print("   2. 查看 docs/PROMPT_QUICK_REFERENCE.md 了解快速使用")
        print("   3. 查看 docs/PROMPT_IMPROVEMENT_ANALYSIS.md 了解详细改进")
        return 0
    else:
        print(f"⚠️  部分检查失败 ({passed}/{total})")
        print("\n请检查以下内容:")
        for check_name, result in results.items():
            if not result:
                print(f"   - {check_name}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
