#!/usr/bin/env python3
"""
Cortex3d 多视角验证与补全模块 v1.0

功能：
1. 使用 AI 分析生成的多视角图片，检测每个面板的实际视角
2. 比对期望视角与实际检测结果
3. 自动补生成缺失的视角
4. 合并成完整的多视角图

使用方法：
    from view_validator import ViewValidator
    
    validator = ViewValidator(api_key="your-key")
    result = validator.validate_and_complete(
        image_path="output.png",
        expected_views=["front", "right", "back", "left"],
        reference_image="ref.png",
        style="anime"
    )
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# 尝试导入图像处理库
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class ViewDirection(Enum):
    """视角方向枚举"""
    FRONT = "front"
    FRONT_RIGHT = "front_right"
    RIGHT = "right"
    BACK_RIGHT = "back_right"
    BACK = "back"
    BACK_LEFT = "back_left"
    LEFT = "left"
    FRONT_LEFT = "front_left"
    TOP = "top"
    BOTTOM = "bottom"
    UNKNOWN = "unknown"


@dataclass
class PanelAnalysis:
    """面板分析结果"""
    panel_index: int
    detected_view: str
    confidence: float
    description: str
    issues: List[str]


@dataclass
class ValidationResult:
    """验证结果"""
    is_complete: bool
    expected_views: List[str]
    detected_views: List[str]
    missing_views: List[str]
    duplicate_views: List[str]
    panel_analyses: List[PanelAnalysis]
    suggestions: List[str]


class ViewValidator:
    """
    多视角验证器
    
    使用 AI 检测生成图片中的实际视角，并自动补全缺失视角
    """
    
    # =========================================================================
    # 工业级视角检测提示词 v3.0
    # =========================================================================
    DETECTION_PROMPT = """You are an expert 3D modeling QA analyst. Your job is to verify that a multi-view reference sheet contains the correct camera angles for 3D reconstruction.

## CONTEXT & PURPOSE
This image is a **multi-view reference sheet** used for 3D modeling. It contains multiple panels showing the SAME OBJECT (could be a character, creature, vehicle, furniture, or any item) from DIFFERENT CAMERA ANGLES.

**Your Goal**: Identify WHICH CAMERA ANGLE each panel represents, so we can verify if any angles are missing or duplicated.

## STEP 1: GLOBAL ANALYSIS (Do This First!)

Before analyzing individual panels, observe the ENTIRE image:

1. **What is the subject?** (person/animal/robot/vehicle/object/furniture/etc.)
2. **How many panels are there?** Count carefully.
3. **What is the layout?**
   - 4 panels: Usually **1x4** (horizontal row)
   - 6 panels: Usually **2x3** (2 rows × 3 columns)
   - 8 panels: Usually **2x4** (2 rows × 4 columns)
4. **What is the expected view set?**
   - 4-view: FRONT, RIGHT, BACK, LEFT
   - 6-view: FRONT, FRONT_RIGHT, RIGHT, BACK, BACK_LEFT, LEFT
   - 8-view: 6-view + TOP, BOTTOM

## STEP 2: UNDERSTAND CAMERA ANGLES

Imagine the subject is standing at the center of a clock:
- **FRONT (0°/12 o'clock)**: Camera faces the subject's FRONT (face/main side)
- **FRONT_RIGHT (45°)**: Camera between front and right
- **RIGHT (90°/3 o'clock)**: Camera sees the RIGHT SIDE
- **BACK_RIGHT (135°)**: Camera between right and back
- **BACK (180°/6 o'clock)**: Camera faces the BACK
- **BACK_LEFT (225°)**: Camera between back and left
- **LEFT (270°/9 o'clock)**: Camera sees the LEFT SIDE
- **FRONT_LEFT (315°)**: Camera between left and front
- **TOP**: Camera directly ABOVE, looking DOWN
- **BOTTOM**: Camera directly BELOW, looking UP

### FOR CHARACTERS/CREATURES (with face):
| View | You See | Face/Head Direction |
|------|---------|---------------------|
| FRONT | Face, chest | Looking at camera |
| RIGHT | Right ear, right shoulder | Face points LEFT in image |
| BACK | Back of head, spine | Face not visible |
| LEFT | Left ear, left shoulder | Face points RIGHT in image |

### FOR OBJECTS/VEHICLES (no face):
Identify the "front" by:
- Vehicles: Where headlights/cockpit are
- Furniture: The side meant to face users
- Items: The side with logo/main features

## STEP 3: ANALYZE EACH PANEL

For each panel, determine:
1. Which side of the subject am I seeing?
2. Is this a primary angle (0°/90°/180°/270°) or diagonal (45°/135°/225°/315°)?
3. Is this a vertical angle (TOP/BOTTOM)?

## STEP 4: CROSS-CHECK FOR ERRORS

After classifying all panels:
1. **Check for duplicates**: Do any two panels show the same angle?
2. **Check for missing angles**: Based on the panel count, are all expected angles present?
3. **Check confidence**: Are any classifications uncertain?

## OUTPUT FORMAT

```json
{
    "global_analysis": {
        "subject_type": "character/creature/vehicle/object/furniture/other",
        "subject_description": "brief description",
        "panel_count": <number>,
        "layout": "1x4/2x3/2x4/other",
        "expected_view_set": "4-view/6-view/8-view"
    },
    "panels": [
        {
            "panel_index": 1,
            "position": "top-left/top-center/top-right/bottom-left/etc OR col1/col2/etc",
            "detected_view": "front/front_right/right/back_right/back/back_left/left/front_left/top/bottom/unknown",
            "confidence": 0.0-1.0,
            "key_features": "what visible features led to this classification",
            "reasoning": "one sentence explanation"
        }
    ],
    "verification": {
        "detected_views": ["front", "right", "back", "left"],
        "missing_views": [],
        "duplicate_views": [],
        "issues": []
    }
}
```

## IMPORTANT NOTES

1. **Be objective**: Don't assume the standard order. Actually LOOK at each panel.
2. **LEFT vs RIGHT is tricky**: 
   - RIGHT view = you see the subject's RIGHT side = subject faces LEFT in image
   - LEFT view = you see the subject's LEFT side = subject faces RIGHT in image
3. **Objects have fronts too**: Identify the canonical "front" based on design intent.
4. **Report issues**: If two panels look identical, flag it!

Now analyze this image. First understand the whole picture, then examine each panel."""

    # 补全生成提示词模板
    COMPLETION_PROMPT_TEMPLATE = """Generate a SINGLE panel showing the character from the {view_name} view ({angle}).

**CRITICAL: This is to COMPLETE a multi-view set. The character must be IDENTICAL to the reference.**

## VIEW REQUIREMENT
Generate ONLY the {view_name} view:
{view_description}

## CHARACTER REFERENCE
Use the attached reference image. The character must be:
- Identical pose, clothing, accessories
- Same proportions and details
- Only the camera angle changes

## STYLE
{style_instructions}

## OUTPUT
- Single panel, no grid
- Clean neutral background (gray or white)
- Character centered
- Same scale as the reference panels

## SPATIAL LOCK
The character is FROZEN. Only camera position changes:
- Same pose, same expression
- Same clothing folds
- Same accessory positions
- NO adjustments for "better visibility"

Generate ONE clean panel of the {view_name} view."""

    def __init__(
        self,
        api_key: str = None,
        model_name: str = "gemini-2.0-flash",
        max_retries: int = 3,
        verbose: bool = True
    ):
        """
        初始化验证器
        
        Args:
            api_key: Gemini API 密钥
            model_name: 用于分析的模型
            max_retries: 补全的最大重试次数
            verbose: 是否输出详细日志
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.max_retries = max_retries
        self.verbose = verbose
        
        if not GENAI_AVAILABLE:
            raise ImportError("需要安装 google-generativeai: pip install google-generativeai")
        
        if not PIL_AVAILABLE:
            raise ImportError("需要安装 Pillow: pip install Pillow")
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
    
    def _log(self, message: str):
        """输出日志"""
        if self.verbose:
            print(message)
    
    def _get_view_description(self, view_name: str) -> Tuple[str, str]:
        """获取视角的描述和角度"""
        view_info = {
            "front": ("0°", "Camera directly in front. We see the character's face."),
            "front_right": ("45°", "Camera at 45° right-front. Face visible at angle, right side more visible."),
            "right": ("90°", "Camera on character's RIGHT side. Face points toward LEFT edge of image."),
            "back_right": ("135°", "Camera at 135°. Mostly back visible, slight right side."),
            "back": ("180°", "Camera directly behind. We see the character's back, NO face."),
            "back_left": ("225°", "Camera at 225°. Mostly back visible, slight left side."),
            "left": ("270°", "Camera on character's LEFT side. Face points toward RIGHT edge of image."),
            "front_left": ("315°", "Camera at 45° left-front. Face visible at angle, left side more visible."),
            "top": ("↓", "Camera directly above, looking down at top of head."),
            "bottom": ("↑", "Camera directly below, looking up at soles of feet."),
        }
        return view_info.get(view_name, ("?", f"Unknown view: {view_name}"))
    
    def analyze_image(self, image_path: str) -> ValidationResult:
        """
        分析多视角图片，检测每个面板的实际视角
        
        Args:
            image_path: 图片路径
        
        Returns:
            包含检测结果的 ValidationResult
        """
        self._log(f"[分析] 正在分析图片: {image_path}")
        
        # 加载图片
        img = Image.open(image_path)
        
        # 调用 AI 分析
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content([
            self.DETECTION_PROMPT,
            img
        ])
        
        # 解析响应
        response_text = response.text
        self._log(f"[AI响应] {response_text[:500]}...")
        
        # 提取 JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_str = response_text
        
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            self._log(f"[警告] JSON 解析失败: {e}")
            # 返回空结果
            return ValidationResult(
                is_complete=False,
                expected_views=[],
                detected_views=[],
                missing_views=[],
                duplicate_views=[],
                panel_analyses=[],
                suggestions=["AI 响应解析失败，请重试"]
            )
        
        # 解析全局分析信息
        global_analysis = result.get("global_analysis", {})
        subject_type = global_analysis.get("subject_type", "unknown")
        layout = global_analysis.get("layout", "unknown")
        subject_desc = global_analysis.get("subject_description", "")
        
        self._log(f"[主体类型] {subject_type}: {subject_desc}")
        self._log(f"[布局] {layout}")
        
        # 构建分析结果
        panel_analyses = []
        detected_views = []
        
        # 从 verification 中获取问题信息
        verification = result.get("verification", {})
        ai_detected_missing = verification.get("missing_views", [])
        ai_detected_duplicates = verification.get("duplicate_views", [])
        issues = verification.get("issues", [])
        
        if ai_detected_missing:
            self._log(f"[AI检测-缺失] {ai_detected_missing}")
        if ai_detected_duplicates:
            self._log(f"[AI检测-重复] {ai_detected_duplicates}")
        for issue in issues:
            self._log(f"[AI检测-问题] {issue}")
        
        for panel in result.get("panels", []):
            view = panel.get("detected_view", "unknown")
            detected_views.append(view)
            
            # 提取关键特征和推理
            key_features = panel.get("key_features", "")
            reasoning = panel.get("reasoning", "")
            position = panel.get("position", "")
            
            # 构建描述
            description_parts = []
            if position:
                description_parts.append(f"位置: {position}")
            if reasoning:
                description_parts.append(reasoning)
            if key_features:
                description_parts.append(f"特征: {key_features}")
            
            panel_analyses.append(PanelAnalysis(
                panel_index=panel.get("panel_index", 0),
                detected_view=view,
                confidence=panel.get("confidence", 0.0),
                description=" | ".join(description_parts) if description_parts else "",
                issues=[]
            ))
        
        self._log(f"[检测结果] 检测到 {len(detected_views)} 个面板: {detected_views}")
        
        return ValidationResult(
            is_complete=True,  # 这里只是分析，不验证完整性
            expected_views=[],
            detected_views=detected_views,
            missing_views=[],
            duplicate_views=[],
            panel_analyses=panel_analyses,
            suggestions=[]
        )
    
    def validate(
        self,
        image_path: str,
        expected_views: List[str]
    ) -> ValidationResult:
        """
        验证图片是否包含所有期望的视角
        
        Args:
            image_path: 图片路径
            expected_views: 期望的视角列表
        
        Returns:
            验证结果
        """
        # 先分析图片
        analysis = self.analyze_image(image_path)
        
        # 规范化视角名称
        expected_normalized = [v.lower().replace("-", "_") for v in expected_views]
        detected_normalized = [v.lower().replace("-", "_") for v in analysis.detected_views]
        
        # 计算缺失和重复
        missing = []
        for expected in expected_normalized:
            if expected not in detected_normalized:
                missing.append(expected)
        
        # 检测重复
        from collections import Counter
        view_counts = Counter(detected_normalized)
        duplicates = [v for v, count in view_counts.items() if count > 1]
        
        # 生成建议
        suggestions = []
        if missing:
            suggestions.append(f"缺失视角: {', '.join(missing)}")
        if duplicates:
            suggestions.append(f"重复视角: {', '.join(duplicates)}")
        
        is_complete = len(missing) == 0 and len(duplicates) == 0
        
        self._log(f"[验证] 期望: {expected_normalized}")
        self._log(f"[验证] 检测: {detected_normalized}")
        self._log(f"[验证] 缺失: {missing}")
        self._log(f"[验证] 完整: {is_complete}")
        
        return ValidationResult(
            is_complete=is_complete,
            expected_views=expected_normalized,
            detected_views=detected_normalized,
            missing_views=missing,
            duplicate_views=duplicates,
            panel_analyses=analysis.panel_analyses,
            suggestions=suggestions
        )
    
    def generate_missing_view(
        self,
        reference_image_path: str,
        missing_view: str,
        style: str = None,
        output_dir: str = "outputs",
        asset_id: str = None
    ) -> Optional[str]:
        """
        生成缺失的视角
        
        Args:
            reference_image_path: 参考图片路径（用于保持角色一致性）
            missing_view: 缺失的视角名称
            style: 风格描述
            output_dir: 输出目录
            asset_id: 资源 ID（用于统一命名，如 294829fb-6da7-45a7-bbfe-5318999084c7）
        
        Returns:
            生成的图片路径，失败返回 None
        """
        self._log(f"[补全] 正在生成缺失视角: {missing_view}")
        
        # 获取视角描述
        angle, description = self._get_view_description(missing_view)
        
        # 构建风格指令
        if style:
            from prompts.styles import find_matching_style
            preset = find_matching_style(style)
            if preset:
                style_instructions = preset.style_instruction
            else:
                style_instructions = f"Style: {style}"
        else:
            style_instructions = "Match the style of the reference image exactly."
        
        # 构建提示词
        prompt = self.COMPLETION_PROMPT_TEMPLATE.format(
            view_name=missing_view.upper().replace("_", "-"),
            angle=angle,
            view_description=description,
            style_instructions=style_instructions
        )
        
        # 加载参考图片
        ref_img = Image.open(reference_image_path)
        
        # 调用图像生成模型
        try:
            model = genai.GenerativeModel("models/gemini-2.0-flash-exp-image-generation")
            response = model.generate_content(
                [prompt, ref_img],
                generation_config=genai.GenerationConfig(
                    response_modalities=["image", "text"]
                )
            )
            
            # 提取生成的图片
            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # 使用统一的资源 ID 命名
                    # 格式: {asset_id}_{view}.png (如 294829fb-xxx_right.png)
                    if asset_id:
                        filename = f"{asset_id}_{missing_view}.png"
                    else:
                        # 如果没有提供 asset_id，尝试从参考图片名提取
                        ref_stem = Path(reference_image_path).stem
                        # 移除可能已有的 _view 后缀
                        for suffix in ['_front', '_right', '_back', '_left', '_top', '_bottom', 
                                       '_front_right', '_front_left', '_back_right', '_back_left']:
                            if ref_stem.endswith(suffix):
                                ref_stem = ref_stem[:-len(suffix)]
                                break
                        filename = f"{ref_stem}_{missing_view}.png"
                    
                    output_path = Path(output_dir) / filename
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    
                    self._log(f"[补全] 生成成功: {output_path}")
                    return str(output_path)
            
            self._log(f"[补全] 响应中未找到图片")
            return None
            return None
            
        except Exception as e:
            self._log(f"[补全] 生成失败: {e}")
            return None
    
    def _extract_asset_id(self, image_path: str) -> str:
        """
        从图片路径提取资源 ID
        
        支持的格式:
        - 294829fb-6da7-45a7-bbfe-5318999084c7.jpg → 294829fb-6da7-45a7-bbfe-5318999084c7
        - 294829fb-6da7-45a7-bbfe-5318999084c7_front.png → 294829fb-6da7-45a7-bbfe-5318999084c7
        - character_20251226_013442.jpg → character_20251226_013442
        
        Args:
            image_path: 图片路径
        
        Returns:
            资源 ID 字符串
        """
        stem = Path(image_path).stem
        
        # 移除可能已有的视角后缀
        view_suffixes = [
            '_front', '_right', '_back', '_left', 
            '_top', '_bottom',
            '_front_right', '_front_left', 
            '_back_right', '_back_left'
        ]
        
        for suffix in view_suffixes:
            if stem.endswith(suffix):
                stem = stem[:-len(suffix)]
                break
        
        return stem
    
    def validate_and_complete(
        self,
        image_path: str,
        expected_views: List[str],
        reference_image: str = None,
        style: str = None,
        output_dir: str = "outputs",
        max_iterations: int = 3,
        asset_id: str = None
    ) -> Dict:
        """
        验证并自动补全缺失视角
        
        这是主要的入口函数，会：
        1. 分析生成的图片
        2. 检测缺失的视角
        3. 自动生成缺失视角
        4. 返回完整结果
        
        Args:
            image_path: 生成的多视角图片路径
            expected_views: 期望的视角列表
            reference_image: 原始参考图片（用于补全生成）
            style: 风格描述
            output_dir: 输出目录
            max_iterations: 最大补全迭代次数
            asset_id: 资源 ID（统一命名，如 294829fb-xxx）。若不提供则自动从 image_path 提取
        
        Returns:
            包含验证结果和补全图片路径的字典
        """
        self._log("=" * 60)
        self._log("开始多视角验证与补全流程")
        self._log("=" * 60)
        
        # 自动提取资源 ID（如果未提供）
        if not asset_id:
            asset_id = self._extract_asset_id(image_path)
        self._log(f"[资源ID] {asset_id}")
        
        # 智能选择参考图片
        # 优先使用切割后的 front 视图，这样能保证更高的角色一致性
        if not reference_image:
            # 尝试查找 {asset_id}_front.png
            image_dir = Path(image_path).parent
            front_candidates = [
                image_dir / f"{asset_id}_front.png",
                image_dir / f"{asset_id}_front.jpg",
                image_dir / f"{asset_id}_front.webp",
            ]
            
            for front_path in front_candidates:
                if front_path.exists():
                    reference_image = str(front_path)
                    self._log(f"[参考图] 使用切割后的 front 视图: {front_path.name}")
                    break
            
            # 如果没找到 front，回退到原始图片
            if not reference_image:
                reference_image = image_path
                self._log(f"[参考图] 未找到 front 视图，使用原始图片")
        else:
            self._log(f"[参考图] 使用指定的参考图: {Path(reference_image).name}")
        
        result = {
            "asset_id": asset_id,
            "original_image": image_path,
            "reference_image": reference_image,
            "expected_views": expected_views,
            "validation_passed": False,
            "iterations": 0,
            "completed_views": [],
            "missing_views": [],
            "generated_panels": [],
            "final_status": "pending"
        }
        
        for iteration in range(max_iterations):
            result["iterations"] = iteration + 1
            self._log(f"\n[迭代 {iteration + 1}/{max_iterations}]")
            
            # 验证当前图片
            validation = self.validate(image_path, expected_views)
            
            if validation.is_complete:
                self._log("[成功] 所有视角验证通过！")
                result["validation_passed"] = True
                result["completed_views"] = validation.detected_views
                result["final_status"] = "complete"
                break
            
            # 记录缺失视角
            result["missing_views"] = validation.missing_views
            
            if not validation.missing_views:
                # 有重复但不缺失
                self._log(f"[警告] 检测到重复视角: {validation.duplicate_views}")
                result["final_status"] = "has_duplicates"
                break
            
            # 尝试补全每个缺失视角
            for missing_view in validation.missing_views:
                self._log(f"\n[补全] 尝试生成: {missing_view}")
                
                generated_path = self.generate_missing_view(
                    reference_image_path=reference_image,
                    missing_view=missing_view,
                    style=style,
                    output_dir=output_dir,
                    asset_id=asset_id
                )
                
                if generated_path:
                    result["generated_panels"].append({
                        "view": missing_view,
                        "path": generated_path,
                        "iteration": iteration + 1
                    })
        
        # 最终状态
        if not result["validation_passed"]:
            if result["generated_panels"]:
                result["final_status"] = "partial_completion"
                self._log(f"\n[部分完成] 生成了 {len(result['generated_panels'])} 个补全面板")
            else:
                result["final_status"] = "failed"
                self._log("\n[失败] 无法完成所有视角")
        
        self._log("\n" + "=" * 60)
        self._log(f"验证结果: {result['final_status']}")
        self._log("=" * 60)
        
        return result
    
    def merge_panels(
        self,
        original_image: str,
        replacement_panels: List[Dict],
        expected_views: List[str],
        output_path: str = None
    ) -> Optional[str]:
        """
        将补全的面板合并回原图
        
        Args:
            original_image: 原始多视角图片
            replacement_panels: 要替换的面板 [{"view": "left", "path": "xxx.png"}, ...]
            expected_views: 期望的视角顺序
            output_path: 输出路径
        
        Returns:
            合并后的图片路径
        """
        # TODO: 实现面板合并逻辑
        # 1. 分割原图为面板
        # 2. 识别每个面板对应的视角
        # 3. 替换错误/重复的面板
        # 4. 重新拼接
        
        self._log("[合并] 面板合并功能开发中...")
        return None


def create_validator(api_key: str = None, verbose: bool = True) -> ViewValidator:
    """
    创建验证器实例的便捷函数
    
    Args:
        api_key: Gemini API 密钥
        verbose: 是否输出详细日志
    
    Returns:
        ViewValidator 实例
    """
    return ViewValidator(api_key=api_key, verbose=verbose)


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="多视角图片验证与补全工具")
    parser.add_argument("image", help="要验证的图片路径")
    parser.add_argument(
        "--views",
        nargs="+",
        default=["front", "right", "back", "left"],
        help="期望的视角列表"
    )
    parser.add_argument(
        "--reference",
        default=None,
        help="参考图片路径（用于补全生成）"
    )
    parser.add_argument(
        "--style",
        default=None,
        help="风格描述"
    )
    parser.add_argument(
        "--output",
        default="outputs/validated",
        help="输出目录"
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Gemini API Key"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="仅分析，不补全"
    )
    
    args = parser.parse_args()
    
    # 创建验证器
    validator = create_validator(api_key=args.token)
    
    if args.analyze_only:
        # 仅分析模式
        result = validator.validate(args.image, args.views)
        print(f"\n检测到的视角: {result.detected_views}")
        print(f"缺失的视角: {result.missing_views}")
        print(f"重复的视角: {result.duplicate_views}")
        print(f"验证通过: {result.is_complete}")
    else:
        # 验证并补全模式
        result = validator.validate_and_complete(
            image_path=args.image,
            expected_views=args.views,
            reference_image=args.reference,
            style=args.style,
            output_dir=args.output
        )
        
        print(f"\n最终状态: {result['final_status']}")
        print(f"迭代次数: {result['iterations']}")
        print(f"生成的补全面板: {len(result['generated_panels'])}")
        
        for panel in result["generated_panels"]:
            print(f"  - {panel['view']}: {panel['path']}")
