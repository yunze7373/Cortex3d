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
        """图片参考模式模板"""
        return """Generate a 3D character turntable reference sheet with exactly 4 panels, showing the character described below from 4 angles.

## OUTPUT
Single image with 4 panels horizontally: [FRONT] [RIGHT] [BACK] [LEFT]

## CHARACTER DESCRIPTION (from reference photo)
{character_description}

## CRITICAL: PRESERVE THE ORIGINAL POSE
⚠️ The character has a SPECIFIC pose from the reference photo. You MUST preserve this pose:
- If the character is WALKING → show walking pose from all 4 angles
- If the character is SITTING → show sitting pose from all 4 angles  
- If one leg is forward → keep that leg forward in all views
- If arms are in a specific position → maintain that position

DO NOT change the pose to a generic standing pose!

## TURNTABLE ROTATION
The 4 panels show the SAME character in the SAME pose, just rotated:
- Panel 1 (FRONT): 0° - facing camera
- Panel 2 (RIGHT): 90° - right side visible
- Panel 3 (BACK): 180° - back visible
- Panel 4 (LEFT): 270° - left side visible

## ANATOMICAL RULES
- Arms connect to shoulders only
- Legs connect to hips only
- Upper and lower body face the SAME direction
- NO twisted bodies, NO extra limbs

## PANEL LAYOUT
- 4 equal panels side by side
- Same scale in all panels
- Neutral gray background
- NO text labels

## LIGHTING
- Flat, even studio lighting
- No harsh shadows
- Face clearly visible

Generate the character maintaining the EXACT pose described, viewed from 4 angles."""

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
        """通用多视角模板（支持任意视角数量）"""
        return """Generate a professional 3D character turntable reference sheet with exactly {view_count} panels arranged in {layout_description}.

## OUTPUT REQUIREMENT
Single image containing {view_count} panels: {panel_list}

## CHARACTER
{character_description}
Style: {style}

## CRITICAL RULES - READ CAREFULLY

### TURNTABLE ROTATION (NOT MIRROR!)
Imagine the character standing on a rotating platform:
{view_descriptions}

⚠️ IMPORTANT: Each panel shows a UNIQUE angle. No duplicates!
⚠️ REFERENCE PHOTO OVERRIDE: The reference photo has a specific camera angle. You MUST IGNORE the reference camera angle and generate the specific angles requested above.
⚠️ FORCE ROTATION: Do not just copy the reference photo. ROTATE the character to the requested angle.

### ANATOMICAL CORRECTNESS (CRITICAL!)
- Arms MUST connect to shoulders only
- Legs MUST connect to hips only
- Head MUST connect to neck only
- NO extra limbs, NO twisted body parts
- Upper body and lower body MUST face the SAME direction in each panel
- The entire body rotates together as one unit

### POSE CONSISTENCY (CRITICAL!)
- EXACT same pose in ALL {view_count} panels - only the viewing angle changes
- Same arm positions, same leg positions, same head tilt
- If holding an object → it stays in the same hand in ALL views
- This is ONE character photographed from {view_count} angles, NOT {view_count} different poses

### PANEL LAYOUT
- {view_count} panels arranged as {layout_description}
- Character centered in each panel
- Same scale/size in all panels
- Clean separation between panels
- Neutral gray or white background

### LIGHTING
- Flat, even studio lighting (no harsh shadows)
- Face clearly visible without shadow obstruction
- Consistent lighting direction across all panels

### ABSOLUTELY FORBIDDEN
- NO text labels (no "front", "back", "left", "right", no angle numbers)
- NO twisted bodies (upper body facing different direction than legs)
- NO mirror flips between side views
- NO anatomical errors (no extra limbs, no wrong joint positions)
- NO pose variations between panels

Generate a clean, professional character reference sheet following ALL rules above."""

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
        
        # 选择模板
        if view_mode == "4-view":
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
        if rows > 1:
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

    def build_image_reference_prompt(self, character_description: str) -> str:
        """
        构建图片参考模式提示词
        
        Args:
            character_description: 从参考图片提取的描述
        
        Returns:
            完整提示词
        """
        template = self.load_prompt("multiview", "image_ref")
        return template.get("template", "").format(
            character_description=character_description
        )

    def build_strict_copy_prompt(self) -> str:
        """
        构建严格复制模式提示词
        
        Returns:
            完整提示词
        """
        template = self.load_prompt("multiview", "strict_copy")
        return template.get("template", "")


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
