#!/usr/bin/env python3
"""
智能助手增强版概念设计 - 混合规则+小型LLM方案
"""

class HybridSmartAssistant:
    def __init__(self):
        # 保留原有的规则系统作为快速路径
        self.rule_assistant = AdvancedParameterAssistant()
        self.use_llm = False  # 可配置是否启用LLM
        
        # 小型LLM相关（可选）
        if self.use_llm:
            self.llm_client = self._init_small_llm()
    
    def process_input(self, user_input: str):
        """混合处理用户输入"""
        
        # 第1层：快速规则匹配
        confidence = self._calculate_rule_confidence(user_input)
        
        if confidence > 0.8:
            # 高置信度，使用规则系统（速度优先）
            return self.rule_assistant.process_natural_language_input(user_input)
        
        elif self.use_llm:
            # 低置信度且启用LLM，使用小模型处理
            return self._llm_process(user_input)
        
        else:
            # 回退到规则系统
            return self.rule_assistant.process_natural_language_input(user_input)
    
    def _llm_process(self, user_input: str):
        """使用小型LLM处理复杂场景"""
        
        prompt = f"""
你是Cortex3d的参数助手。用户说："{user_input}"

请分析用户意图并选择最合适的模式：
1. simple_wardrobe - 快速换装 (--wear)
2. image_composite - 复杂合成 (--mode-composite) 
3. anime_character - 动漫角色生成
4. realistic_portrait - 写实肖像
5. game_character - 游戏角色
6. concept_art - 概念艺术
7. 3d_model - 3D模型生成
8. image_repair - 图像修复

只返回模式名称，不要解释。
"""
        
        # 调用小模型推理
        mode = self.llm_client.generate(prompt).strip()
        
        # 基于LLM结果生成参数
        return self._generate_params_from_mode(mode, user_input)
    
    def _calculate_rule_confidence(self, user_input: str) -> float:
        """计算规则匹配的置信度"""
        
        # 简单的置信度计算逻辑
        keywords_hit = 0
        total_keywords = 0
        
        keyword_patterns = [
            r'(快速换装|简单换装|wear)',
            r'(动漫|anime|二次元)',
            r'(写实|realistic|photorealistic)',
            r'(3d|三维|模型)',
            # ... 更多模式
        ]
        
        for pattern in keyword_patterns:
            total_keywords += 1
            if re.search(pattern, user_input.lower()):
                keywords_hit += 1
        
        return keywords_hit / total_keywords if total_keywords > 0 else 0.0

# 使用示例
hybrid_assistant = HybridSmartAssistant()

# 这些会走快速规则路径
print(hybrid_assistant.process_input("快速换装"))  # 规则匹配
print(hybrid_assistant.process_input("动漫风格"))  # 规则匹配

# 这些可能会走LLM路径  
print(hybrid_assistant.process_input("我想让这个角色试试新衣服的效果"))  # LLM处理
print(hybrid_assistant.process_input("帮我把这张照片变得更有艺术感"))  # LLM处理