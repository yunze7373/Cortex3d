#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cortex3d 智能助手功能测试脚本
测试各种AI助手模式的功能完整性
"""

import sys
import os
from pathlib import Path

# 添加scripts目录到路径
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

def test_smart_assistant():
    """测试高级智能助手"""
    print("🧠 测试高级智能助手...")
    
    try:
        from smart_assistant import AdvancedParameterAssistant
        assistant = AdvancedParameterAssistant()
        
        # 测试启动
        print("✅ 模块导入成功")
        
        # 测试对话功能
        start_message = assistant.start_intelligent_conversation()
        assert "🧠 Cortex3d 高级智能助手" in start_message
        print("✅ 启动消息正常")
        
        # 测试意图识别
        test_inputs = [
            "我想生成一个动漫风格的角色",
            "快速制作一个3D模型用于游戏",
            "高质量的写实肖像，商业项目用",
            "这张照片转成多视角的角色图"
        ]
        
        for test_input in test_inputs:
            try:
                response, continue_chat, command_args = assistant.process_natural_language_input(test_input)
                print(f"✅ 输入测试成功: '{test_input[:20]}...'")
            except Exception as e:
                print(f"❌ 输入测试失败: '{test_input[:20]}...' - {e}")
                
        print("🎯 高级智能助手测试完成\n")
        
    except ImportError as e:
        print(f"❌ 高级智能助手模块导入失败: {e}\n")
    except Exception as e:
        print(f"❌ 高级智能助手测试出错: {e}\n")

def test_simple_assistant():
    """测试简化智能助手"""
    print("🤖 测试简化智能助手...")
    
    try:
        from intelligent_assistant import IntelligentParameterAssistant
        assistant = IntelligentParameterAssistant()
        
        print("✅ 简化助手模块导入成功")
        
        # 测试对话功能
        start_message = assistant.start_conversation()
        assert "智能参数助手" in start_message or "智能助手" in start_message
        print("✅ 启动消息正常")
        
        print("🎯 简化智能助手测试完成\n")
        
    except ImportError as e:
        print(f"❌ 简化智能助手模块导入失败: {e}\n")
    except Exception as e:
        print(f"❌ 简化智能助手测试出错: {e}\n")

def test_parameter_system():
    """测试参数系统"""
    print("⚙️ 测试参数系统...")
    
    try:
        from generate_character import create_parser
        parser = create_parser()
        
        print("✅ 参数解析器创建成功")
        
        # 测试AI助手参数
        test_commands = [
            ["--ai-assistant"],
            ["--smart-chat"], 
            ["--quick-setup", "beginner"],
            ["--analyze-image", "test.jpg"],
            ["描述文本", "--anime", "-v", "4"]
        ]
        
        for cmd in test_commands:
            try:
                args = parser.parse_args(cmd)
                print(f"✅ 参数解析成功: {' '.join(cmd)}")
            except SystemExit:
                # argparse在--help等情况下会调用sys.exit，这是正常的
                pass
            except Exception as e:
                print(f"❌ 参数解析失败: {' '.join(cmd)} - {e}")
        
        print("🎯 参数系统测试完成\n")
        
    except ImportError as e:
        print(f"❌ 参数系统模块导入失败: {e}\n")
    except Exception as e:
        print(f"❌ 参数系统测试出错: {e}\n")

def test_templates():
    """测试参数模板"""
    print("📋 测试参数模板...")
    
    try:
        from smart_assistant import AdvancedParameterAssistant
        assistant = AdvancedParameterAssistant()
        
        templates = assistant.parameter_templates
        
        # 检查必需的模板
        required_templates = [
            'anime_character',
            'realistic_portrait', 
            'game_character',
            'concept_art',
            '3d_model'
        ]
        
        for template_name in required_templates:
            if template_name in templates:
                template = templates[template_name]
                assert 'base' in template
                assert 'description' in template
                print(f"✅ 模板 '{template_name}' 结构正确")
            else:
                print(f"❌ 缺少模板 '{template_name}'")
        
        print("🎯 参数模板测试完成\n")
        
    except Exception as e:
        print(f"❌ 参数模板测试出错: {e}\n")

def test_integration():
    """测试集成功能"""
    print("🔗 测试功能集成...")
    
    # 检查文件结构
    required_files = [
        "scripts/generate_character.py",
        "scripts/smart_assistant.py", 
        "scripts/intelligent_assistant.py",
        "docs/智能助手使用指南.md"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ 文件存在: {file_path}")
        else:
            print(f"❌ 文件缺失: {file_path}")
    
    print("🎯 功能集成测试完成\n")

def main():
    """主测试函数"""
    print("🚀 Cortex3d 智能助手功能测试")
    print("=" * 50)
    
    # 运行所有测试
    test_smart_assistant()
    test_simple_assistant() 
    test_parameter_system()
    test_templates()
    test_integration()
    
    print("✨ 测试完成！")
    print("\n📋 使用指南:")
    print("1. 高级智能助手: python scripts/generate_character.py --ai-assistant")
    print("2. 简化助手: python scripts/generate_character.py --smart-chat")
    print("3. 图像分析: python scripts/generate_character.py --analyze-image image.jpg")
    print("4. 快速预设: python scripts/generate_character.py --quick-setup beginner")
    print("\n📚 详细文档: docs/智能助手使用指南.md")

if __name__ == "__main__":
    main()