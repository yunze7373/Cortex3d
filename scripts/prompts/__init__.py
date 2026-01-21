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
        self._fallback_templates = self._init_fallback_templates()
    
    def _init_fallback_templates(self) -> Dict[str, dict]:
        """初始化硬编码的回退模板（YAML 加载失败时使用）"""
        return {
            "multiview/standard": {
                "name": "standard_multiview",
                "version": "2.0",
                "layout": "1x4_horizontal",
                "template": self._get_standard_template()
            },
            "multiview/image_ref": {
                "name": "image_reference",
                "version": "1.0",
                "template": self._get_image_ref_template()
            },
            "multiview/strict_copy": {
                "name": "strict_copy",
                "version": "1.0",
                "template": self._get_strict_copy_template()
            },
            "multiview/universal": {
                "name": "universal_multiview",
                "version": "1.0",
                "template": self._get_universal_template()
            },
            "multiview/six_view": {
                "name": "six_view_multiview",
                "version": "1.0",
                "template": self._get_six_view_template()
            },
            "multiview/eight_view": {
                "name": "eight_view_multiview",
                "version": "1.0",
                "template": self._get_eight_view_template()
            },
            "negative/anatomy": {
                "prompts": [
                    "extra limbs", "missing limbs", "extra fingers", "missing fingers",
                    "extra arms", "extra legs", "deformed hands", "deformed feet",
                    "twisted body", "unnatural pose", "broken anatomy", "fused limbs",
                    "floating limbs", "disconnected body parts"
                ]
            },
            "negative/quality": {
                "prompts": [
                    "low quality", "blurry", "pixelated", "jpeg artifacts",
                    "watermark", "text", "logo", "signature", "cropped",
                    "out of frame", "mutated", "disfigured", "bad proportions",
                    "duplicate panels", "mirror flip"
                ]
            },
            "negative/layout": {
                "prompts": [
                    "2x2 grid layout", "vertical layout", "stacked panels",
                    "overlapping views", "unequal panel sizes", "diagonal arrangement",
                    "circular layout", "text labels", "view labels",
                    "front back left right text"
                ]
            }
        }
    
    def _get_standard_template(self) -> str:
        """标准4视角模板"""
        return """Generate a professional 3D character turntable reference sheet with exactly 4 panels arranged horizontally.

## OUTPUT REQUIREMENT
Single image containing 4 panels in a row: [FRONT] [RIGHT] [BACK] [LEFT]

## CHARACTER
{character_description}
Style: {style}

## CRITICAL RULES - READ CAREFULLY

### TURNTABLE ROTATION (NOT MIRROR!)
Imagine the character standing on a rotating platform:
- Panel 1 (FRONT): Platform at 0° - We see the FACE, chest, front of body
- Panel 2 (RIGHT SIDE): Platform rotated 90° clockwise - We see the RIGHT ear, RIGHT shoulder, RIGHT hip
- Panel 3 (BACK): Platform rotated 180° - We see back of HEAD, spine, buttocks
- Panel 4 (LEFT SIDE): Platform rotated 270° clockwise - We see the LEFT ear, LEFT shoulder, LEFT hip

⚠️ IMPORTANT: Panels 2 and 4 are NOT mirrors! They show OPPOSITE sides of the body!
- RIGHT SIDE shows: right ear, right arm, right leg
- LEFT SIDE shows: left ear, left arm, left leg

### ANATOMICAL CORRECTNESS (CRITICAL!)
- Arms MUST connect to shoulders only
- Legs MUST connect to hips only
- Head MUST connect to neck only
- NO extra limbs, NO twisted body parts
- Upper body and lower body MUST face the SAME direction in each panel
- The entire body rotates together as one unit

### POSE CONSISTENCY (CRITICAL!)
- EXACT same pose in ALL 4 panels - only the viewing angle changes
- Same arm positions, same leg positions, same head tilt
- If holding an object in right hand → it stays in right hand in ALL views
- This is ONE character photographed from 4 angles, NOT 4 different poses

### PANEL LAYOUT
- 4 equal-width panels arranged horizontally (side by side)
- Character centered in each panel
- Same scale/size in all panels
- Clean separation between panels
- Neutral gray or white background

### LIGHTING
- Flat, even studio lighting (no harsh shadows)
- Face clearly visible without shadow obstruction
- Consistent lighting direction across all panels

### ABSOLUTELY FORBIDDEN
- NO text labels (no "front", "back", "left", "right")
- NO twisted bodies (upper body facing different direction than legs)
- NO mirror flips (left and right views must show different sides)
- NO anatomical errors (no extra limbs, no wrong joint positions)
- NO pose variations between panels

Generate a clean, professional character reference sheet following ALL rules above."""

    def _get_image_ref_template(self) -> str:
        """图片参考模式模板（支持任意视角数量）"""
        return """Generate a 3D character reference sheet with exactly {view_count} panel(s), showing the character from the reference image.

## OUTPUT REQUIREMENT
Single image with {view_count} panel(s): {panel_list}

## CHARACTER DESCRIPTION (from reference photo)
{character_description}

## CRITICAL: GENERATE EXACTLY THESE SPECIFIC VIEW(S)
You MUST generate exactly the following view(s) of the character:
{view_descriptions}

⚠️ SINGLE VIEW MODE: If only 1 panel is requested, output ONLY that one specific angle. Do NOT create multiple panels.
⚠️ REFERENCE PHOTO OVERRIDE: The reference photo may show the character from a different angle. You MUST IGNORE the camera angle in the reference photo and ROTATE the character to match the requested angle(s) above.
⚠️ FORCE ROTATION: Extract the character's appearance from the reference, then ROTATE them to the exact specified angle(s).

## CRITICAL: PRESERVE THE ORIGINAL POSE
⚠️ The character has a SPECIFIC pose from the reference photo. You MUST preserve this pose:
- If the character is WALKING → show walking pose from the requested angle(s)
- If the character is SITTING → show sitting pose from the requested angle(s)
- If one leg is forward → keep that leg forward
- If arms are in a specific position → maintain that position

DO NOT change the pose to a generic standing pose!

## ANATOMICAL RULES
- Arms connect to shoulders only
- Legs connect to hips only
- Upper and lower body face the SAME direction
- NO twisted bodies, NO extra limbs

## PANEL LAYOUT
- {view_count} panel(s) arranged as {layout_description}
- Character centered in each panel
- Same scale in all panels
- Neutral gray background
- NO text labels

## LIGHTING
- Flat, even studio lighting
- No harsh shadows
- Character clearly visible

## ABSOLUTELY FORBIDDEN
- NO text labels on the image
- NO additional views beyond what is specified above
- Do NOT generate 4 views if only 1 or 2 are requested
- NO pose changes from the reference (except for rotation)

Generate ONLY the specified view(s) of the character, maintaining the EXACT pose from the reference."""

    def _get_strict_copy_template(self) -> str:
        """严格复制模式模板"""
        return """Create a 4-panel CHARACTER TURNTABLE showing THIS PERSON from the reference image.

## TASK: TURNTABLE ROTATION (90° between each view)
Imagine THIS PERSON is standing on a rotating platform. The platform rotates exactly 90° between each panel.

## THE 4 DISTINCT VIEWS (MUST BE DIFFERENT)
Each panel shows THIS PERSON from a COMPLETELY DIFFERENT angle:

| Panel | Angle | What You See | Key Identifier |
|-------|-------|--------------|----------------|
| 1 | 0° (FRONT) | Face visible, looking at camera | BOTH EYES visible |
| 2 | 90° (RIGHT SIDE) | Profile view, facing right | RIGHT EAR visible, NO face |
| 3 | 180° (BACK) | Back of head, no face | BACK OF HEAD only |
| 4 | 270° (LEFT SIDE) | Profile view, facing left | LEFT EAR visible, NO face |

## STRICT REQUIREMENTS
1. ⚠️ EACH VIEW MUST BE UNIQUE - no duplicate angles
2. ⚠️ Panel 1 and 3 must be OPPOSITE (face vs back of head)
3. ⚠️ Panel 2 and 4 must be OPPOSITE (right ear vs left ear)
4. Keep THIS PERSON's face, hair, clothes, and accessories identical across all views
5. Only the CAMERA POSITION changes, character stays the same

## FORBIDDEN
❌ Two panels showing the face (front) 
❌ Two panels showing the back
❌ Two panels showing the same side profile
❌ Similar angles in adjacent panels
❌ Text labels on the image

## OUTPUT
Single horizontal image: [FRONT 0°] [RIGHT 90°] [BACK 180°] [LEFT 270°]
Gray background. Full body visible in all panels.

Generate 4 DISTINCT turntable views of THIS PERSON."""

    def _get_universal_template(self) -> str:
        """通用多视角模板（支持任意视角数量，包括单视角）"""
        return """Generate a professional 3D character reference sheet with exactly {view_count} panel(s) arranged as {layout_description}.

## OUTPUT REQUIREMENT
Single image containing {view_count} panel(s): {panel_list}

## CHARACTER
{character_description}
Style: {style}

## CRITICAL: GENERATE EXACTLY THESE VIEWS
You MUST generate exactly the following view(s), no more, no less:
{view_descriptions}

⚠️ IMPORTANT FOR SINGLE VIEW: If only 1 panel is requested, generate ONLY that one specific angle. Do NOT generate multiple views.
⚠️ REFERENCE PHOTO OVERRIDE: If a reference photo is provided, you MUST IGNORE the camera angle in the reference photo. Instead, ROTATE the character to match the requested angle(s) above.
⚠️ FORCE ROTATION: Do not just copy the reference photo's perspective. ROTATE the character to the exact angle(s) specified.

## ANATOMICAL CORRECTNESS (CRITICAL!)
- Arms MUST connect to shoulders only
- Legs MUST connect to hips only
- Head MUST connect to neck only
- NO extra limbs, NO twisted body parts
- Upper body and lower body MUST face the SAME direction in each panel
- The entire body rotates together as one unit

## POSE CONSISTENCY (if multiple panels)
- EXACT same pose in ALL panels - only the viewing angle changes
- Same arm positions, same leg positions, same head tilt
- This is ONE character photographed from the specified angle(s)

## PANEL LAYOUT
- {view_count} panel(s) arranged as {layout_description}
- Character centered in each panel
- Same scale/size in all panels
- Clean separation between panels (if multiple)
- Neutral gray or white background

## LIGHTING
- Flat, even studio lighting (no harsh shadows)
- Face clearly visible without shadow obstruction (if visible from the angle)
- Consistent lighting direction across all panels

## ABSOLUTELY FORBIDDEN
- NO text labels (no "front", "back", "left", "right", no angle numbers)
- NO twisted bodies (upper body facing different direction than legs)
- NO anatomical errors (no extra limbs, no wrong joint positions)
- NO additional views beyond what is requested
- Do NOT generate 4 views if only 1 is requested

Generate ONLY the specified view(s) following ALL rules above."""

    def _get_six_view_template(self) -> str:
        """6视角专用模板"""
        return """Generate a professional 3D character reference sheet with exactly 6 panels in a 2x3 grid layout.

## OUTPUT REQUIREMENT
Single image containing 6 panels arranged as 2 rows x 3 columns:
Row 1: [FRONT 0°] [FRONT-RIGHT 45°] [RIGHT 90°]
Row 2: [BACK 180°] [LEFT 270°] [FRONT-LEFT 315°]

## CHARACTER
{character_description}
Style: {style}

## TURNTABLE ROTATION
Imagine the character standing on a rotating platform:
- Panel 1 (FRONT): Platform at 0° - Face visible, looking at camera
- Panel 2 (FRONT-RIGHT): Platform at 45° - Right cheek visible, 3/4 view from front-right
- Panel 3 (RIGHT): Platform at 90° - Right ear visible, full profile view
- Panel 4 (BACK): Platform at 180° - Back of head visible, NO face
- Panel 5 (LEFT): Platform at 270° - Left ear visible, full profile view
- Panel 6 (FRONT-LEFT): Platform at 315° - Left cheek visible, 3/4 view from front-left

## CRITICAL RULES
- EXACT same pose in ALL 6 panels - only viewing angle changes
- NO text labels on the image
- NO anatomical errors (extra limbs, twisted body)
- Consistent lighting and character scale across all panels
- Arms MUST connect to shoulders, Legs MUST connect to hips
- Clean separation between panels with neutral background

Generate a professional 6-view character reference sheet."""

    def _get_eight_view_template(self) -> str:
        """8视角专用模板"""
        return """Generate a professional 3D character reference sheet with exactly 8 panels in a 2x4 grid layout.

## OUTPUT REQUIREMENT
Single image containing 8 panels arranged as 2 rows x 4 columns:
Row 1: [FRONT 0°] [FRONT-RIGHT 45°] [RIGHT 90°] [BACK 180°]
Row 2: [LEFT 270°] [FRONT-LEFT 315°] [TOP ↓] [BOTTOM ↑]

## CHARACTER
{character_description}
Style: {style}

## VIEW DESCRIPTIONS
- Panel 1 (FRONT): Platform at 0° - Face visible, looking at camera
- Panel 2 (FRONT-RIGHT): Platform at 45° - Right cheek visible, 3/4 view
- Panel 3 (RIGHT): Platform at 90° - Right ear visible, full profile view
- Panel 4 (BACK): Platform at 180° - Back of head visible, NO face
- Panel 5 (LEFT): Platform at 270° - Left ear visible, full profile view
- Panel 6 (FRONT-LEFT): Platform at 315° - Left cheek visible, 3/4 view
- Panel 7 (TOP): Bird's eye view - Looking straight down at top of head and shoulders
- Panel 8 (BOTTOM): Worm's eye view - Looking straight up at soles of feet

## CRITICAL RULES
- EXACT same pose in all horizontal views (Panels 1-6)
- TOP and BOTTOM views show the character from directly above/below
- NO text labels on the image
- NO anatomical errors
- Consistent lighting and scale
- Clean panel separation with neutral background

Generate a professional 8-view character reference sheet including top and bottom perspectives."""

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
        
        # 尝试从 YAML 文件加载
        yaml_path = PROMPTS_DIR / category / f"{name}.yaml"
        
        if YAML_AVAILABLE and yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    template = yaml.safe_load(f)
                self._cache[cache_key] = template
                return template
            except Exception as e:
                print(f"[WARNING] 加载 YAML 失败 ({yaml_path}): {e}, 使用回退模板")
        
        # 使用回退模板
        if cache_key in self._fallback_templates:
            template = self._fallback_templates[cache_key]
            self._cache[cache_key] = template
            return template
        
        # 未找到模板
        raise ValueError(f"未找到提示词模板: {cache_key}")

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
        
        # 格式化
        try:
            return template_str.format(
                character_description=character_description,
                style=style,
                view_count=view_count,
                layout_description=layout_desc,
                panel_list=format_panel_list(views),
                view_descriptions=format_view_descriptions(views)
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
            top_bottom_instructions=top_bottom_instructions
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
        # 加载模板中的风格预设
        template = self.load_prompt("multiview", "image_ref")
        style_presets = template.get("style_presets", {})
        
        if not style:
            return style_presets.get("default", "Match the reference image style.")
        
        style_lower = style.lower()
        
        # 检测是否为写实风格
        photorealistic_keywords = ["photorealistic", "photo", "realistic", "raw", "real", "8k", "hyperrealistic"]
        if any(kw in style_lower for kw in photorealistic_keywords):
            return style_presets.get("photorealistic", f"Generate in photorealistic style: {style}")
        
        # 检测是否为动画风格
        anime_keywords = ["anime", "manga", "cartoon", "2d", "cell shaded", "ghibli"]
        if any(kw in style_lower for kw in anime_keywords):
            return style_presets.get("anime", f"Generate in anime style: {style}")
        
        # 默认：使用用户指定的风格
        return f"""**STYLE REQUIREMENT:**
{style}
- Maintain this exact style consistently across all panels
- Match the visual characteristics of the reference image"""

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
            top_bottom_instructions=top_bottom_instructions
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
