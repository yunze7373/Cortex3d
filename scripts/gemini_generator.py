#!/usr/bin/env python3
"""
Gemini 多视角图像生成器
使用 Gemini API 生成四视图角色设计图

使用共享配置: 从 config.py 导入提示词模板和模型名称

依赖:
    pip install google-generativeai pillow
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import base64
import io

# 导入共享配置
from config import IMAGE_MODEL, build_multiview_prompt

# Lazy imports
genai = None
PIL_Image = None
cv2 = None
np = None


def _ensure_imports():
    """延迟导入依赖库"""
    global genai, PIL_Image, cv2, np
    
    if genai is None:
        try:
            import google.generativeai as _genai
            from PIL import Image as _Image
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            genai = _genai
            PIL_Image = _Image
        except ImportError as e:
            raise ImportError(
                f"缺少必要依赖: {e}\n"
                "请运行: pip install google-generativeai pillow"
            )
    
    # 可选的 OpenCV 导入（用于图像处理）
    if cv2 is None:
        try:
            import cv2 as _cv2
            import numpy as _np
            cv2 = _cv2
            np = _np
        except ImportError:
            pass  # 如果没有 opencv，某些功能会被禁用


# 使用共享配置中的默认模型
DEFAULT_MODEL = IMAGE_MODEL


# =============================================================================
# Gemini API 调用
# =============================================================================

def generate_character_views(
    character_description: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    output_dir: str = "test_images",
    auto_cut: bool = True,
    style: str = "cinematic character",
    view_mode: str = "4-view",
    custom_views: list = None,
    negative_prompt: str = None,
    reference_image_path: str = None,
    use_strict_mode: bool = False,
    resolution: str = "2K"
) -> Optional[str]:
    """
    使用 Gemini API 生成多视图角色图像
    
    Args:
        character_description: 角色描述
        api_key: Gemini API Key
        model_name: 模型名称
        output_dir: 输出目录
        auto_cut: 是否自动切割
        style: 风格描述
        view_mode: 视角模式 (4-view, 6-view, 8-view, custom)
        custom_views: 自定义视角列表
        negative_prompt: 负面提示词
        reference_image_path: 参考图像路径（用于图生图）
        use_strict_mode: 严格复制模式（基于参考图像）
        resolution: 目标分辨率 (1K/2K/4K)，通过后处理实现
    
    Returns:
        生成的图片路径
    """
    _ensure_imports()
    
    # 配置 API
    genai.configure(api_key=api_key)
    
    print("="*60)
    print("Gemini 多视角图像生成器")
    print("="*60)
    print(f"[模型] {model_name}")
    print(f"[角色描述] {character_description[:100]}...")
    print(f"[风格] {style}")
    print(f"[视角模式] {view_mode}")
    if reference_image_path:
        mode_label = "严格复制" if use_strict_mode else "参考图像"
        print(f"[{mode_label}] {reference_image_path}")
    print(f"[目标分辨率] {resolution}")
    print("-"*60)
    
    # 创建模型
    model = genai.GenerativeModel(model_name)
    
    # 处理参考图像
    reference_image = None
    if reference_image_path:
        try:
            reference_image = PIL_Image.open(reference_image_path)
            print(f"[INFO] 参考图像已加载: {reference_image.size}")
        except Exception as e:
            print(f"[WARNING] 无法加载参考图像: {e}")
            reference_image = None
    
    # 构建提示词
    if use_strict_mode and reference_image:
        # 严格复制模式：基于参考图像生成多视角
        from config import build_strict_copy_prompt
        full_prompt = build_strict_copy_prompt(character_description or "the character in the image")
        print("[模式] 严格复制 - 100% 基于参考图像")
    elif reference_image:
        # 参考图像模式：提取特征并生成多视角
        from config import build_image_reference_prompt
        full_prompt = build_image_reference_prompt(
            character_description or "Extract character details and generate multi-view"
        )
        print("[模式] 图像参考 - 提取特征生成多视角")
    else:
        # 普通文本生成模式
        full_prompt = build_multiview_prompt(
            character_description, 
            style=style,
            view_mode=view_mode,
            custom_views=custom_views
        )
    
    # 添加负面提示词
    if negative_prompt:
        full_prompt += f"\n\nNEGATIVE PROMPT (AVOID THESE):\n{negative_prompt}"
        print(f"[负面提示词] {negative_prompt[:60]}...")
    
    print("[INFO] 正在生成图像... (可能需要 30-60 秒)")
    
    try:
        # 安全设置
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }

        # 生成内容 (启用图像生成)
        # 如果有参考图像，将其包含在请求中
        if reference_image:
            response = model.generate_content(
                [full_prompt, reference_image],
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                ),
                safety_settings=safety_settings
            )
        else:
            response = model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                ),
                safety_settings=safety_settings
            )
        
        # 检查响应
        if not response.candidates:
            print("[ERROR] 生成失败: 无返回内容")
            return None
        
        # 查找图像数据
        image_data = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                if part.inline_data.mime_type.startswith('image/'):
                    image_data = part.inline_data.data
                    break
        
        if not image_data:
            # 如果没有直接的图像数据，尝试使用 Imagen
            print("[INFO] 尝试使用 Imagen 生成...")
            return generate_with_imagen(character_description, api_key, output_dir, auto_cut)
        
        # 保存图像
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"character_{timestamp}.png"
        filepath = output_path / filename
        
        # 解码并保存
        image_bytes = base64.b64decode(image_data) if isinstance(image_data, str) else image_data
        image = PIL_Image.open(io.BytesIO(image_bytes))
        
        # 分辨率调整（如果需要）
        image = _adjust_resolution(image, resolution)
        
        image.save(str(filepath))
        
        print(f"[保存] {filepath}")
        
        # 自动切割
        if auto_cut:
            try:
                from prompts.views import get_views_by_names, get_views_for_mode
                
                # 计算期望的视脚列表
                if view_mode == "custom" and custom_views:
                    expected_view_objs = get_views_by_names(custom_views)
                else:
                    expected_view_objs = get_views_for_mode(view_mode)
                expected_views = [v.name for v in expected_view_objs]
                
                cut_and_save(str(filepath), output_dir, expected_views=expected_views)
            except Exception as e:
                print(f"[WARNING] 无法计算期望视角: {e}, 使用默认切割")
                cut_and_save(str(filepath), output_dir)
        
        return str(filepath)
        
    except Exception as e:
        print(f"[ERROR] 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_with_imagen(
    character_description: str,
    api_key: str,
    output_dir: str = "test_images",
    auto_cut: bool = True
) -> Optional[str]:
    """
    使用 Imagen 3 模型生成图像
    
    Args:
        character_description: 角色描述
        api_key: Gemini API Key
        output_dir: 输出目录
        auto_cut: 是否自动切割
    
    Returns:
        生成的图片路径
    """
    _ensure_imports()
    
    genai.configure(api_key=api_key)
    
    # 使用 Imagen 模型
    try:
        imagen = genai.ImageGenerationModel("imagen-3.0-generate-002")
    except Exception:
        print("[WARNING] Imagen 模型不可用，尝试其他方法...")
        return generate_with_gemini_vision(character_description, api_key, output_dir, auto_cut)
    
    # 构建简洁的 Imagen 提示词
    imagen_prompt = f"""Professional 3D character reference sheet, quadriptych layout with 4 orthographic views (front, back, left side, right side).

Character: {character_description}

Style: Hyper-realistic 3D CGI render, 8K textures, A-pose standing pose, pure light grey background (#D3D3D3), clear silhouettes, no text, no watermarks."""

    print("[INFO] 使用 Imagen 3 生成...")
    
    try:
        result = imagen.generate_images(
            prompt=imagen_prompt,
            number_of_images=1,
            aspect_ratio="4:3",  # 适合四宫格
            safety_filter_level="block_only_high",
        )
        
        if not result.images:
            print("[ERROR] Imagen 未返回图像")
            return None
        
        # 保存图像
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"character_{timestamp}.png"
        filepath = output_path / filename
        
        result.images[0].save(str(filepath))
        print(f"[保存] {filepath}")
        
        # 自动切割
        if auto_cut:
            cut_and_save(str(filepath), output_dir)
        
        return str(filepath)
        
    except Exception as e:
        print(f"[ERROR] Imagen 生成失败: {e}")
        return generate_with_gemini_vision(character_description, api_key, output_dir, auto_cut)


def generate_with_gemini_vision(
    character_description: str,
    api_key: str,
    output_dir: str = "test_images",
    auto_cut: bool = True
) -> Optional[str]:
    """
    使用 Gemini 2.0 Flash 的原生图像生成能力
    """
    _ensure_imports()
    
    genai.configure(api_key=api_key)
    
    print("[INFO] 使用 Gemini 2.0 Flash 原生图像生成...")
    
    # Gemini 2.0 Flash 支持原生图像输出
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    
    prompt = f"""Generate an image: A professional 3D character modeling reference sheet.

Layout: 4 panels arranged horizontally in a single row:
- Panel 1 (Left): Front view (0°) - Face visible
- Panel 2: Right side view (90°) - Right ear visible
- Panel 3: Back view (180°) - Back of head visible
- Panel 4 (Right): Left side view (270°) - Left ear visible

Character: {character_description}

Requirements:
- A-pose (arms 45° from body)
- Orthographic projection (no perspective)
- Pure light grey background
- Hyper-realistic 3D CGI style
- 8K quality textures
- No text or watermarks
- Character must be identical in all 4 views
- Same pose in all panels"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="image/png",
            )
        )
        
        # 提取图像
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # 保存图像
                    output_path = Path(output_dir)
                    output_path.mkdir(parents=True, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"character_{timestamp}.png"
                    filepath = output_path / filename
                    
                    image_data = part.inline_data.data
                    image = PIL_Image.open(io.BytesIO(image_data))
                    image.save(str(filepath))
                    
                    print(f"[保存] {filepath}")
                    
                    if auto_cut:
                        cut_and_save(str(filepath), output_dir)
                    
                    return str(filepath)
        
        print("[ERROR] 未获取到图像数据")
        print("[TIP] 请尝试手动使用 Gemini 网页版生成图像")
        return None
        
    except Exception as e:
        print(f"[ERROR] 生成失败: {e}")
        print("\n" + "="*60)
        print("备选方案: 手动生成")
        print("="*60)
        print("1. 访问 https://gemini.google.com/")
        print("2. 使用以下提示词生成图像:")
        print("-"*60)
        print(prompt[:500] + "...")
        print("-"*60)
        print("3. 下载图像到 test_images/ 目录")
        print("4. 运行: python scripts/image_processor.py test_images/your_image.png")
        return None


def cut_and_save(image_path: str, output_dir: str, expected_views: list = None):
    """
    调用 image_processor 切割图像
    """
    script_dir = Path(__file__).parent
    sys.path.insert(0, str(script_dir))
    
    try:
        from image_processor import process_quadrant_image
        
        print("\n[INFO] 自动切割四视图...")
        process_quadrant_image(
            input_path=image_path,
            output_dir=output_dir,
            remove_bg_flag=True,
            expected_views=expected_views,
            margin=5
        )
    except ImportError:
        print("[WARNING] 无法导入 image_processor，跳过自动切割")
        print("[TIP] 运行: python scripts/image_processor.py " + image_path)
    except Exception as e:
        print(f"[WARNING] 切割失败: {e}")


def _adjust_resolution(image: "PIL_Image.Image", resolution: str) -> "PIL_Image.Image":
    """
    调整图像分辨率
    
    Args:
        image: PIL 图像对象
        resolution: 目标分辨率 (1K/2K/4K)
    
    Returns:
        调整后的图像
    """
    resolution_map = {
        "1K": 1024,
        "2K": 2048,
        "4K": 4096
    }
    
    target_size = resolution_map.get(resolution, 2048)
    
    # 如果图像已经足够大，保持原样
    if max(image.size) >= target_size:
        print(f"[分辨率] {image.size[0]}x{image.size[1]} (无需调整)")
        return image
    
    # 计算新尺寸（保持宽高比）
    aspect_ratio = image.size[0] / image.size[1]
    if image.size[0] > image.size[1]:
        new_width = target_size
        new_height = int(target_size / aspect_ratio)
    else:
        new_height = target_size
        new_width = int(target_size * aspect_ratio)
    
    # 使用高质量重采样
    resized = image.resize((new_width, new_height), PIL_Image.Resampling.LANCZOS)
    print(f"[分辨率] {image.size[0]}x{image.size[1]} → {new_width}x{new_height} ({resolution})")
    
    return resized


def analyze_image_for_character(image_path: str, api_key: str, user_guidance: str = None) -> Optional[str]:
    """
    使用 Gemini 分析图片，提取角色特征描述
    
    Args:
        image_path: 图片路径
        api_key: Gemini API Key
        user_guidance: 用户指导（可选，指定分析哪个人物或关注什么细节）
    
    Returns:
        角色描述文本
    """
    _ensure_imports()
    
    genai.configure(api_key=api_key)
    
    try:
        # 加载图像
        image = PIL_Image.open(image_path)
        
        # 创建视觉模型
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # 构建分析提示词
        analysis_prompt = """Analyze this image and provide a detailed character description for 3D modeling reference.

Focus on:
- Physical appearance (face, hair, body type)
- Clothing and accessories (materials, colors, details)
- Notable features or distinctive elements
- Overall style and aesthetic

Provide a clear, structured description that can be used to generate multi-view character references."""
        
        if user_guidance:
            analysis_prompt += f"\n\nUser guidance: {user_guidance}"
        
        # 发送请求
        response = model.generate_content([analysis_prompt, image])
        
        if response.text:
            return response.text.strip()
        else:
            print("[WARNING] 图像分析未返回文本")
            return None
            
    except Exception as e:
        print(f"[ERROR] 图像分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="使用 Gemini API 生成四视角角色设计图"
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="角色描述 (例如: '末日幸存者，穿着破旧西装')"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="Gemini API Key (或设置 GEMINI_API_KEY 环境变量)"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="模型名称 (默认: gemini-2.0-flash-exp)"
    )
    parser.add_argument(
        "--output", "-o",
        default="test_images",
        help="输出目录 (默认: test_images)"
    )
    parser.add_argument(
        "--no-cut",
        action="store_true",
        help="不自动切割图像"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互模式"
    )
    
    args = parser.parse_args()
    
    # 检查 API Key
    if not args.api_key:
        print("[ERROR] 请设置 Gemini API Key:")
        print("  export GEMINI_API_KEY='your-api-key'")
        print("  或使用 --api-key 参数")
        sys.exit(1)
    
    # 交互模式
    if args.interactive or not args.description:
        print("\n" + "="*60)
        print("Gemini 多视角角色图像生成器 (交互模式)")
        print("="*60)
        print("\n请描述你想要生成的角色:")
        print("(例如: 末日幸存者，穿着破烂的西装，手持手枪)")
        print("-"*60)
        
        description = input("\n角色描述: ").strip()
        if not description:
            print("[ERROR] 请输入角色描述")
            sys.exit(1)
    else:
        description = args.description
    
    # 生成图像
    result = generate_character_views(
        character_description=description,
        api_key=args.api_key,
        model_name=args.model,
        output_dir=args.output,
        auto_cut=not args.no_cut
    )
    
    if result:
        print("\n" + "="*60)
        print("✅ 生成完成!")
        print("="*60)
        print(f"原始图像: {result}")
        print(f"切割视图: {args.output}/ 目录下的 *_front.png, *_back.png 等")
    else:
        print("\n[FAILED] 图像生成未成功")
        sys.exit(1)


if __name__ == "__main__":
    main()
