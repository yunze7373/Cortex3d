#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cortex3d 智能参数助手
通过AI多轮对话帮助用户生成最合适的参数组合
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class UserExperience(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"

class GenerationPurpose(Enum):
    PERSONAL_USE = "personal"
    COMMERCIAL = "commercial"
    LEARNING = "learning"
    PRODUCTION = "production"

@dataclass
class UserIntent:
    """用户意图分析结果"""
    purpose: GenerationPurpose
    experience_level: UserExperience
    has_reference_image: bool
    desired_style: Optional[str]
    target_quality: str  # "fast", "balanced", "high", "ultra"
    needs_3d: bool
    needs_multiple_views: bool
    specific_requirements: List[str]
    time_budget: str  # "urgent", "normal", "unlimited"

@dataclass
class ParameterRecommendation:
    """参数推荐结果"""
    command_args: List[str]
    explanation: str
    estimated_time: str
    quality_level: str
    alternatives: List[Dict[str, str]]

class IntelligentParameterAssistant:
    def __init__(self):
        self.conversation_history = []
        self.user_intent = None
        
    def start_conversation(self) -> str:
        """开始智能对话"""
        welcome_msg = """
🤖 Cortex3d 智能参数助手
────────────────────────────

👋 欢迎！我将通过几个简单问题来帮您选择最佳的生成参数。

让我们开始吧！请告诉我：
1️⃣ 您想要生成什么类型的角色？
   - 可以描述角色外观（如"赛博朋克女战士"）
   - 或者告诉我您有参考图片

💡 提示：您也可以直接说"我有一张照片想转成动漫风格"这样的需求
        """
        return welcome_msg
    
    def analyze_user_input(self, user_input: str) -> Tuple[str, bool]:
        """分析用户输入并返回响应和是否需要继续对话"""
        
        self.conversation_history.append({"user": user_input})
        
        # 简化版意图识别（实际可以用更复杂的NLP）
        user_input_lower = user_input.lower()
        
        # 第一轮：了解基本需求
        if len(self.conversation_history) == 1:
            return self._handle_initial_input(user_input_lower)
        
        # 后续轮次：细化参数
        return self._handle_followup_input(user_input_lower)
    
    def _handle_initial_input(self, user_input: str) -> Tuple[str, bool]:
        """处理初始输入"""
        
        # 检测是否有参考图片
        has_image = any(word in user_input for word in ["图片", "照片", "图像", "photo", "image", "picture"])
        
        # 检测风格倾向
        style_keywords = {
            "动漫": "anime", "anime": "anime",
            "写实": "photorealistic", "真实": "photorealistic", "照片": "photorealistic",
            "像素": "pixel", "pixel": "pixel", "8bit": "pixel",
            "赛博朋克": "cyberpunk", "cyberpunk": "cyberpunk",
            "水彩": "watercolor", "油画": "oil",
            "卡通": "3d-toon", "3d": "3d-toon"
        }
        
        detected_style = None
        for keyword, style in style_keywords.items():
            if keyword in user_input:
                detected_style = style
                break
        
        # 检测3D需求
        needs_3d = any(word in user_input for word in ["3d", "三维", "立体", "模型", "打印"])
        
        response = f"""
✅ 了解！您想要生成：{user_input}

现在让我了解更多细节：

2️⃣ 您的使用目的是什么？
   A) 个人娱乐/学习 
   B) 商业用途/项目
   C) 专业制作/高质量需求

3️⃣ 您对时间和质量的偏好？
   A) 快速预览（几分钟，中等质量）
   B) 平衡模式（正常时间，好质量）
   C) 高质量模式（较长时间，最佳效果）

请回复对应字母，如 "A, B" 或直接描述您的需求。
        """
        
        if has_image:
            response += "\n💡 我注意到您提到了图片，稍后我会询问图片相关的处理方式。"
        
        if detected_style:
            response += f"\n🎨 我检测到您可能喜欢 {detected_style} 风格，稍后会为您优化相关参数。"
        
        return response, True
    
    def _handle_followup_input(self, user_input: str) -> Tuple[str, bool]:
        """处理后续输入"""
        
        # 解析用户选择
        purpose = GenerationPurpose.PERSONAL_USE
        quality = "balanced"
        
        if "a" in user_input and "个人" in user_input or "娱乐" in user_input:
            purpose = GenerationPurpose.PERSONAL_USE
        elif "b" in user_input or "商业" in user_input:
            purpose = GenerationPurpose.COMMERCIAL  
        elif "c" in user_input or "专业" in user_input or "高质量" in user_input:
            purpose = GenerationPurpose.PRODUCTION
            
        if "a" in user_input and ("快" in user_input or "预览" in user_input):
            quality = "fast"
        elif "b" in user_input or "平衡" in user_input:
            quality = "balanced"
        elif "c" in user_input or "高质量" in user_input:
            quality = "high"
            
        # 生成推荐
        recommendation = self._generate_recommendation(purpose, quality)
        
        return self._format_recommendation(recommendation), False
    
    def _generate_recommendation(self, purpose: GenerationPurpose, quality: str) -> ParameterRecommendation:
        """生成参数推荐"""
        
        base_args = ["python", "scripts/generate_character.py"]
        
        # 根据历史对话分析用户需求
        user_description = self.conversation_history[0]["user"]
        
        # 检测各种需求
        has_image = any(word in user_description.lower() for word in ["图片", "照片", "图像", "photo", "image"])
        needs_3d = any(word in user_description.lower() for word in ["3d", "三维", "立体", "模型"])
        
        # 风格检测
        style_map = {
            "动漫": "--anime", "anime": "--anime",
            "写实": "--photorealistic", "真实": "--photorealistic", 
            "像素": "--pixel", "pixel": "--pixel",
            "赛博朋克": "--cyberpunk", "cyberpunk": "--cyberpunk",
            "水彩": "--watercolor", "油画": "--oil",
            "卡通": "--3d-toon"
        }
        
        style_arg = None
        for keyword, arg in style_map.items():
            if keyword in user_description.lower():
                style_arg = arg
                break
        
        # 构建推荐参数
        if not has_image:
            # 纯文本生成
            base_args.append(f'"{user_description}"')
        else:
            # 图像参考生成
            base_args.extend(["--input", "your_image.jpg"])
            
        # 添加风格
        if style_arg:
            base_args.append(style_arg)
        else:
            base_args.append("--anime")  # 默认动漫风格
            
        # 根据质量需求添加参数
        if quality == "fast":
            base_args.extend(["--res", "1K", "--views", "4"])
            estimated_time = "2-5分钟"
            quality_level = "中等质量，快速预览"
        elif quality == "balanced":
            base_args.extend(["--res", "2K", "-v", "6"])
            estimated_time = "5-10分钟"
            quality_level = "良好质量，平衡模式"
        else:  # high quality
            base_args.extend(["--pro", "--res", "4K", "-v", "8"])
            estimated_time = "10-20分钟"
            quality_level = "最高质量，专业模式"
            
        # 根据用途添加参数
        if purpose == GenerationPurpose.PRODUCTION:
            base_args.append("--smart-fix")  # 自动补全
            
        # 3D需求
        if needs_3d:
            base_args.append("--3d")
            if quality == "fast":
                base_args.append("--fast-3d")
            elif quality == "high":
                base_args.extend(["--algo", "trellis2", "--3d-quality", "ultra"])
                
        # 添加预览
        base_args.append("--preview")
        
        # 生成说明
        explanation = self._generate_explanation(base_args, purpose, quality, has_image, needs_3d, style_arg)
        
        # 生成替代方案
        alternatives = self._generate_alternatives(base_args, quality)
        
        return ParameterRecommendation(
            command_args=base_args,
            explanation=explanation,
            estimated_time=estimated_time,
            quality_level=quality_level,
            alternatives=alternatives
        )
    
    def _generate_explanation(self, args: List[str], purpose, quality, has_image, needs_3d, style) -> str:
        """生成参数解释"""
        
        explanations = []
        
        if has_image:
            explanations.append("📥 使用图像参考模式，从您的图片中提取角色特征")
        
        if style:
            style_names = {
                "--anime": "日式动漫",
                "--photorealistic": "写实摄影",
                "--pixel": "像素艺术", 
                "--cyberpunk": "赛博朋克",
                "--watercolor": "水彩画",
                "--3d-toon": "3D卡通"
            }
            explanations.append(f"🎨 应用{style_names.get(style, style)}风格")
            
        if quality == "fast":
            explanations.append("⚡ 快速模式：1K分辨率，4视角，适合快速预览")
        elif quality == "balanced":
            explanations.append("⚖️ 平衡模式：2K分辨率，6视角，质量与速度平衡")
        else:
            explanations.append("💎 高质量模式：4K分辨率，Pro模型，8视角，专业级效果")
            
        if needs_3d:
            explanations.append("🚀 启用3D转换，自动生成三维模型")
            
        if "--smart-fix" in args:
            explanations.append("🔍 启用智能补全，自动检测和修复缺失视角")
            
        explanations.append("👀 启用自动预览，生成完成后立即查看结果")
        
        return "\n".join(f"  {exp}" for exp in explanations)
    
    def _generate_alternatives(self, base_args: List[str], quality: str) -> List[Dict[str, str]]:
        """生成替代方案"""
        
        alternatives = []
        
        # 速度优化版本
        if quality != "fast":
            fast_args = [arg for arg in base_args]
            # 替换质量参数
            for i, arg in enumerate(fast_args):
                if arg in ["--pro", "--res", "--4K", "-v", "8"]:
                    if arg == "--res" and i + 1 < len(fast_args):
                        fast_args[i + 1] = "1K"
                    elif arg == "-v" and i + 1 < len(fast_args):
                        fast_args[i + 1] = "4"
                    elif arg == "--pro":
                        fast_args.remove(arg)
                        
            alternatives.append({
                "name": "⚡ 快速版本",
                "command": " ".join(fast_args),
                "description": "降低质量，提升速度，适合测试"
            })
        
        # 质量优化版本
        if quality != "high":
            quality_args = [arg for arg in base_args]
            if "--pro" not in quality_args:
                quality_args.insert(-1, "--pro")
            if "--res" in quality_args:
                res_index = quality_args.index("--res")
                if res_index + 1 < len(quality_args):
                    quality_args[res_index + 1] = "4K"
                    
            alternatives.append({
                "name": "💎 高质量版本", 
                "command": " ".join(quality_args),
                "description": "最佳效果，适合重要项目"
            })
            
        # 本地模式版本
        local_args = [arg for arg in base_args]
        local_args.insert(-2, "--mode")
        local_args.insert(-2, "local")
        
        alternatives.append({
            "name": "🏠 本地模式",
            "command": " ".join(local_args),
            "description": "使用本地服务，无需网络，速度更快"
        })
        
        return alternatives
    
    def _format_recommendation(self, rec: ParameterRecommendation) -> str:
        """格式化推荐结果"""
        
        command_str = " ".join(rec.command_args)
        
        result = f"""
🎯 为您推荐的参数配置：
{'═' * 50}

📋 推荐命令：
{command_str}

💡 参数说明：
{rec.explanation}

⏱️ 预计耗时：{rec.estimated_time}
🎗️ 质量等级：{rec.quality_level}

🔄 其他选择：
"""
        
        for alt in rec.alternatives:
            result += f"\n{alt['name']}:\n  {alt['command']}\n  💬 {alt['description']}\n"
            
        result += f"""
💾 使用方法：
1. 复制上面的推荐命令
2. 如果使用图片，请将图片放在 reference_images/ 目录下
3. 在终端中运行命令
4. 等待生成完成并自动预览

❓ 如需调整参数，您可以：
- 运行 'python scripts/generate_character.py --help' 查看所有参数
- 或者重新运行智能助手：'python scripts/intelligent_assistant.py'
        """
        
        return result

def main():
    """主函数"""
    assistant = IntelligentParameterAssistant()
    
    print(assistant.start_conversation())
    
    while True:
        try:
            user_input = input("\n💬 您的回答: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("\n👋 感谢使用Cortex3d智能助手！")
                break
                
            response, continue_chat = assistant.analyze_user_input(user_input)
            print(response)
            
            if not continue_chat:
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 感谢使用Cortex3d智能助手！")
            break
        except Exception as e:
            print(f"\n❌ 出现错误：{e}")
            print("请重新输入或输入 'quit' 退出。")

if __name__ == "__main__":
    main()