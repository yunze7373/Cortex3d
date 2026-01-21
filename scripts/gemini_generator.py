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


# 使用共享配置中的默认模型（和代理模式完全一致）
DEFAULT_MODEL = IMAGE_MODEL  # models/nano-banana-pro-preview


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
    resolution: str = "2K",
    original_args = None,
    export_prompt: bool = False,
    subject_only: bool = False,
    with_props: list = None
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
        subject_only: 只处理主体，移除背景物体
        with_props: 要包含的道具列表
    
    Returns:
        生成的图片路径
    """
    _ensure_imports()
    
    # 配置 API
    genai.configure(api_key=api_key)
    
    print("="*60)
    print("Gemini 多视角图像生成器 (直连模式)")
    print("="*60)
    print(f"[模型] {model_name}")
    print(f"[角色描述] {character_description[:100]}...")
    print(f"[风格] {style}")
    print(f"[视角模式] {view_mode}")
    if reference_image_path:
        mode_label = "严格复制" if use_strict_mode else "参考图像"
        print(f"[{mode_label}] {reference_image_path}")
    if subject_only:
        print(f"[主体隔离] 只处理主体人物，移除背景物体")
    if with_props:
        print(f"[包含道具] {', '.join(with_props)}")
    print(f"[分辨率] {resolution}")
    print("-"*60)
    
    # 处理参考图像（转为 base64）
    reference_image_b64 = None
    if reference_image_path:
        try:
            with open(reference_image_path, 'rb') as f:
                image_bytes = f.read()
            reference_image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            # 获取 MIME 类型
            if reference_image_path.lower().endswith('.png'):
                mime = 'image/png'
            elif reference_image_path.lower().endswith(('.jpg', '.jpeg')):
                mime = 'image/jpeg'
            else:
                mime = 'image/png'
            reference_image_b64 = f"data:{mime};base64,{reference_image_b64}"
            print(f"[INFO] 参考图像已加载")
        except Exception as e:
            print(f"[WARNING] 无法加载参考图像: {e}")
            reference_image_b64 = None
    
    # 构建提示词（和代理模式完全一致）
    if use_strict_mode and reference_image_b64:
        from config import build_strict_copy_prompt
        full_prompt = build_strict_copy_prompt(
            view_mode=view_mode,
            custom_views=custom_views,
            style=style,
            subject_only=subject_only,
            with_props=with_props
        )
        print("[模式] 严格复制 - 100% 基于参考图像")
    elif reference_image_b64:
        from config import build_image_reference_prompt
        full_prompt = build_image_reference_prompt(
            character_description or "Extract character details and generate multi-view",
            view_mode=view_mode,
            custom_views=custom_views,
            style=style,
            subject_only=subject_only,
            with_props=with_props
        )
        print(f"[模式] 图像参考 - 提取特征生成 {view_mode if view_mode != 'custom' else str(custom_views)} 视角")
    else:
        full_prompt = build_multiview_prompt(
            character_description, 
            style=style,
            view_mode=view_mode,
            custom_views=custom_views,
            subject_only=subject_only,
            with_props=with_props
        )
    
    # 添加负面提示词
    if negative_prompt:
        print(f"[负面提示词] {negative_prompt[:60]}...")
    
    print("[INFO] 正在生成图像... (可能需要 30-60 秒)")
    
    try:
        # 准备 API 调用参数（和代理模式完全对齐）
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        
        # 分辨率映射
        resolution_map = {
            "1K": "1K",
            "2K": "2K",
            "4K": "4K"
        }
        image_size = resolution_map.get(resolution, "2K")
        
        # 宽高比（默认 3:2 适合四视图横排）
        aspect_ratio = "3:2"
        
        # 构建生成配置
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
        }
        
        # 安全设置（和代理一致）
        safety_settings = [
            {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
            {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
            {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
            {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
        ]
        
        # 定义回退模型（和代理模式完全一致）
        FALLBACK_MODELS = {
            "models/nano-banana-pro-preview": "gemini-2.5-flash-image",
            "nano-banana-pro-preview": "gemini-2.5-flash-image",
        }
        
        current_model = model_name
        MAX_RETRIES = 1
        
        for attempt in range(MAX_RETRIES + 1):
            print(f"[Gemini API] 尝试模型: {current_model} (尝试 {attempt+1}/{MAX_RETRIES+1})")
            
            # 创建模型
            model = genai.GenerativeModel(current_model)
        
            # 创建模型
            model = genai.GenerativeModel(current_model)
        
            # 准备内容列表
            contents = [full_prompt]
            
            # 如果有参考图像，添加到内容中
            if reference_image_b64:
                # 解析 data URL
                if reference_image_b64.startswith('data:'):
                    header, b64_data = reference_image_b64.split(',', 1)
                    mime_type = header.split(';')[0].split(':')[1]
                else:
                    b64_data = reference_image_b64
                    mime_type = 'image/png'
                
                # 添加图像部分
                contents.append({
                    'mime_type': mime_type,
                    'data': b64_data
                })
            
            # Gemini 优化：使用语义负面提示（正面描述所需场景）
            # 根据 Gemini API 文档建议，避免直接列出禁止项，而是强调正面要求
            if negative_prompt:
                # 将传统负面提示词转换为语义正面指令
                semantic_avoidance = """
## 🛡️ QUALITY REQUIREMENTS (what the image MUST have):
- Clean, anatomically correct figure with proper limb count and proportions
- Consistent pose maintained identically across all panels
- Head, gaze, and body orientation frozen in the same position in every view
- All limbs in exactly the same position and crossing order across views
- High quality, sharp details, no artifacts or distortions
- Clean panel layout with consistent sizing
- No text, labels, or overlays on the image"""
                contents[0] += semantic_avoidance
            
            # ===================================================================
            # 导出提示词模式：输出参数而不调用 API
            # ===================================================================
            if export_prompt:
                print("\n" + "="*70)
                print("📋 导出提示词和参数 (复制到 Gemini App 使用)")
                print("="*70)
                
                print(f"\n【推荐模型】")
                print(f"   nano-banana-pro-preview (最佳图像生成模型)")
                print(f"   备用: gemini-2.5-flash-image")
                print(f"   提示: 在 AI Studio 或 API 中使用上述模型名称")
                
                print(f"\n【配置参数建议】")
                print(f"   分辨率: {image_size}")
                print(f"   宽高比: {aspect_ratio}")
                print(f"   Temperature: {generation_config.get('temperature', 0.7)}")
                print(f"   Top P: {generation_config.get('top_p', 0.95)}")
                print(f"   Top K: {generation_config.get('top_k', 40)}")
                
                print(f"\n【完整提示词】")
                print("-"*70)
                print(contents[0])
                print("-"*70)
                
                # 显示负面提示词信息（原始版本，供参考）
                if negative_prompt:
                    print(f"\n【负面提示词信息】")
                    print(f"   📋 原始负面提示词 (已转换为语义正面指令):")
                    print(f"   {negative_prompt}")
                    print(f"   ")
                    print(f"   ✅ Gemini 优化: 已自动转换为 'QUALITY REQUIREMENTS' 正面描述")
                    print(f"   💡 根据 Gemini API 文档建议，使用语义负面提示效果更好")
                
                if reference_image_b64:
                    print(f"\n【⚠️  参考图像 - 重要】")
                    print(f"   文件路径: {reference_image_path}")
                    print(f"   图像类型: {mime_type}")
                    print(f"   ")
                    print(f"   📎 操作步骤:")
                    print(f"      1. 在 Gemini App 中点击 📎 (附件) 按钮")
                    print(f"      2. 上传图像: {reference_image_path}")
                    print(f"      3. 图像会显示在对话框中")
                    print(f"      4. 然后粘贴上面的【完整提示词】")
                    if use_strict_mode:
                        print(f"   ")
                        print(f"   🎯 严格模式: 生成的图像将 100% 基于上传的参考图")
                
                print(f"\n【安全设置】")
                print(f"   骚扰: BLOCK_ONLY_HIGH")
                print(f"   仇恨言论: BLOCK_ONLY_HIGH")
                print(f"   性暗示: BLOCK_ONLY_HIGH")
                print(f"   危险内容: BLOCK_ONLY_HIGH")
                
                print(f"\n{'='*70}")
                print("💡 完整使用流程:")
                print("="*70)
                print("\n第一步: 打开 Gemini App")
                print("   访问: https://gemini.google.com")
                print("   或使用 Gemini 移动应用")
                
                print("\n第二步: 选择模型")
                print("   在 AI Studio 中使用: nano-banana-pro-preview")
                print("   或在代码中调用: models/nano-banana-pro-preview")
                
                if reference_image_b64:
                    print("\n第三步: 上传参考图像 ⚠️ 先上传图像!")
                    print(f"   1. 点击对话框左下角的 📎 (附件) 图标")
                    print(f"   2. 选择图像文件: {reference_image_path}")
                    print(f"   3. 等待图像上传并显示在对话框中")
                    step_four = "第四步"
                else:
                    step_four = "第三步"
                
                print(f"\n{step_four}: 粘贴提示词")
                print("   1. 复制上面【完整提示词】部分的全部内容")
                print("   2. 粘贴到 Gemini 对话框中")
                if reference_image_b64:
                    print("   3. 确认图像和提示词都已在对话框中")
                
                print(f"\n第{'五' if reference_image_b64 else '四'}步: 发送并等待")
                print("   1. 点击发送按钮")
                print("   2. 等待 30-60 秒生成完成")
                print("   3. 生成的图像会显示在回复中")
                
                print(f"\n第{'六' if reference_image_b64 else '五'}步: 保存图像")
                print("   1. 右键点击生成的图像")
                print("   2. 选择 '保存图片为...'")
                print("   3. 保存到您的输出目录")
                
                print("\n" + "="*70)
                print("✅ 提示: 如果生成失败,请检查:")
                print("   - 是否选择了支持图像生成的模型")
                if reference_image_b64:
                    print("   - 参考图像是否已正确上传")
                print("   - 提示词是否完整复制(不要遗漏任何部分)")
                print("="*70 + "\n")
                
                # 导出模式下不实际调用 API，直接返回
                return None
            
            print(f"[Gemini API] 调用参数: image_size={image_size}, aspect_ratio={aspect_ratio}")
            
            try:
                # 调用 Gemini API
                response = model.generate_content(
                    contents,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # 检查响应
                if not response or not response.candidates:
                    print("[ERROR] 生成失败: 无返回内容")
                    if attempt < MAX_RETRIES:
                        continue  # 尝试回退模型
                    return None
                
                # 提取图像数据
                image_data = None
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        if part.inline_data.mime_type.startswith('image/'):
                            image_data = part.inline_data.data
                            break
                
                if not image_data:
                    print("[ERROR] API 未返回图像数据")
                    if attempt < MAX_RETRIES:
                        print(f"[INFO] 尝试使用回退模型...")
                        continue  # 尝试回退模型
                    print("[提示] Gemini API 可能不支持该模型的图像生成")
                    print("       请尝试使用 --mode proxy 通过代理服务访问")
                    return None
                
                # 保存图像
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"character_{timestamp}.png"
                filepath = output_path / filename
                
                # 解码并保存
                image_bytes = base64.b64decode(image_data) if isinstance(image_data, str) else image_data
                image = PIL_Image.open(io.BytesIO(image_bytes))
                image.save(str(filepath))
                
                print(f"[保存] {filepath}")
                
                # 成功，跳出重试循环
                break
                
            except Exception as e:
                error_msg = str(e)
                
                # 检测配额错误（ResourceExhausted / 429）
                is_quota_error = (
                    "429" in error_msg or 
                    "quota" in error_msg.lower() or 
                    "ResourceExhausted" in str(type(e).__name__)
                )
                
                # 检测模型不存在错误
                is_model_not_found = "not found" in error_msg.lower() or "404" in error_msg
                
                if is_quota_error:
                    print(f"\n⚠️  配额限制")
                    print(f"   模型 '{current_model}' 的免费配额已用完")
                    
                    # 检查是否需要回退模型
                    if attempt < MAX_RETRIES:
                        fallback_model = FALLBACK_MODELS.get(current_model)
                        if fallback_model and fallback_model != current_model:
                            print(f"   → 自动切换到回退模型: {fallback_model}")
                            current_model = fallback_model
                            continue  # 重试
                    
                    # 如果已经是最后一次尝试，给出友好提示
                    print(f"\n{'='*70}")
                    print(f"💡 解决方案 - 请选择以下任一选项:")
                    print(f"{'='*70}")
                    
                    # 构建基于实际参数的命令
                    if original_args:
                        base_cmd_parts = ["python scripts\\generate_character.py"]
                        
                        # 添加描述或图像输入
                        if hasattr(original_args, 'from_image') and original_args.from_image:
                            base_cmd_parts.append(f"--from-image {original_args.from_image}")
                        elif hasattr(original_args, 'description') and original_args.description:
                            base_cmd_parts.append(f'"{original_args.description}"')
                        
                        # 添加其他参数
                        if hasattr(original_args, 'strict') and original_args.strict:
                            base_cmd_parts.append("--strict")
                        if hasattr(original_args, 'resolution') and original_args.resolution and original_args.resolution != "2K":
                            base_cmd_parts.append(f"--resolution {original_args.resolution}")
                        if hasattr(original_args, 'views') and original_args.views and original_args.views != 4:
                            base_cmd_parts.append(f"--views {original_args.views}")
                        if hasattr(original_args, 'preprocess') and original_args.preprocess:
                            base_cmd_parts.append("--preprocess")
                        
                        proxy_cmd = " ".join(base_cmd_parts + ["--mode proxy --token 'your-aiproxy-token'"])
                        direct_cmd = " ".join(base_cmd_parts + ["--mode direct --token 'another-gemini-key'"])
                        
                        print(f"\n📌 选项 1: 切换到代理模式 (推荐)")
                        print(f"   {proxy_cmd}")
                        
                        print(f"\n📌 选项 2: 使用不同的 Gemini API Key")
                        print(f"   {direct_cmd}")
                    else:
                        # 降级到通用提示
                        print(f"\n📌 选项 1: 切换到代理模式 (--mode proxy --token 'your-token')")
                        print(f"📌 选项 2: 使用不同的 API Key (--mode direct --token 'new-key')")
                    
                    print(f"\n📌 选项 3: 等待配额恢复 (24小时后)")
                    print(f"📌 选项 4: 升级付费计划 (https://ai.google.dev/pricing)")
                    
                    print(f"\n{'='*70}")
                    print(f"💬 推荐使用代理模式以获得最佳体验")
                    print(f"{'='*70}\n")
                    return None
                    
                elif is_model_not_found:
                    print(f"\n❌ 模型不存在: {current_model}")
                    
                    if attempt < MAX_RETRIES:
                        fallback_model = FALLBACK_MODELS.get(current_model)
                        if fallback_model and fallback_model != current_model:
                            print(f"   → 自动切换到回退模型: {fallback_model}")
                            current_model = fallback_model
                            continue  # 重试
                    
                    # 构建基于实际参数的代理模式命令
                    if original_args:
                        base_cmd_parts = ["python scripts\\generate_character.py"]
                        if hasattr(original_args, 'from_image') and original_args.from_image:
                            base_cmd_parts.append(f"--from-image {original_args.from_image}")
                        if hasattr(original_args, 'strict') and original_args.strict:
                            base_cmd_parts.append("--strict")
                        proxy_cmd = " ".join(base_cmd_parts + ["--mode proxy --token 'your-aiproxy-token'"])
                        print(f"   💡 建议使用代理模式: {proxy_cmd}")
                    else:
                        print(f"   💡 建议使用代理模式 (--mode proxy --token 'your-token')")
                    return None
                    
                else:
                    # 其他未知错误
                    print(f"\n❌ 生成失败: {error_msg}")
                    
                    # 尝试回退模型
                    if attempt < MAX_RETRIES:
                        fallback_model = FALLBACK_MODELS.get(current_model)
                        if fallback_model and fallback_model != current_model:
                            print(f"   → 尝试回退模型: {fallback_model}")
                            current_model = fallback_model
                            continue  # 重试
                    
                    # 最后一次尝试，打印详细错误
                    print(f"\n🔍 详细错误信息:")
                    import traceback
                    traceback.print_exc()
                    return None
                # 成功，跳出重试循环
                break
                
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] 生成失败: {error_msg}")
                
                # 检查是否需要回退模型
                if attempt < MAX_RETRIES:
                    # 检查是否是配额错误或模型不支持错误
                    if "quota" in error_msg.lower() or "429" in error_msg or "not found" in error_msg.lower():
                        fallback_model = FALLBACK_MODELS.get(current_model)
                        if fallback_model and fallback_model != current_model:
                            print(f"⚠️  模型 {current_model} 调用失败，自动切换到回退模型: {fallback_model}")
                            current_model = fallback_model
                            continue  # 重试
                
                # 如果是最后一次尝试，打印详细错误并退出
                if attempt >= MAX_RETRIES:
                    import traceback
                    traceback.print_exc()
                    return None
        
        # 如果成功保存了图像，继续处理
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


# 已移除 generate_with_imagen 和 generate_with_gemini_vision 函数
# 直连模式应该和代理模式使用相同的逻辑，只是访问路径不同


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


# 分辨率控制已在 API 调用时通过 image_size 参数指定
# 无需后处理调整


def analyze_image_for_character(image_path: str, api_key: str, user_guidance: str = None, original_args = None) -> Optional[str]:
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
        
        # 创建视觉模型（和代理模式完全一致，使用 gemini-2.0-flash）
        model = genai.GenerativeModel("gemini-2.0-flash")
        
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
        error_msg = str(e)
        
        # 检测配额错误
        is_quota_error = (
            "429" in error_msg or 
            "quota" in error_msg.lower() or 
            "ResourceExhausted" in str(type(e).__name__)
        )
        
        if is_quota_error:
            print(f"\n⚠️  配额限制: gemini-2.0-flash 的免费配额已用完")
            print(f"\n💡 建议: 使用代理模式可避免配额限制")
            if original_args:
                base_cmd_parts = ["python scripts\\generate_character.py"]
                if hasattr(original_args, 'from_image') and original_args.from_image:
                    base_cmd_parts.append(f"--from-image {original_args.from_image}")
                if hasattr(original_args, 'strict') and original_args.strict:
                    base_cmd_parts.append("--strict")
                proxy_cmd = " ".join(base_cmd_parts + ["--mode proxy --token 'your-aiproxy-token'"])
                print(f"   {proxy_cmd}\n")
        else:
            print(f"[ERROR] 图像分析失败: {error_msg}")
        
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
