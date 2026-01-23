"""
Cortex3d 提示词库管理器
支持 YAML 格式的提示词模板加载和版本管理
"""

import os
from pathlib import Path
from typing import Dict, Optional, List, Union

# 尝试导入 yaml，如果不可用则使用简单的解析器
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .views import (
    ViewConfig,
    get_views_for_mode,
    get_views_by_names,
    get_layout_for_views,
    format_panel_list,
    format_view_descriptions,
    VIEW_PRESETS
)


PROMPTS_DIR = Path(__file__).parent


class PromptLibrary:
    """提示词库管理器"""
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}
    
    def load_prompt(self, category: str, name: str) -> dict:
        """
        加载指定提示词模板
        
        Args:
            category: 类别 (multiview, negative, presets)
            name: 模板名称
        
        Returns:
            模板字典
        """
        cache_key = f"{category}/{name}"
        
        # 检查缓存
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 从 YAML 文件加载
        yaml_path = PROMPTS_DIR / category / f"{name}.yaml"
        
        if not yaml_path.exists():
            raise ValueError(f"未找到提示词模板: {yaml_path}")
        
        if not YAML_AVAILABLE:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                template = yaml.safe_load(f)
            self._cache[cache_key] = template
            return template
        except Exception as e:
            raise ValueError(f"加载模板失败 ({yaml_path}): {e}")

    def get_multiview_prompt(self, mode: str = "standard") -> str:
        """
        获取多视角生成提示词模板
        
        Args:
            mode: 模式 (standard, image_ref, strict_copy, universal, six_view, eight_view)
        
        Returns:
            提示词模板字符串
        """
        template = self.load_prompt("multiview", mode)
        return template.get("template", "")

    def get_negative_prompt(self, categories: List[str] = None) -> str:
        """
        获取负面提示词（合并多个类别）
        
        Args:
            categories: 类别列表 (anatomy, quality, layout)
        
        Returns:
            合并后的负面提示词字符串
        """
        if categories is None:
            categories = ["anatomy", "quality", "layout"]
        
        all_prompts = []
        for cat in categories:
            try:
                template = self.load_prompt("negative", cat)
                prompts = template.get("prompts", [])
                all_prompts.extend(prompts)
            except ValueError:
                pass  # 跳过不存在的类别
        
        return ", ".join(all_prompts)

    def build_multiview_prompt(
        self,
        character_description: str,
        style: str = "cinematic character",
        view_mode: str = "4-view",
        custom_views: List[str] = None
    ) -> str:
        """
        构建多视角生成提示词
        
        Args:
            character_description: 角色描述
            style: 风格描述
            view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
            custom_views: 自定义视角列表 (仅 custom 模式)
        
        Returns:
            完整提示词
        """
        # 确定要生成的视角
        if view_mode == "custom" and custom_views:
            views = get_views_by_names(custom_views)
        else:
            views = get_views_for_mode(view_mode)
        
        view_count = len(views)
        
        # 智能选择模板
        # - 自定义视角或非标准数量 -> universal 模板
        # - 4视角标准 -> standard 模板
        # - 6视角标准 -> six_view 模板
        # - 8视角标准 -> eight_view 模板
        if view_mode == "custom" or view_count not in [4, 6, 8]:
            template_name = "universal"
        elif view_mode == "4-view":
            template_name = "standard"
        elif view_mode == "6-view":
            template_name = "six_view"
        elif view_mode == "8-view":
            template_name = "eight_view"
        else:
            template_name = "universal"
        
        template = self.load_prompt("multiview", template_name)
        template_str = template.get("template", "")
        
        # 构建布局描述
        rows, cols, aspect = get_layout_for_views(view_count)
        if view_count == 1:
            layout_desc = "a single panel"
        elif rows > 1:
            layout_desc = f"{rows} rows x {cols} columns"
        else:
            layout_desc = f"{cols} panels in a horizontal row"
        
        # 构建输出类型描述
        output_type_description = f"Generate a STRICT multi-view reference sheet with EXACTLY {view_count} panels."
        
        # 检测风格类型
        style_lower = style.lower() if style else ""
        photorealistic_keywords = ["photorealistic", "photo", "realistic", "raw", "real", "8k"]
        if any(kw in style_lower for kw in photorealistic_keywords):
            output_type_description = f"Generate a STRICT multi-view photo composite with EXACTLY {view_count} panels."
        
        # 构建 TOP/BOTTOM 说明（仅当包含这些视角时）
        view_names = [v.name for v in views]
        top_bottom_instructions = ""
        if any(v in ["top", "bottom"] for v in view_names):
            top_bottom_instructions = """## ⚠️ TOP & BOTTOM VIEW NOTES
- TOP view: Camera directly above, looking DOWN at top of head/shoulders
- BOTTOM view: Camera directly below, looking UP at soles of feet
- These views show the subject from extreme vertical angles
"""
        
        # 格式化
        try:
            return template_str.format(
                character_description=character_description,
                style=style,
                view_count=view_count,
                layout_description=layout_desc,
                panel_list=format_panel_list(views),
                view_descriptions=format_view_descriptions(views),
                top_bottom_instructions=top_bottom_instructions,
                output_type_description=output_type_description,
                spatial_lock_instructions=self._get_spatial_lock_instructions(view_count),
                final_rules_instructions=self._get_final_rules_instructions(view_count)
            )
        except KeyError:
            # 某些模板可能不需要所有变量
            return template_str.format(
                character_description=character_description,
                style=style
            )

    def build_image_reference_prompt(
        self, 
        character_description: str,
        view_mode: str = "4-view",
        custom_views: List[str] = None,
        style: str = None
    ) -> str:
        """
        构建图片参考模式提示词
        
        Args:
            character_description: 从参考图片提取的描述
            view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
            custom_views: 自定义视角列表 (仅 custom 模式)
            style: 风格描述 (photorealistic, anime, 或自定义)
        
        Returns:
            完整提示词
        """
        from prompts.views import infer_reference_system, format_reference_system_context
        
        # 确定要生成的视角
        if view_mode == "custom" and custom_views:
            views = get_views_by_names(custom_views)
            # 推断参考视角系统（为 AI 提供上下文）
            ref_system_name, ref_system_views = infer_reference_system(custom_views)
        else:
            views = get_views_for_mode(view_mode)
            ref_system_name = view_mode
            ref_system_views = views
        
        view_count = len(views)
        view_names = [v.name for v in views]
        
        # 构建布局描述
        rows, cols, aspect = get_layout_for_views(view_count)
        if view_count == 1:
            layout_desc = "a single panel"
        elif rows > 1:
            layout_desc = f"{rows} rows x {cols} columns"
        else:
            layout_desc = f"{cols} panels in a horizontal row"
        
        # 构建参考系统上下文（帮助 AI 理解视角在整体系统中的位置）
        reference_context = ""
        if view_mode == "custom" and custom_views:
            reference_context = format_reference_system_context(ref_system_name, ref_system_views, views)
        
        # 构建风格指令和输出类型描述
        style_instructions = self._get_style_instructions(style)
        output_type_description = self._get_output_type_description(style, view_count)
        
        # 构建 TOP/BOTTOM 说明（仅当包含这些视角时）
        top_bottom_instructions = self._get_top_bottom_instructions(view_names)
        
        # 构建空间锁定指令（单视角时简化）
        spatial_lock_instructions = self._get_spatial_lock_instructions(view_count)
        
        # 构建最终规则指令（单视角时简化）
        final_rules_instructions = self._get_final_rules_instructions(view_count)
        
        template = self.load_prompt("multiview", "image_ref")
        return template.get("template", "").format(
            character_description=character_description,
            view_count=view_count,
            layout_description=layout_desc,
            panel_list=format_panel_list(views),
            view_descriptions=format_view_descriptions(views),
            reference_context=reference_context,
            style_instructions=style_instructions,
            output_type_description=output_type_description,
            top_bottom_instructions=top_bottom_instructions,
            spatial_lock_instructions=spatial_lock_instructions,
            final_rules_instructions=final_rules_instructions
        )
    
    def _get_output_type_description(self, style: str = None, view_count: int = 4) -> str:
        """
        根据风格生成输出类型描述，避免"3D reference sheet + photorealistic"冲突
        """
        template = self.load_prompt("multiview", "image_ref")
        dynamic_content = template.get("dynamic_content", {})
        
        if style:
            style_lower = style.lower()
            photorealistic_keywords = ["photorealistic", "photo", "realistic", "raw", "real", "8k"]
            if any(kw in style_lower for kw in photorealistic_keywords):
                return dynamic_content.get(
                    "output_type_photorealistic", 
                    f"Generate a multi-view photo composite with exactly {view_count} panel(s)."
                ).format(view_count=view_count)
        
        return dynamic_content.get(
            "output_type_default",
            f"Generate a multi-view reference sheet with exactly {view_count} panel(s)."
        ).format(view_count=view_count)
    
    def _get_top_bottom_instructions(self, view_names: List[str]) -> str:
        """
        仅当视角包含 top 或 bottom 时返回说明
        """
        has_top_bottom = any(v in ["top", "bottom"] for v in view_names)
        if not has_top_bottom:
            return ""  # 4-view 等不含 top/bottom 时不添加
        
        template = self.load_prompt("multiview", "image_ref")
        dynamic_content = template.get("dynamic_content", {})
        return dynamic_content.get("top_bottom_hint", "")
    
    def _get_style_instructions(self, style: str = None) -> str:
        """
        根据风格参数生成风格指令
        
        Args:
            style: 风格字符串 (可能包含 photorealistic, anime 等关键词)
        
        Returns:
            风格指令字符串
        """
        # 从风格预设系统获取
        from prompts.styles import find_matching_style
        
        if style:
            matched_preset = find_matching_style(style)
            if matched_preset:
                return matched_preset.style_instruction
        
        # 未匹配预设时，加载模板中的默认风格
        template = self.load_prompt("multiview", "image_ref")
        style_presets = template.get("style_presets", {})
        
        if not style:
            return style_presets.get("default", "Match the reference image style.")
        
        # 自定义风格：使用通用模板
        return f"""**STYLE REQUIREMENT:**
{style}
- Maintain this exact style consistently across all panels
- Match the visual characteristics of the reference image"""

    def _get_spatial_lock_instructions(self, view_count: int) -> str:
        """
        根据视角数量返回空间锁定指令
        单视角时移除多面板相关描述
        """
        if view_count == 1:
            return """**🔒 SPATIAL LOCK:**
- Fixed body proportions and anatomy
- Fixed outfit, accessories, and equipment
- Fixed hair length, style, and color
- Fixed facial features and expression
- Fixed pose and gesture
- Consistent lighting direction
- Same character, same moment, one perfect angle"""
        else:
            return f"""**🔒 ABSOLUTE SPATIAL LOCK (apply across ALL {view_count} panels):**
- Fixed body proportions and anatomy — identical in every panel
- Fixed outfit, accessories, equipment — no variation allowed
- Fixed hair length, style, and color — exact match required
- Fixed facial features and expression — same in every panel
- Fixed pose and gesture — synchronized across views
- Fixed object scale — character appears same size in all panels
- Consistent lighting direction — unified across the sheet
- Same character, same moment, multiple angles captured simultaneously"""

    def _get_final_rules_instructions(self, view_count: int) -> str:
        """
        根据视角数量返回最终规则指令
        单视角时简化规则
        """
        if view_count == 1:
            return """**📋 FINAL RULES:**
1. Single clean panel with consistent proportions
2. Maintain exact character appearance from reference
3. High quality, no distortion or artifacts
4. Character centered and well-framed

❗ Failure to follow these rules is unacceptable."""
        else:
            return f"""**📋 FINAL HARD RULES:**
1. Identical scale and framing across all {view_count} panels
2. Zero variation in outfit, hair, or accessories
3. Unified lighting across the entire sheet
4. High quality with no panel-to-panel inconsistencies
5. Character consistency is non-negotiable

❗ Failure to follow these rules is unacceptable."""

    def build_strict_copy_prompt(
        self,
        view_mode: str = "4-view",
        custom_views: List[str] = None,
        style: str = None
    ) -> str:
        """
        构建严格复制模式提示词
        
        Args:
            view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
            custom_views: 自定义视角列表 (仅 custom 模式)
            style: 风格描述 (photorealistic, anime, 或自定义)
        
        Returns:
            完整提示词
        """
        from prompts.views import infer_reference_system, format_reference_system_context
        
        # 确定要生成的视角
        if view_mode == "custom" and custom_views:
            views = get_views_by_names(custom_views)
            # 推断参考视角系统（为 AI 提供上下文）
            ref_system_name, ref_system_views = infer_reference_system(custom_views)
        else:
            views = get_views_for_mode(view_mode)
            ref_system_name = view_mode
            ref_system_views = views
        
        view_count = len(views)
        view_names = [v.name for v in views]
        
        # 构建布局描述
        rows, cols, aspect = get_layout_for_views(view_count)
        if view_count == 1:
            layout_desc = "a single panel"
        elif rows > 1:
            layout_desc = f"{rows} rows x {cols} columns"
        else:
            layout_desc = f"{cols} panels in a horizontal row"
        
        # 构建参考系统上下文（帮助 AI 理解视角在整体系统中的位置）
        reference_context = ""
        if view_mode == "custom" and custom_views:
            reference_context = format_reference_system_context(ref_system_name, ref_system_views, views)
        
        # 构建风格指令和输出类型描述
        style_instructions = self._get_style_instructions(style)
        output_type_description = self._get_output_type_description(style, view_count)
        
        # 构建 TOP/BOTTOM 说明（仅当包含这些视角时）
        top_bottom_instructions = self._get_top_bottom_instructions(view_names)
        
        template = self.load_prompt("multiview", "strict_copy")
        return template.get("template", "").format(
            view_count=view_count,
            layout_description=layout_desc,
            panel_list=format_panel_list(views),
            view_descriptions=format_view_descriptions(views),
            reference_context=reference_context,
            style_instructions=style_instructions,
            output_type_description=output_type_description,
            top_bottom_instructions=top_bottom_instructions,
            spatial_lock_instructions=self._get_spatial_lock_instructions(view_count),
            final_rules_instructions=self._get_final_rules_instructions(view_count)
        )


# 全局单例
prompt_library = PromptLibrary()


# 便捷函数
def get_multiview_prompt(mode: str = "standard") -> str:
    """获取多视角提示词模板"""
    return prompt_library.get_multiview_prompt(mode)


def get_negative_prompt(categories: List[str] = None) -> str:
    """获取负面提示词"""
    return prompt_library.get_negative_prompt(categories)


def build_multiview_prompt(
    character_description: str,
    style: str = "cinematic character",
    view_mode: str = "4-view",
    custom_views: List[str] = None
) -> str:
    """构建多视角提示词"""
    return prompt_library.build_multiview_prompt(
        character_description=character_description,
        style=style,
        view_mode=view_mode,
        custom_views=custom_views
    )
