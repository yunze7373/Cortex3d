#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级智能参数助手
使用更智能的对话流程和参数推荐算法
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ConversationContext:
    """对话上下文"""
    user_messages: List[str] = field(default_factory=list)
    detected_intent: Dict[str, any] = field(default_factory=dict)
    current_stage: str = "initial"
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
class AdvancedParameterAssistant:
    def __init__(self):
        self.context = ConversationContext()
        self.parameter_templates = self._load_parameter_templates()
        
    def _load_parameter_templates(self) -> Dict[str, Dict]:
        """加载参数模板"""
        return {
            "anime_character": {
                "base": ["--anime", "-v", "6", "--res", "2K"],
                "quality_boost": ["--pro", "--res", "4K", "-v", "8"],
                "speed_boost": ["--res", "1K", "-v", "4"],
                "description": "动漫风格角色生成"
            },
            "realistic_portrait": {
                "base": ["--photorealistic", "--pro", "--res", "4K"],
                "quality_boost": ["--ratio", "3:2", "--auto-complete"],
                "speed_boost": ["--res", "2K", "--no-negative"],
                "description": "写实肖像生成"
            },
            "game_character": {
                "base": ["--pixel", "-v", "8", "--3d", "--fast-3d"],
                "quality_boost": ["--algo", "hunyuan3d-2.1"],
                "speed_boost": ["--res", "1K", "-v", "4"],
                "description": "游戏角色生成"
            },
            "concept_art": {
                "base": ["--watercolor", "--res", "4K", "--ratio", "16:9"],
                "quality_boost": ["--pro", "--iterative-360", "6"],
                "speed_boost": ["--res", "2K", "-v", "4"],
                "description": "概念艺术生成"
            },
            "3d_model": {
                "base": ["--3d", "--res", "4K", "-v", "8", "--auto-complete"],
                "quality_boost": ["--algo", "trellis2", "--3d-quality", "ultra"],
                "speed_boost": ["--fast-3d", "--res", "2K"],
                "description": "3D模型生成"
            },
            "image_repair": {
                "base": ["--preprocess", "--auto-complete", "--res", "2K"],
                "quality_boost": ["--pro", "--res", "4K", "--preprocess-model", "birefnet-general"],
                "speed_boost": ["--res", "1K", "--preprocess-model", "isnet-general-use"],
                "description": "图像修复和增强"
            },
            "detail_fix": {
                "base": ["--mode-refine", "--auto-complete"],
                "quality_boost": ["--pro", "--res", "4K", "--max-retries", "5"],
                "speed_boost": ["--res", "2K", "--max-retries", "2"],
                "description": "细节修复和完善"
            },
            "style_transfer": {
                "base": ["--mode-style", "--preserve-details"],
                "quality_boost": ["--pro", "--res", "4K", "--auto-complete"],
                "speed_boost": ["--res", "2K"],
                "description": "风格转换和艺术化"
            }
        }
    
    def start_intelligent_conversation(self) -> str:
        """开始智能对话"""
        return """
🧠 Cortex3d 高级智能助手
═════════════════════════════════════

🎯 我将通过智能对话帮您找到最佳参数配置！

请用自然语言描述您的需求，例如：
• "我想把这张照片转成动漫风格的多视角图片"
• "生成一个赛博朋克风格的3D角色模型"  
• "制作游戏用的像素风格角色，要快一点"
• "高质量的写实肖像，用于商业项目"

💡 您也可以：
- 上传图片并说明处理需求
- 提及时间要求（急用/不着急）
- 说明质量要求（预览/一般/高质量）
- 提及用途（学习/项目/商用）

🗣️ 请告诉我您的具体需求：
        """
    
    def process_natural_language_input(self, user_input: str) -> Tuple[str, bool, Optional[List[str]]]:
        """处理自然语言输入"""
        
        self.context.user_messages.append(user_input)
        user_input_lower = user_input.lower()
        
        # 智能意图识别
        self._analyze_user_intent(user_input_lower)
        
        # 根据置信度决定是否需要进一步澄清
        if self._should_ask_clarification():
            clarification_q = self._generate_clarification_question()
            return clarification_q, True, None
        
        # 生成最终参数推荐
        recommendation = self._generate_smart_recommendation()
        return recommendation, False, recommendation['command_args']
    
    def _analyze_user_intent(self, user_input: str):
        """分析用户意图"""
        
        intent = self.context.detected_intent
        scores = self.context.confidence_scores
        
        # 检测输入类型
        if any(word in user_input for word in ["图片", "照片", "图像", "photo", "image", "picture", "转换", "参考", "这张"]):
            intent['has_image'] = True
            scores['has_image'] = 0.9
        
        # 检测风格偏好
        style_patterns = {
            'anime': r'(动漫|anime|二次元|卡通|动画)',
            'photorealistic': r'(写实|真实|照片|摄影|realistic|photo)',
            'pixel': r'(像素|pixel|8bit|16bit|复古|游戏)',
            'cyberpunk': r'(赛博朋克|cyberpunk|科幻|未来|霓虹)',
            'watercolor': r'(水彩|水彩画|watercolor|艺术|绘画)',
            'clay': r'(粘土|clay|玩偶|手办)',
            'ghibli': r'(吉卜力|宫崎骏|ghibli|治愈)'
        }
        
        for style, pattern in style_patterns.items():
            if re.search(pattern, user_input):
                intent['style'] = style
                scores['style'] = 0.8
                break
        
        # 检测3D需求
        if re.search(r'(3d|三维|立体|模型|打印|model)', user_input):
            intent['needs_3d'] = True
            scores['needs_3d'] = 0.8
        
        # 检测质量要求
        quality_patterns = {
            'fast': r'(快|急|预览|草图|测试)',
            'high': r'(高质量|精细|商用|专业|最好|完美)',
            'balanced': r'(正常|一般|平衡|中等)'
        }
        
        for quality, pattern in quality_patterns.items():
            if re.search(pattern, user_input):
                intent['quality'] = quality
                scores['quality'] = 0.7
                break
        
        # 检测用途
        purpose_patterns = {
            'commercial': r'(商用|商业|项目|客户|公司|工作)',
            'learning': r'(学习|练习|试试|测试|实验)',
            'personal': r'(个人|自己|娱乐|玩玩|hobby)'
        }
        
        for purpose, pattern in purpose_patterns.items():
            if re.search(pattern, user_input):
                intent['purpose'] = purpose
                scores['purpose'] = 0.6
                break
        
        # 检测视角需求
        if re.search(r'(多视角|全方位|360|四面|八面)', user_input):
            intent['multi_view'] = True
            scores['multi_view'] = 0.7
        
        # 检测特殊要求
        if re.search(r'(换装|服装|衣服|dress|clothing)', user_input):
            intent['wardrobe'] = True
            scores['wardrobe'] = 0.8
            
        # 检测编辑和修复需求
        if re.search(r'(修复|修理|fix|repair|restore|enhance|improve)', user_input):
            intent['needs_repair'] = True
            scores['needs_repair'] = 0.8
            
        if re.search(r'(去背景|抠图|remove.*background|背景去除)', user_input):
            intent['needs_preprocess'] = True
            scores['needs_preprocess'] = 0.9
            
        if re.search(r'(模糊|不清楚|清晰|锐化|blur|sharp|clear)', user_input):
            intent['quality_issue'] = True
            scores['quality_issue'] = 0.7
            
        if re.search(r'(手指|手部|面部|眼睛|pose|姿势|比例)', user_input):
            intent['detail_fix'] = True
            scores['detail_fix'] = 0.8
            
        if re.search(r'(风格.*转换|改变.*风格|style.*transfer|艺术.*化)', user_input):
            intent['style_transfer'] = True
            scores['style_transfer'] = 0.8
    
    def _should_ask_clarification(self) -> bool:
        """判断是否需要澄清"""
        
        # 如果关键信息的置信度都很低，需要澄清
        important_scores = [
            self.context.confidence_scores.get('style', 0),
            self.context.confidence_scores.get('quality', 0),
            max(self.context.confidence_scores.get('has_image', 0), 0.3)  # 图像不是必需的
        ]
        
        avg_confidence = sum(important_scores) / len(important_scores)
        
        # 如果平均置信度低于0.5且这是第一轮对话，需要澄清
        return avg_confidence < 0.5 and len(self.context.user_messages) == 1
    
    def _generate_clarification_question(self) -> str:
        """生成澄清问题"""
        
        intent = self.context.detected_intent
        scores = self.context.confidence_scores
        
        questions = []
        
        # 风格澄清
        if scores.get('style', 0) < 0.5:
            if intent.get('has_image'):
                questions.append("🎨 您希望保持原图风格还是转换为特定风格？（如动漫、写实、像素艺术等）")
            else:
                questions.append("🎨 您偏好哪种风格？（动漫、写实、像素、赛博朋克、水彩画等）")
        
        # 质量澄清  
        if scores.get('quality', 0) < 0.5:
            questions.append("⚡ 您的质量和时间偏好？\n   • 快速预览（5分钟内，中等质量）\n   • 平衡模式（10分钟，良好质量）\n   • 高质量（20分钟+，最佳效果）")
        
        # 用途澄清
        if scores.get('purpose', 0) < 0.5:
            questions.append("📋 用途说明有助于优化参数：\n   • 个人学习/娱乐\n   • 项目/工作用途\n   • 商业/专业用途")
        
        # 构建回复
        if questions:
            clarification = f"""
🤔 为了给您最佳推荐，请补充以下信息：

{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions))}

💡 您可以简单回答，如 "动漫风格，高质量，项目用途" 
            """
            return clarification
        
        # 如果没有需要澄清的，直接生成推荐
        return self._generate_smart_recommendation()
    
    def _generate_smart_recommendation(self) -> Dict:
        """生成智能推荐"""
        
        intent = self.context.detected_intent
        
        # 选择最佳模板
        template_name = self._select_best_template()
        template = self.parameter_templates[template_name]
        
        # 构建基础参数
        base_args = ["python", "scripts/generate_character.py"]
        
        # 添加描述或图像输入
        if intent.get('has_image'):
            base_args.extend(["--input", "your_image.jpg"])
        else:
            # 使用用户的原始描述
            description = self.context.user_messages[0]
            base_args.append(f'"{description}"')
        
        # 应用模板
        base_args.extend(template['base'])
        
        # 根据质量要求调整
        quality = intent.get('quality', 'balanced')
        if quality == 'high' and 'quality_boost' in template:
            base_args.extend(template['quality_boost'])
        elif quality == 'fast' and 'speed_boost' in template:
            # 替换为快速版本
            base_args = [arg for arg in base_args if arg not in ['--pro', '--4K']]
            base_args.extend(template['speed_boost'])
        
        # 添加特殊功能
        if intent.get('needs_3d') and '--3d' not in base_args:
            base_args.append('--3d')
            if quality == 'high':
                base_args.extend(['--algo', 'trellis2', '--3d-quality', 'ultra'])
            elif quality == 'fast':
                base_args.append('--fast-3d')
                
        if intent.get('multi_view') and '-v' not in base_args:
            base_args.extend(['-v', '8'])
        
        if intent.get('wardrobe'):
            base_args.extend(['--wear', 'clothing_item.png'])
            
        # 修复和预处理功能
        if intent.get('needs_preprocess'):
            base_args.extend(['--preprocess', '--preprocess-model', 'birefnet-general'])
            
        if intent.get('needs_repair') or intent.get('quality_issue'):
            base_args.append('--auto-complete')
            if quality == 'high':
                base_args.extend(['--max-retries', '5'])
                
        if intent.get('detail_fix'):
            if intent.get('has_image'):
                base_args.extend(['--mode-refine', '--refine-details', 'custom', '--from-refine', 'source_image.jpg'])
            else:
                base_args.append('--auto-complete')
                
        if intent.get('style_transfer'):
            base_args.extend(['--mode-style', '--preserve-details'])
            if intent.get('style'):
                style_preset_map = {
                    'anime': 'anime',
                    'photorealistic': 'cinematic', 
                    'watercolor': 'watercolor',
                    'oil': 'oil-painting'
                }
                preset = style_preset_map.get(intent['style'], 'anime')
                base_args.extend(['--style-preset', preset])
        
        # 兼容旧的编辑功能
        if intent.get('editing') and not any(intent.get(k) for k in ['needs_repair', 'detail_fix', 'style_transfer']):
            base_args.extend(['--mode-edit', '--edit-elements', 'add:your_modification'])
        
        # 总是添加预览
        if '--preview' not in base_args:
            base_args.append('--preview')
        
        # 生成解释
        explanation = self._generate_detailed_explanation(template_name, intent, quality)
        
        # 估算时间
        estimated_time = self._estimate_generation_time(base_args, intent)
        
        # 生成替代方案
        alternatives = self._generate_intelligent_alternatives(base_args, template_name)
        
        return {
            'command_args': base_args,
            'template_name': template_name,
            'explanation': explanation,
            'estimated_time': estimated_time,
            'alternatives': alternatives,
            'confidence': self._calculate_overall_confidence()
        }
    
    def _select_best_template(self) -> str:
        """选择最佳参数模板"""
        
        intent = self.context.detected_intent
        
        # 基于检测到的意图选择模板
        if intent.get('needs_repair') or intent.get('quality_issue'):
            if intent.get('detail_fix'):
                return 'detail_fix'
            else:
                return 'image_repair'
        elif intent.get('style_transfer'):
            return 'style_transfer'
        elif intent.get('style') == 'anime':
            return 'anime_character'
        elif intent.get('style') == 'photorealistic':
            return 'realistic_portrait'
        elif intent.get('style') == 'pixel' or 'game' in ' '.join(self.context.user_messages).lower():
            return 'game_character'
        elif intent.get('style') in ['watercolor', 'ghibli'] or 'art' in ' '.join(self.context.user_messages).lower():
            return 'concept_art'
        elif intent.get('needs_3d'):
            return '3d_model'
        else:
            # 默认返回动漫角色模板
            return 'anime_character'
    
    def _generate_detailed_explanation(self, template_name: str, intent: Dict, quality: str) -> str:
        """生成详细解释"""
        
        template = self.parameter_templates[template_name]
        explanations = [f"🎯 选择 {template['description']} 模板"]
        
        # 解释主要参数
        if intent.get('has_image'):
            explanations.append("📥 使用图像输入模式，分析参考图片特征")
        
        if intent.get('style'):
            style_names = {
                'anime': '日式动漫', 'photorealistic': '写实摄影', 
                'pixel': '像素艺术', 'cyberpunk': '赛博朋克',
                'watercolor': '水彩画', 'ghibli': '吉卜力'
            }
            explanations.append(f"🎨 应用 {style_names.get(intent['style'], intent['style'])} 风格")
        
        # 质量说明
        if quality == 'fast':
            explanations.append("⚡ 快速模式：优化速度，适合预览和测试")
        elif quality == 'high':
            explanations.append("💎 高质量模式：最佳效果，适合重要项目")
        else:
            explanations.append("⚖️ 平衡模式：质量与速度的最佳平衡")
        
        # 特殊功能说明
        if intent.get('needs_3d'):
            explanations.append("🚀 启用3D转换，生成三维模型")
        
        if intent.get('multi_view'):
            explanations.append("👁️ 多视角生成，提供全方位角色展示")
            
        if intent.get('wardrobe'):
            explanations.append("👗 换装功能，智能服装替换")
            
        # 修复和增强功能说明
        if intent.get('needs_preprocess'):
            explanations.append("🖼️ 图像预处理，自动去除背景提高质量")
            
        if intent.get('needs_repair'):
            explanations.append("🔧 智能修复，自动检测并修复图像问题")
            
        if intent.get('quality_issue'):
            explanations.append("✨ 质量增强，改善模糊和清晰度问题")
            
        if intent.get('detail_fix'):
            explanations.append("🎯 细节修复，针对面部、手部等局部问题")
            
        if intent.get('style_transfer'):
            explanations.append("🎨 风格转换，保持原始细节的艺术化处理")
        
        return '\n  '.join(explanations)
    
    def _estimate_generation_time(self, args: List[str], intent: Dict) -> str:
        """估算生成时间"""
        
        base_time = 3  # 基础时间（分钟）
        
        # 分辨率影响
        if '--res' in args:
            res_idx = args.index('--res') + 1
            if res_idx < len(args):
                if args[res_idx] == '4K':
                    base_time *= 2
                elif args[res_idx] == '1K':
                    base_time *= 0.5
        
        # Pro模型影响
        if '--pro' in args:
            base_time *= 1.5
        
        # 视角数量影响
        if '-v' in args:
            views_idx = args.index('-v') + 1
            if views_idx < len(args):
                views = int(args[views_idx])
                base_time *= (views / 4)  # 以4视角为基准
        
        # 3D转换影响
        if '--3d' in args:
            base_time += 5
            if '--fast-3d' in args:
                base_time -= 2
            elif 'trellis' in ' '.join(args):
                base_time += 5
        
        # 智能补全影响
        if any(arg in args for arg in ['--smart-fix', '--auto-complete']):
            base_time += 3
        
        if base_time < 2:
            return "1-3分钟"
        elif base_time < 10:
            return f"{int(base_time)-1}-{int(base_time)+2}分钟"
        elif base_time < 20:
            return f"{int(base_time)-2}-{int(base_time)+5}分钟"
        else:
            return "20分钟以上"
    
    def _generate_intelligent_alternatives(self, base_args: List[str], template_name: str) -> List[Dict]:
        """生成智能替代方案"""
        
        alternatives = []
        
        # 速度优化版本
        speed_args = base_args.copy()
        if '--res' in speed_args:
            res_idx = speed_args.index('--res') + 1
            if res_idx < len(speed_args):
                speed_args[res_idx] = '1K'
        if '--pro' in speed_args:
            speed_args.remove('--pro')
        if '-v' in speed_args:
            views_idx = speed_args.index('-v') + 1
            if views_idx < len(speed_args):
                speed_args[views_idx] = '4'
        
        alternatives.append({
            'name': '⚡ 速度优化版',
            'command': ' '.join(speed_args),
            'description': '2-5分钟快速生成，适合测试想法'
        })
        
        # 质量增强版本
        quality_args = base_args.copy()
        if '--pro' not in quality_args:
            quality_args.insert(-1, '--pro')
        if '--res' in quality_args:
            res_idx = quality_args.index('--res') + 1
            if res_idx < len(quality_args):
                quality_args[res_idx] = '4K'
        if '--auto-complete' not in quality_args:
            quality_args.insert(-1, '--auto-complete')
        
        alternatives.append({
            'name': '💎 极致质量版',
            'command': ' '.join(quality_args),
            'description': '15-25分钟，专业级最高质量输出'
        })
        
        # 3D增强版本（如果原始命令没有3D）
        if '--3d' not in base_args:
            d3_args = base_args.copy()
            d3_args.extend(['--3d', '--algo', 'hunyuan3d-2.1'])
            alternatives.append({
                'name': '🚀 3D增强版',
                'command': ' '.join(d3_args),
                'description': '添加3D模型生成，适合游戏和3D打印'
            })
        
        return alternatives
    
    def _calculate_overall_confidence(self) -> float:
        """计算总体置信度"""
        
        scores = list(self.context.confidence_scores.values())
        if not scores:
            return 0.5
        
        return sum(scores) / len(scores)
    
    def format_smart_recommendation(self, recommendation: Dict) -> str:
        """格式化智能推荐结果"""
        
        command = ' '.join(recommendation['command_args'])
        confidence = recommendation['confidence']
        
        # 置信度指示器
        confidence_indicator = "🟢 高" if confidence > 0.7 else "🟡 中" if confidence > 0.4 else "🔴 低"
        
        result = f"""
🎯 智能推荐结果
{'═' * 60}

💡 推荐置信度: {confidence_indicator} ({confidence:.1%})

📋 推荐命令:
{command}

🔍 参数解释:
  {recommendation['explanation']}

⏱️ 预计用时: {recommendation['estimated_time']}

🔄 其他选择:
"""
        
        for alt in recommendation['alternatives']:
            result += f"\n{alt['name']}:\n  💬 {alt['description']}\n  📋 {alt['command']}\n"
        
        result += f"""
📝 使用说明:
1. 如果使用图片，请先将图片放到 reference_images/ 目录
2. 复制推荐命令到终端执行
3. 首次运行建议使用 "⚡ 速度优化版" 测试效果

❓ 不满意？
- 输入 'modify' 可调整参数
- 输入 'restart' 可重新开始对话
- 直接运行 'python scripts/generate_character.py --help' 查看所有选项
        """
        
        return result

# 主程序入口
if __name__ == "__main__":
    assistant = AdvancedParameterAssistant()
    
    print(assistant.start_intelligent_conversation())
    
    while True:
        try:
            user_input = input("\n🗣️ 请描述您的需求: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                print("\n👋 感谢使用Cortex3d智能助手！")
                break
            
            if user_input.lower() == 'restart':
                assistant = AdvancedParameterAssistant()
                print(assistant.start_intelligent_conversation())
                continue
            
            response, continue_chat, command_args = assistant.process_natural_language_input(user_input)
            
            if continue_chat:
                print(response)
            else:
                # 显示最终推荐
                recommendation = response if isinstance(response, dict) else assistant._generate_smart_recommendation()
                print(assistant.format_smart_recommendation(recommendation))
                
                # 询问是否执行
                while True:
                    choice = input("\n🤔 是否立即执行推荐命令? (y/n/modify): ").lower()
                    if choice in ['y', 'yes', '是', '执行']:
                        print("\n✅ 请复制上面的命令到新终端执行，或按Ctrl+C退出助手后执行。")
                        break
                    elif choice in ['n', 'no', '否', '不']:
                        print("\n📋 命令已生成，您可以稍后手动执行。")
                        break
                    elif choice in ['modify', 'adjust', '修改', '调整']:
                        print("\n🔧 请描述您希望如何调整参数：")
                        break
                    else:
                        print("请输入 y/n/modify")
                        
                break
                
        except KeyboardInterrupt:
            print("\n\n👋 感谢使用智能助手！")
            break
        except Exception as e:
            print(f"\n❌ 出现错误: {e}")
            print("请重新描述需求或输入 'quit' 退出。")