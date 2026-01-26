#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能助手的修图和修复功能
"""

import sys
from pathlib import Path

# 添加scripts目录到路径
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

def test_repair_features():
    """测试修复功能"""
    print("🔧 测试修图和修复功能")
    print("=" * 50)
    
    try:
        from smart_assistant import AdvancedParameterAssistant
        
        # 测试修复相关的用例
        repair_scenarios = [
            {
                "input": "这张照片很模糊，需要修复清晰度",
                "expected": ["image_repair", "quality_issue"]
            },
            {
                "input": "去除背景，只保留人物主体",
                "expected": ["needs_preprocess"]
            },
            {
                "input": "修复这张图片的手部问题，手指数量不对",
                "expected": ["detail_fix", "needs_repair"]
            },
            {
                "input": "把这张照片转换成动漫风格",
                "expected": ["style_transfer", "style"]
            },
            {
                "input": "这张AI生成的图有很多瑕疵，需要整体修复",
                "expected": ["needs_repair", "quality_issue"]
            }
        ]
        
        for i, scenario in enumerate(repair_scenarios, 1):
            print(f"\n📝 测试用例 {i}: {scenario['input']}")
            
            assistant = AdvancedParameterAssistant()
            assistant._analyze_user_intent(scenario['input'].lower())
            
            intent = assistant.context.detected_intent
            scores = assistant.context.confidence_scores
            
            # 检查是否检测到预期的意图
            detected = []
            for key in scenario['expected']:
                if intent.get(key) or scores.get(key, 0) > 0:
                    detected.append(key)
            
            print(f"   检测到的意图: {detected}")
            print(f"   置信度分数: {dict(scores)}")
            
            # 测试模板选择
            template = assistant._select_best_template()
            print(f"   选择的模板: {template}")
            
            # 生成推荐
            try:
                recommendation = assistant._generate_smart_recommendation()
                command = ' '.join(recommendation['command_args'])
                print(f"   推荐命令: {command[:100]}...")
                print(f"   ✅ 成功生成推荐")
            except Exception as e:
                print(f"   ❌ 推荐生成失败: {e}")
        
        print(f"\n🎯 修复功能测试完成！")
        
        # 测试新增的模板
        print(f"\n📋 新增修复模板:")
        templates = assistant.parameter_templates
        repair_templates = ['image_repair', 'detail_fix', 'style_transfer']
        
        for template_name in repair_templates:
            if template_name in templates:
                template = templates[template_name]
                print(f"  ✅ {template['description']} ({template_name})")
                print(f"     基础参数: {' '.join(template['base'])}")
            else:
                print(f"  ❌ 缺少模板: {template_name}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def demo_repair_usage():
    """演示修复功能使用"""
    print(f"\n🎬 修图修复功能演示")
    print("=" * 50)
    
    demo_commands = [
        {
            "name": "🖼️ 图像预处理去背景",
            "command": "python scripts/generate_character.py --input photo.jpg --preprocess --preprocess-model birefnet-general",
            "description": "自动去除背景，提高生成质量"
        },
        {
            "name": "🔧 智能修复补全",
            "command": "python scripts/generate_character.py --input damaged.jpg --auto-complete --max-retries 5",
            "description": "自动检测并修复图像问题"
        },
        {
            "name": "🎯 细节修复模式",
            "command": "python scripts/generate_character.py --mode-refine --refine-details face --detail-issue '眼睛不对称' --from-refine portrait.jpg",
            "description": "精确修复面部细节问题"
        },
        {
            "name": "🎨 风格转换模式",
            "command": "python scripts/generate_character.py --mode-style --style-preset anime --preserve-details --from-style photo.jpg",
            "description": "保持细节的风格转换"
        },
        {
            "name": "🛠️ 元素编辑模式",
            "command": "python scripts/generate_character.py --mode-edit --edit-elements 'remove:背景,modify:提高清晰度' --from-edited source.jpg",
            "description": "添加、移除或修改图像元素"
        },
        {
            "name": "💎 高质量修复流水线",
            "command": "python scripts/generate_character.py --input problem.jpg --preprocess --auto-complete --pro --res 4K",
            "description": "完整的高质量修复处理"
        }
    ]
    
    for demo in demo_commands:
        print(f"\n{demo['name']}:")
        print(f"  💬 功能: {demo['description']}")
        print(f"  📋 命令: {demo['command']}")
    
    print(f"\n✨ 修复功能让图像处理更专业更智能！")

if __name__ == "__main__":
    test_repair_features()
    demo_repair_usage()
    
    print(f"\n🚀 完整使用指南已更新:")
    print("📖 查看: docs/完整参数使用指南.md")
    print("🔧 新增: 图像修复和增强章节")
    print("🧠 智能助手现在支持修图修复对话！")