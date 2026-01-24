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
            import google.genai as _genai
            from PIL import Image as _Image
            from google.genai.types import HarmCategory, HarmBlockThreshold
            genai = _genai
            PIL_Image = _Image
        except ImportError as e:
            raise ImportError(
                f"缺少必要依赖: {e}\n"
                "请运行: pip install google-genai pillow"
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
            elif reference_image_path.lower().endswith('.webp'):
                mime = 'image/webp'
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
        from google.genai.types import HarmCategory, HarmBlockThreshold
        
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


# =============================================================================
# 新增编辑功能 - P0 高优先级
# =============================================================================

def edit_character_elements(
    source_image_path: str,
    edit_instruction: str,
    character_description: str,
    api_key: str,
    model_name: str = None,  # 默认使用 gemini-2.5-flash-image
    output_dir: str = "test_images",
    auto_cut: bool = True,
    style: str = "cinematic character",
    export_prompt: bool = False,
    subject_only: bool = False,
    with_props: list = None,
    mode: str = "proxy",  # 新增: 支持 proxy/direct
    proxy_base_url: str = None
) -> Optional[str]:
    """
    编辑角色的元素(添加/移除/修改)
    
    使用 Gemini 2.5 Flash Image 模型进行图像编辑，保持原始风格、光照和透视效果。
    
    Args:
        source_image_path: 源图像路径
        edit_instruction: 编辑指令 ("add:xxx", "remove:xxx", "modify:xxx")
        character_description: 角色描述
        api_key: API Key (代理模式为 proxy token，直连模式为 Gemini API Key)
        model_name: 模型名称 (默认: gemini-2.5-flash-image)
        output_dir: 输出目录
        auto_cut: 是否自动切割
        style: 风格描述
        export_prompt: 是否导出提示词
        subject_only: 是否仅主体
        with_props: 配件列表
        mode: API 调用模式 ("proxy" 或 "direct")
        proxy_base_url: 代理服务地址 (仅 proxy 模式)
    
    Returns:
        编辑后图像的路径
    """
    from pathlib import Path
    from image_editor_utils import parse_edit_instruction, compose_edit_prompt, load_image_as_base64
    
    _ensure_imports()
    
    # 使用正确的图像编辑模型
    if not model_name:
        model_name = "gemini-2.5-flash-image"
    
    # 解析编辑指令
    edit_type, edit_detail = parse_edit_instruction(edit_instruction)
    
    print(f"\n[编辑模式] {edit_type.upper()}")
    print(f"  原图: {Path(source_image_path).name}")
    print(f"  操作: {edit_detail}")
    print(f"  模型: {model_name}")
    print(f"  调用模式: {mode.upper()}")
    
    # 构建提示词 - 使用 Gemini 官方推荐的格式
    prompt = compose_edit_prompt(
        edit_type=edit_type,
        edit_instruction=edit_detail,
        character_description=character_description,
        additional_context=f"Style: {style}"
    )
    
    if export_prompt:
        print("\n[导出模式] 提示词已复制到剪贴板:")
        print("="*70)
        print(prompt)
        print("="*70)
        return None
    
    # 根据模式选择调用方式
    if mode == "proxy":
        return _edit_via_proxy(
            source_image_path=source_image_path,
            prompt=prompt,
            edit_type=edit_type,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            proxy_base_url=proxy_base_url
        )
    else:
        return _edit_via_direct(
            source_image_path=source_image_path,
            prompt=prompt,
            edit_type=edit_type,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir
        )


def _edit_via_proxy(
    source_image_path: str,
    prompt: str,
    edit_type: str,
    api_key: str,
    model_name: str,
    output_dir: str,
    proxy_base_url: str = None
) -> Optional[str]:
    """通过 AiProxy 代理进行图像编辑"""
    import requests
    import base64
    from pathlib import Path
    
    proxy_base_url = proxy_base_url or os.environ.get("AIPROXY_BASE_URL", "https://bot.bigjj.click/aiproxy")
    
    # 加载源图像
    with open(source_image_path, 'rb') as f:
        image_bytes = f.read()
    
    # 判断 MIME 类型
    suffix = Path(source_image_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }
    mime_type = mime_map.get(suffix, "image/jpeg")
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    # 调用 AiProxy
    endpoint = f"{proxy_base_url.rstrip('/')}/generate"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "model": model_name,
        "image": f"data:{mime_type};base64,{b64_image}",
        "safetySettings": [
            { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH" },
            { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH" },
            { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH" },
            { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH" }
        ]
    }
    
    try:
        print(f"\n[AiProxy] 调用图像编辑: {endpoint}")
        print(f"[AiProxy] 模型: {model_name}")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"[ERROR] AiProxy 调用失败: {response.status_code}")
            print(f"        {response.text[:200]}")
            return None
        
        result = response.json()
        
        # 提取图像数据 (从 reply 中提取)
        reply = result.get("reply", "")
        
        # 使用 aiproxy_client 中的提取函数
        from aiproxy_client import extract_image_from_reply
        image_data = extract_image_from_reply(reply)
        
        if not image_data:
            print("[ERROR] AiProxy 响应中未找到图像数据")
            return None
        
        image_bytes, _ = image_data
        
        # 保存编辑后的图像
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"{edit_type}_edited_{timestamp}.png"
        
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        
        print(f"✅ 编辑完成: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"[ERROR] 代理编辑失败: {e}")
        return None


def _edit_via_direct(
    source_image_path: str,
    prompt: str,
    edit_type: str,
    api_key: str,
    model_name: str,
    output_dir: str
) -> Optional[str]:
    """直连 Gemini API 进行图像编辑"""
    from pathlib import Path
    from image_editor_utils import load_image_as_base64
    
    _ensure_imports()
    
    # 配置 API
    if api_key:
        genai.configure(api_key=api_key)
    
    # 加载源图像
    image_b64 = load_image_as_base64(source_image_path)
    if image_b64 is None:
        print(f"[ERROR] 无法加载源图像: {source_image_path}")
        return None
    
    # 获取正确的 MIME 类型
    ext = source_image_path.lower()
    if ext.endswith('.png'):
        mime_type = "image/png"
    elif ext.endswith('.webp'):
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"
    
    try:
        # 调用 Gemini API - 使用新的 google.genai 客户端
        # 注意: gemini-2.5-flash-image 需要使用新 SDK
        try:
            from google import genai as new_genai
            from google.genai import types
            from PIL import Image
            
            client = new_genai.Client(api_key=api_key)
            image_input = Image.open(source_image_path)
            
            print(f"\n[Gemini] 调用图像编辑 API...")
            print(f"[Gemini] 模型: {model_name}")
            
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, image_input],
            )
            
            # 提取生成的图像
            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    # 保存编辑后的图像
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = Path(output_dir) / f"{edit_type}_edited_{timestamp}.png"
                    
                    image = part.as_image()
                    image.save(str(output_path))
                    
                    print(f"✅ 编辑完成: {output_path}")
                    return str(output_path)
                elif hasattr(part, 'text') and part.text:
                    print(f"[Gemini 响应] {part.text[:200]}...")
            
            print("[ERROR] API 未返回图像数据")
            return None
            
        except ImportError:
            # 回退到旧的 google.generativeai
            print("[INFO] 使用旧版 google.generativeai SDK")
            
            model = genai.GenerativeModel(model_name)
            
            contents = [
                prompt,
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_b64
                    }
                }
            ]
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=4096,
                temperature=0.7,
            )
            
            print(f"\n[Gemini] 调用图像编辑 API...")
            response = model.generate_content(
                contents,
                generation_config=generation_config,
                safety_settings=[]
            )
            
            if not response or not response.candidates:
                print("[ERROR] 编辑失败: 无返回内容")
                return None
            
            # 提取生成的图像
            image_data = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    if part.inline_data.mime_type.startswith('image/'):
                        image_data = part.inline_data.data
                        break
            
            if not image_data:
                print("[ERROR] API 未返回图像数据")
                return None
            
            # 保存编辑后的图像
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(output_dir) / f"{edit_type}_edited_{timestamp}.png"
            
            if isinstance(image_data, str):
                import base64
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ 编辑完成: {output_path}")
            return str(output_path)
        
    except Exception as e:
        print(f"[ERROR] 编辑失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def refine_character_details(
    source_image_path: str,
    detail_part: str,  # "face", "hands", "pose", "custom"
    issue_description: str,
    character_description: str,
    api_key: str,
    model_name: str = None,  # 默认使用 gemini-2.5-flash-image
    output_dir: str = "test_images",
    auto_cut: bool = True,
    export_prompt: bool = False,
    mode: str = "proxy",  # 新增: 支持 proxy/direct
    proxy_base_url: str = None
) -> Optional[str]:
    """
    优化角色的特定细节部位(语义遮盖)
    
    Args:
        source_image_path: 源图像路径
        detail_part: 要优化的部位 (face/hands/pose/custom)
        issue_description: 问题描述
        character_description: 角色描述
        api_key: API Key (代理模式为 proxy token，直连模式为 Gemini API Key)
        model_name: 模型名称 (默认: gemini-2.5-flash-image)
        output_dir: 输出目录
        auto_cut: 是否自动切割
        export_prompt: 是否导出提示词
        mode: API 调用模式 ("proxy" 或 "direct")
        proxy_base_url: 代理服务地址 (仅 proxy 模式)
    
    Returns:
        优化后图像的路径
    """
    from pathlib import Path
    from image_editor_utils import compose_refine_prompt, load_image_as_base64
    
    _ensure_imports()
    
    # 使用正确的图像编辑模型
    if not model_name:
        model_name = "gemini-2.5-flash-image"
    
    # 构建部位标签
    part_labels = {
        'face': '脸部表情和特征',
        'hands': '手指和手部细节',
        'pose': '身体姿势',
        'eyes': '眼睛和视线',
        'custom': issue_description
    }
    
    part_label = part_labels.get(detail_part, detail_part)
    
    print(f"\n[细节优化] {detail_part.upper()}")
    print(f"  原图: {Path(source_image_path).name}")
    print(f"  问题: {issue_description}")
    print(f"  模型: {model_name}")
    print(f"  调用模式: {mode.upper()}")
    
    # 构建提示词
    prompt = compose_refine_prompt(
        detail_part=part_label,
        issue_description=issue_description,
        character_description=character_description,
        preservation_notes="保持所有其他元素完全相同"
    )
    
    if export_prompt:
        print("\n[导出模式] 提示词已复制到剪贴板:")
        print("="*70)
        print(prompt)
        print("="*70)
        return None
    
    # 根据模式选择调用方式 (复用 edit 函数的代理/直连逻辑)
    if mode == "proxy":
        return _edit_via_proxy(
            source_image_path=source_image_path,
            prompt=prompt,
            edit_type=f"refined_{detail_part}",
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            proxy_base_url=proxy_base_url
        )
    else:
        return _edit_via_direct(
            source_image_path=source_image_path,
            prompt=prompt,
            edit_type=f"refined_{detail_part}",
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir
        )


# =============================================================================
# P1 功能: 风格转换 (Style Transfer)
# =============================================================================

def style_transfer_character(
    source_image_path: str,
    style_preset: str,
    character_description: str,
    api_key: str,
    model_name: str = None,  # 默认使用 gemini-2.5-flash-image
    output_dir: str = "test_images",
    custom_style: Optional[str] = None,
    preserve_details: bool = True,
    mode: str = "proxy",  # 新增: 支持 proxy/direct
    proxy_base_url: str = None
) -> Optional[str]:
    """
    应用风格转换到角色图像
    
    Args:
        source_image_path: 源图像路径
        style_preset: 风格预设 (anime/cinematic/oil-painting/watercolor/comic/3d)
        character_description: 角色描述
        api_key: API Key (代理模式为 proxy token，直连模式为 Gemini API Key)
        model_name: 模型名称 (默认: gemini-2.5-flash-image)
        output_dir: 输出目录
        custom_style: 自定义风格描述 (覆盖预设)
        preserve_details: 是否保留原始细节
        mode: API 调用模式 ("proxy" 或 "direct")
        proxy_base_url: 代理服务地址 (仅 proxy 模式)
    
    Returns:
        风格转换后图像的路径
    """
    from pathlib import Path
    from image_editor_utils import compose_style_transfer_prompt, load_image_as_base64
    
    _ensure_imports()
    
    # 使用正确的图像编辑模型
    if not model_name:
        model_name = "gemini-2.5-flash-image"
    
    # 风格预设映射
    style_presets = {
        "anime": "Japanese anime style with exaggerated features, bright colors, and expressive eyes",
        "cinematic": "Cinematic photorealistic style with professional lighting and composition",
        "oil-painting": "Classical oil painting style with visible brushstrokes and rich colors",
        "watercolor": "Watercolor painting style with soft edges and flowing pigments",
        "comic": "Comic book style with bold outlines and limited color palette",
        "3d": "3D rendered/CGI style with modern digital aesthetics"
    }
    
    # 确定风格描述
    style_description = custom_style if custom_style else style_presets.get(style_preset, style_preset)
    
    print(f"\n[风格转换模式]")
    print(f"  源图: {Path(source_image_path).name}")
    print(f"  风格: {style_preset}" + (f" (自定义)" if custom_style else ""))
    print(f"  模型: {model_name}")
    print(f"  调用模式: {mode.upper()}")
    
    # 构建提示词
    prompt = compose_style_transfer_prompt(
        target_style=style_description,
        character_description=character_description
    )
    
    # 保留细节的额外指令
    if preserve_details:
        prompt += "\n\nImportant: Preserve all anatomical details, proportions, and character identity while applying the style."
    
    # 根据模式选择调用方式 (复用 edit 函数的代理/直连逻辑)
    if mode == "proxy":
        return _edit_via_proxy(
            source_image_path=source_image_path,
            prompt=prompt,
            edit_type=f"styled_{style_preset}",
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            proxy_base_url=proxy_base_url
        )
    else:
        return _edit_via_direct(
            source_image_path=source_image_path,
            prompt=prompt,
            edit_type=f"styled_{style_preset}",
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir
        )


# =============================================================================
# P0 功能: 高保真细节保留编辑 (Preserve Detail Edit)
# =============================================================================

def preserve_detail_edit(
    main_image_path: str,
    instruction: str,
    preserve_details: str = None,
    element_image_path: str = None,
    api_key: str = None,
    model_name: str = None,
    output_dir: str = "test_images",
    output_name: str = None,
    mode: str = "proxy",
    proxy_base_url: str = None
) -> Optional[str]:
    """
    高保真细节保留编辑
    
    在修改图像时保留关键细节（如面部特征、徽标位置等）。
    适用于需要精确控制哪些元素保持不变的场景。
    
    Args:
        main_image_path: 主图片路径（包含要保留细节的图片）
        instruction: 修改指令
        preserve_details: 要保留的关键细节描述（如 "保持女性的面部特征完全不变"）
        element_image_path: 可选的元素图片路径（如 logo、配饰等要添加的元素）
        api_key: API Key
        model_name: 模型名称 (默认: gemini-2.5-flash-image)
        output_dir: 输出目录
        output_name: 输出文件名 (可选)
        mode: API 调用模式 ("proxy" 或 "direct")
        proxy_base_url: 代理服务地址 (仅 proxy 模式)
    
    Returns:
        编辑后图像的路径
    
    示例:
        # 给人物 T 恤添加 logo，保持面部不变
        preserve_detail_edit(
            main_image_path="woman.png",
            instruction="将 logo 添加到她的黑色 T 恤上，让 logo 看起来像自然印在面料上",
            preserve_details="确保女性的面部和特征保持完全不变",
            element_image_path="logo.png"
        )
        
        # 改变背景但保持人物细节
        preserve_detail_edit(
            main_image_path="portrait.png",
            instruction="将背景改为海滩日落场景",
            preserve_details="保持人物的面部、发型、服装的所有细节完全不变"
        )
    """
    from pathlib import Path
    
    _ensure_imports()
    
    if not model_name:
        model_name = "gemini-2.5-flash-image"
    
    print(f"\n[高保真细节保留编辑]")
    print(f"  主图片: {Path(main_image_path).name}")
    if element_image_path:
        print(f"  元素图片: {Path(element_image_path).name}")
    print(f"  修改指令: {instruction[:80]}{'...' if len(instruction) > 80 else ''}")
    if preserve_details:
        print(f"  保留细节: {preserve_details[:80]}{'...' if len(preserve_details) > 80 else ''}")
    print(f"  模型: {model_name}")
    print(f"  调用模式: {mode.upper()}")
    
    # 构建完整的提示词，强调细节保留
    full_prompt_parts = []
    
    # 添加修改指令
    full_prompt_parts.append(instruction)
    
    # 添加细节保留要求
    if preserve_details:
        full_prompt_parts.append(f"\n\nCRITICAL REQUIREMENT: {preserve_details}")
    else:
        # 默认的细节保留提示
        full_prompt_parts.append("\n\nIMPORTANT: Preserve all fine details of the original subject, including facial features, expressions, and any identifying characteristics.")
    
    # 添加自然融合提示
    if element_image_path:
        full_prompt_parts.append("\n\nThe added element should blend naturally with the original image, matching the lighting, perspective, and style of the original.")
    
    full_prompt = "".join(full_prompt_parts)
    
    # 根据模式选择调用方式
    if mode == "proxy":
        return _preserve_edit_via_proxy(
            main_image_path=main_image_path,
            element_image_path=element_image_path,
            prompt=full_prompt,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            output_name=output_name,
            proxy_base_url=proxy_base_url
        )
    else:
        return _preserve_edit_via_direct(
            main_image_path=main_image_path,
            element_image_path=element_image_path,
            prompt=full_prompt,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            output_name=output_name
        )


def _preserve_edit_via_proxy(
    main_image_path: str,
    element_image_path: str,
    prompt: str,
    api_key: str,
    model_name: str,
    output_dir: str,
    output_name: str = None,
    proxy_base_url: str = None
) -> Optional[str]:
    """通过 AiProxy 代理进行高保真编辑"""
    import requests
    import base64
    from pathlib import Path
    
    proxy_base_url = proxy_base_url or os.environ.get("AIPROXY_BASE_URL", "https://bot.bigjj.click/aiproxy")
    
    # 准备图片数据
    images_data = []
    
    # 主图片
    with open(main_image_path, 'rb') as f:
        main_bytes = f.read()
    suffix = Path(main_image_path).suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    main_mime = mime_map.get(suffix, "image/jpeg")
    main_b64 = base64.b64encode(main_bytes).decode("utf-8")
    images_data.append(f"data:{main_mime};base64,{main_b64}")
    
    # 元素图片 (可选)
    if element_image_path:
        with open(element_image_path, 'rb') as f:
            elem_bytes = f.read()
        suffix = Path(element_image_path).suffix.lower()
        elem_mime = mime_map.get(suffix, "image/jpeg")
        elem_b64 = base64.b64encode(elem_bytes).decode("utf-8")
        images_data.append(f"data:{elem_mime};base64,{elem_b64}")
    
    # 调用 AiProxy
    endpoint = f"{proxy_base_url.rstrip('/')}/generate"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 根据图片数量选择 payload 格式
    if len(images_data) == 1:
        payload = {
            "prompt": prompt,
            "model": model_name,
            "image": images_data[0],
            "safetySettings": [
                { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH" },
                { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH" },
                { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH" },
                { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH" }
            ]
        }
    else:
        payload = {
            "prompt": prompt,
            "model": model_name,
            "images": images_data,
            "safetySettings": [
                { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH" },
                { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH" },
                { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH" },
                { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH" }
            ]
        }
    
    try:
        print(f"\n[AiProxy] 调用高保真编辑: {endpoint}")
        print(f"[AiProxy] 模型: {model_name}")
        print(f"[AiProxy] 图片数量: {len(images_data)}")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"[ERROR] AiProxy 调用失败: {response.status_code}")
            print(f"        {response.text[:200]}")
            return None
        
        result = response.json()
        
        # 提取图像数据
        reply = result.get("reply", "")
        from aiproxy_client import extract_image_from_reply
        image_data = extract_image_from_reply(reply)
        
        if not image_data:
            print("[ERROR] AiProxy 响应中未找到图像数据")
            return None
        
        image_bytes, _ = image_data
        
        # 保存编辑后的图像
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        if output_name:
            filename = output_name if output_name.endswith('.png') else f"{output_name}.png"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"preserve_edit_{timestamp}.png"
        
        output_path = Path(output_dir) / filename
        
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        
        print(f"✅ 高保真编辑完成: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"[ERROR] 代理高保真编辑失败: {e}")
        return None


def _preserve_edit_via_direct(
    main_image_path: str,
    element_image_path: str,
    prompt: str,
    api_key: str,
    model_name: str,
    output_dir: str,
    output_name: str = None
) -> Optional[str]:
    """直连 Gemini API 进行高保真编辑"""
    from pathlib import Path
    from PIL import Image
    
    try:
        # 使用新的 google.genai SDK
        from google import genai as new_genai
        
        client = new_genai.Client(api_key=api_key)
        
        # 加载图片
        main_img = Image.open(main_image_path)
        
        # 构建内容
        if element_image_path:
            elem_img = Image.open(element_image_path)
            contents = [main_img, elem_img, prompt]
        else:
            contents = [main_img, prompt]
        
        print(f"\n[Gemini] 调用高保真编辑 API...")
        print(f"[Gemini] 模型: {model_name}")
        
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
        )
        
        # 提取生成的图像
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                # 保存编辑后的图像
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                
                if output_name:
                    filename = output_name if output_name.endswith('.png') else f"{output_name}.png"
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"preserve_edit_{timestamp}.png"
                
                output_path = Path(output_dir) / filename
                
                image = part.as_image()
                image.save(str(output_path))
                
                print(f"✅ 编辑完成: {output_path}")
                return str(output_path)
            elif hasattr(part, 'text') and part.text:
                print(f"[Gemini 响应] {part.text[:200]}...")
        
        print("[ERROR] API 未返回图像数据")
        return None
        
    except ImportError:
        # 回退到旧的 google.generativeai
        print("[INFO] 使用旧版 google.generativeai SDK")
        
        _ensure_imports()
        
        if api_key:
            genai.configure(api_key=api_key)
        
        import base64
        
        contents = []
        
        # 主图片
        with open(main_image_path, 'rb') as f:
            main_bytes = f.read()
        suffix = Path(main_image_path).suffix.lower()
        main_mime = "image/png" if suffix == ".png" else "image/jpeg"
        main_b64 = base64.b64encode(main_bytes).decode("utf-8")
        contents.append({
            "inline_data": {"mime_type": main_mime, "data": main_b64}
        })
        
        # 元素图片 (可选)
        if element_image_path:
            with open(element_image_path, 'rb') as f:
                elem_bytes = f.read()
            suffix = Path(element_image_path).suffix.lower()
            elem_mime = "image/png" if suffix == ".png" else "image/jpeg"
            elem_b64 = base64.b64encode(elem_bytes).decode("utf-8")
            contents.append({
                "inline_data": {"mime_type": elem_mime, "data": elem_b64}
            })
        
        contents.append(prompt)
        
        try:
            model = genai.GenerativeModel(model_name)
            
            print(f"\n[Gemini] 调用高保真编辑 API...")
            response = model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4096,
                    temperature=0.7,
                ),
                safety_settings=[]
            )
            
            if not response or not response.candidates:
                print("[ERROR] 编辑失败: 无返回内容")
                return None
            
            # 提取生成的图像
            image_data = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    if part.inline_data.mime_type.startswith('image/'):
                        image_data = part.inline_data.data
                        break
            
            if not image_data:
                print("[ERROR] API 未返回图像数据")
                return None
            
            # 保存编辑后的图像
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(output_dir) / f"{edit_type}_edited_{timestamp}.png"
            
            if isinstance(image_data, str):
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ 编辑完成: {output_path}")
            return str(output_path)
        
        except Exception as e:
            print(f"[ERROR] 编辑失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    except Exception as e:
        print(f"[ERROR] 编辑失败: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# 智能衣服提取 (Smart Clothing Extraction)
# =============================================================================

def smart_extract_clothing(
    image_path: str,
    api_key: str,
    model_name: str = "gemini-2.5-flash-image",
    output_dir: str = "test_images",
    mode: str = "proxy",
    proxy_base_url: str = None,
) -> Optional[str]:
    """
    智能分析图片并提取衣服
    
    工作流程：
    1. AI分析图片：判断是纯衣服、有背景的衣服，还是穿着衣服的人
    2. 去除背景（如果有）
    3. 提取衣服（如果是穿着衣服的人）
    4. 返回处理后的图片路径
    
    Args:
        image_path: 衣服图片路径
        api_key: API密钥
        model_name: 使用的模型
        output_dir: 输出目录
        mode: 调用模式 (proxy/direct)
        proxy_base_url: 代理地址
    
    Returns:
        处理后的图片路径，失败返回None
    """
    from pathlib import Path
    import requests
    import base64
    
    _ensure_imports()
    
    print(f"  🔍 步骤1: AI分析图片内容...")
    
    # =========================================================================
    # 步骤1: 用AI分析图片内容
    # =========================================================================
    analysis_prompt = """Analyze this image and determine its content type:

1. **Pure clothing item**: Only clothing/garment visible, no person wearing it (may have background)
2. **Person wearing clothing**: A person is wearing the clothing
3. **Ambiguous**: Cannot clearly determine

Also check if there is a background:
- Has background: Yes/No
- Background type: (white/solid color/complex scene/transparent)

Please respond in this exact format:
Content: [Pure clothing item / Person wearing clothing / Ambiguous]
Has background: [Yes / No]
Background type: [description]
Clothing description: [brief description of the clothing]"""

    try:
        # 根据模式调用AI分析
        if mode == "proxy":
            analysis_result = _analyze_image_via_proxy(
                image_path=image_path,
                prompt=analysis_prompt,
                api_key=api_key,
                model_name=model_name,
                proxy_base_url=proxy_base_url
            )
        else:
            analysis_result = _analyze_image_via_direct(
                image_path=image_path,
                prompt=analysis_prompt,
                api_key=api_key,
                model_name=model_name
            )
        
        if not analysis_result:
            print(f"     ⚠️ AI分析失败，跳过智能处理")
            return None
        
        print(f"     📋 分析结果:\n{analysis_result}")
        
        # 解析分析结果
        content_type = "unknown"
        has_background = False
        
        result_lower = analysis_result.lower()
        if "pure clothing" in result_lower or "only clothing" in result_lower:
            content_type = "pure_clothing"
        elif "person wearing" in result_lower or "wearing clothing" in result_lower:
            content_type = "person_wearing"
        
        if "has background: yes" in result_lower:
            has_background = True
        
        print(f"     ✅ 检测结果: 内容={content_type}, 背景={has_background}")
        
    except Exception as e:
        print(f"     ⚠️ AI分析出错: {e}")
        print(f"     使用默认处理流程")
        content_type = "unknown"
        has_background = True
    
    # =========================================================================
    # 步骤2: 根据分析结果进行处理
    # =========================================================================
    output_path_obj = Path(output_dir)
    output_path_obj.mkdir(parents=True, exist_ok=True)
    
    img_name = Path(image_path).stem
    
    # 情况1: 纯衣服，无背景 → 直接使用
    if content_type == "pure_clothing" and not has_background:
        print(f"  ✅ 检测到纯衣服且无背景，直接使用")
        return image_path
    
    # 情况2: 纯衣服，有背景 → 仅去除背景
    if content_type == "pure_clothing" and has_background:
        print(f"  🔪 步骤2: 去除背景...")
        try:
            from image_processor import remove_background
            import cv2
            
            img = cv2.imread(image_path)
            if img is None:
                print(f"     ⚠️ 无法读取图片")
                return None
            
            processed = remove_background(img, model_name="birefnet-general")
            processed_path = output_path_obj / f"_extracted_nobg_{img_name}.png"
            cv2.imwrite(str(processed_path), processed)
            
            print(f"     ✅ 背景已去除: {processed_path.name}")
            return str(processed_path)
            
        except Exception as e:
            print(f"     ⚠️ 去除背景失败: {e}")
            return image_path
    
    # 情况3: 穿着衣服的人 → 去背景 + AI提取衣服
    if content_type == "person_wearing":
        print(f"  👤 检测到穿着衣服的人")
        
        # 步骤2a: 先去除背景
        intermediate_path = image_path
        if has_background:
            print(f"  🔪 步骤2a: 去除背景...")
            try:
                from image_processor import remove_background
                import cv2
                
                img = cv2.imread(image_path)
                if img is not None:
                    processed = remove_background(img, model_name="birefnet-general")
                    intermediate_path = output_path_obj / f"_temp_nobg_{img_name}.png"
                    cv2.imwrite(str(intermediate_path), processed)
                    print(f"     ✅ 背景已去除")
                else:
                    print(f"     ⚠️ 无法读取图片，使用原图")
            except Exception as e:
                print(f"     ⚠️ 去除背景失败: {e}，使用原图")
        
        # 步骤2b: AI提取衣服
        print(f"  🎨 步骤2b: AI提取衣服...")
        
        extraction_prompt = """Extract ONLY the clothing/garment from this image of a person wearing it.

Requirements:
- Remove the person completely
- Keep only the clothing item itself
- Maintain the clothing's original shape, color, and details
- Show the clothing as if it's displayed on its own (like in a product photo)
- Keep transparent background

Generate an image showing only the extracted clothing item."""

        try:
            # 调用AI生成提取后的衣服图片
            if mode == "proxy":
                extracted_path = _extract_clothing_via_proxy(
                    image_path=str(intermediate_path),
                    prompt=extraction_prompt,
                    api_key=api_key,
                    model_name=model_name,
                    output_dir=str(output_path_obj),
                    output_name=f"_extracted_clothing_{img_name}.png",
                    proxy_base_url=proxy_base_url
                )
            else:
                extracted_path = _extract_clothing_via_direct(
                    image_path=str(intermediate_path),
                    prompt=extraction_prompt,
                    api_key=api_key,
                    model_name=model_name,
                    output_dir=str(output_path_obj),
                    output_name=f"_extracted_clothing_{img_name}.png"
                )
            
            if extracted_path:
                print(f"     ✅ 衣服提取完成: {Path(extracted_path).name}")
                return extracted_path
            else:
                print(f"     ⚠️ 衣服提取失败，使用去背景后的图片")
                return str(intermediate_path)
                
        except Exception as e:
            print(f"     ⚠️ AI提取出错: {e}")
            return str(intermediate_path)
    
    # 默认: 仅去除背景
    print(f"  🔪 步骤2: 默认处理 - 去除背景...")
    try:
        from image_processor import remove_background
        import cv2
        
        img = cv2.imread(image_path)
        if img is not None:
            processed = remove_background(img, model_name="birefnet-general")
            processed_path = output_path_obj / f"_extracted_default_{img_name}.png"
            cv2.imwrite(str(processed_path), processed)
            print(f"     ✅ 处理完成: {processed_path.name}")
            return str(processed_path)
    except Exception as e:
        print(f"     ⚠️ 处理失败: {e}")
    
    return image_path


def _analyze_image_via_proxy(image_path, prompt, api_key, model_name, proxy_base_url=None):
    """通过代理分析图片"""
    import requests
    import base64
    
    proxy_base_url = proxy_base_url or os.environ.get("AIPROXY_BASE_URL", "https://bot.bigjj.click/aiproxy")
    
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        suffix = Path(image_path).suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(suffix, "image/jpeg")
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        # AiProxy 使用 /generate 端点，而不是 /chat/completions
        endpoint = f"{proxy_base_url.rstrip('/')}/generate"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # AiProxy 格式：使用 prompt + image
        payload = {
            "prompt": prompt,
            "model": model_name,
            "image": f"data:{mime_type};base64,{b64_image}",
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            # AiProxy 返回格式：{"reply": "文本内容"}
            if "reply" in result:
                return result["reply"].strip()
            else:
                print(f"     [DEBUG] 响应格式异常，缺少reply字段: {list(result.keys())}")
                return None
        else:
            print(f"     [DEBUG] API调用失败: {response.status_code}")
            print(f"     [DEBUG] 响应: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"     [DEBUG] 分析请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def _analyze_image_via_direct(image_path, prompt, api_key, model_name):
    """直接调用Gemini分析图片"""
    try:
        _ensure_imports()
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        image = PIL_Image.open(image_path)
        response = model.generate_content([prompt, image])
        
        return response.text if response else None
        
    except Exception as e:
        print(f"     [DEBUG] 直连分析异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def _extract_clothing_via_proxy(image_path, prompt, api_key, model_name, output_dir, output_name, proxy_base_url=None):
    """通过代理提取衣服（图像生成）"""
    import requests
    import base64
    from pathlib import Path
    
    try:
        proxy_base_url = proxy_base_url or os.environ.get("AIPROXY_BASE_URL", "https://bot.bigjj.click/aiproxy")
        
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        suffix = Path(image_path).suffix.lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(suffix, "image/jpeg")
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        endpoint = f"{proxy_base_url.rstrip('/')}/generate"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        payload = {
            "prompt": prompt,
            "model": model_name,
            "image": f"data:{mime_type};base64,{b64_image}",
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            if "image" in result:
                # 保存图片
                output_path = Path(output_dir) / output_name
                
                image_data = result["image"]
                if image_data.startswith("data:"):
                    image_data = image_data.split(",", 1)[1]
                
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(image_data))
                
                return str(output_path)
            else:
                print(f"     [DEBUG] 响应中无image字段: {result.keys()}")
                return None
        else:
            print(f"     [DEBUG] 提取API调用失败: {response.status_code}")
            print(f"     [DEBUG] 响应: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"     [DEBUG] 提取请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def _extract_clothing_via_direct(image_path, prompt, api_key, model_name, output_dir, output_name):
    """直接调用Gemini提取衣服"""
    try:
        _ensure_imports()
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        image = PIL_Image.open(image_path)
        response = model.generate_content([prompt, image])
        
        # Gemini可能返回生成的图片或描述
        # 这里需要根据实际API响应调整
        if response and hasattr(response, 'candidates'):
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data'):
                    output_path = Path(output_dir) / output_name
                    with open(output_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    return str(output_path)
        
        return None
        
    except Exception as e:
        print(f"     [DEBUG] 直连提取异常: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# P0 功能: 高级合成 (Multi-Image Composite)
# =============================================================================

def composite_images(
    image_paths: list,
    instruction: str,
    api_key: str,
    model_name: str = None,
    output_dir: str = "test_images",
    output_name: str = None,
    mode: str = "proxy",
    proxy_base_url: str = None,
    composite_type: str = "auto",
    composite_prompt_template: str = None,
    export_prompt: bool = False,
    instruction_is_final: bool = False,
) -> Optional[str]:
    """
    组合多张图片创建新场景
    
    用于换衣服、换配饰、创意拼贴、产品模型等高级合成场景。
    模型会保持原始图片的风格、光照和透视效果。
    
    Args:
        image_paths: 要合成的图片路径列表 (至少2张)
        instruction: 合成指令，描述如何组合这些图片
        api_key: API Key (代理模式为 proxy token，直连模式为 Gemini API Key)
        model_name: 模型名称 (默认: gemini-2.5-flash-image)
        output_dir: 输出目录
        output_name: 输出文件名 (可选，默认自动生成)
        mode: API 调用模式 ("proxy" 或 "direct")
        proxy_base_url: 代理服务地址 (仅 proxy 模式)
        composite_type: 合成类型 ("clothing", "accessory", "general", "auto")
        composite_prompt_template: 自定义合成提示词模板 (可选)
        instruction_is_final: 如果为 True，instruction 已是完整提示词，不再处理
    
    Returns:
        合成后图像的路径
    
    示例:
        # 换衣服
        composite_images(
            image_paths=["model.png", "dress.png"],
            instruction="让模特穿上这件裙子，保持自然的光影效果"
        )
        
        # 换配饰
        composite_images(
            image_paths=["person.png", "hat.png", "bag.png"],
            instruction="给人物戴上帽子并拿上包包"
        )
    """
    from pathlib import Path
    
    _ensure_imports()
    
    if not model_name:
        model_name = "gemini-2.5-flash-image"
    
    # 单图模式检查 (只有clothing_text类型支持单图)
    if len(image_paths) < 2:
        if composite_type != "clothing_text":
            print("[ERROR] 合成需要至少2张图片 (除非使用 clothing_text 模式)")
            return None
        # 单图模式 - 允许继续
    
    # 确定最终提示词
    if instruction_is_final:
        # instruction 已经是完整的提示词，直接使用
        enhanced_instruction = instruction
    elif composite_prompt_template:
        # 使用自定义模板
        image_list = "\n".join([f"Image {i+1}: {Path(p).name}" for i, p in enumerate(image_paths)])
        enhanced_instruction = composite_prompt_template.format(
            instruction=instruction,
            num_images=len(image_paths),
            image_list=image_list
        )
    else:
        # 使用 config.py 中的严格模板系统（与多视角生成同级别精度）
        from config import build_composite_prompt
        enhanced_instruction = build_composite_prompt(
            instruction=instruction,
            composite_type=composite_type,
            num_images=len(image_paths)
        )
    
    print(f"\n[高级合成]")
    print(f"  输入图片: {len(image_paths)} 张")
    for i, p in enumerate(image_paths, 1):
        print(f"    [{i}] {Path(p).name}")
    print(f"  用户指令: {instruction[:80]}{'...' if len(instruction) > 80 else ''}")
    print(f"  合成类型: {composite_type}")
    print(f"  模型: {model_name}")
    print(f"  调用模式: {mode.upper()}")
    
    # 打印最终提示词
    if export_prompt:
        print(f"\n{'='*60}")
        print("[最终合成提示词]")
        print(f"{'='*60}")
        print(enhanced_instruction)
        print(f"{'='*60}\n")
    
    # 根据模式选择调用方式
    if mode == "proxy":
        return _composite_via_proxy(
            image_paths=image_paths,
            instruction=enhanced_instruction,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            output_name=output_name,
            proxy_base_url=proxy_base_url
        )
    else:
        return _composite_via_direct(
            image_paths=image_paths,
            instruction=enhanced_instruction,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            output_name=output_name
        )


def _composite_via_proxy(
    image_paths: list,
    instruction: str,
    api_key: str,
    model_name: str,
    output_dir: str,
    output_name: str = None,
    proxy_base_url: str = None
) -> Optional[str]:
    """通过 AiProxy 代理进行多图合成"""
    import requests
    import base64
    from pathlib import Path
    
    proxy_base_url = proxy_base_url or os.environ.get("AIPROXY_BASE_URL", "https://bot.bigjj.click/aiproxy")
    
    # 准备多张图片的 base64 数据
    images_data = []
    for img_path in image_paths:
        with open(img_path, 'rb') as f:
            image_bytes = f.read()
        
        suffix = Path(img_path).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp"
        }
        mime_type = mime_map.get(suffix, "image/jpeg")
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        images_data.append({
            "mime_type": mime_type,
            "data": f"data:{mime_type};base64,{b64_image}"
        })
    
    # 调用 AiProxy - 多图合成
    endpoint = f"{proxy_base_url.rstrip('/')}/generate"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 构建 payload - 多图合成需要特殊格式
    # AiProxy 需要支持 images 数组或多个 image 字段
    payload = {
        "prompt": instruction,
        "model": model_name,
        "images": [img["data"] for img in images_data],  # 多图数组
        "safetySettings": [
            { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH" },
            { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH" },
            { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH" },
            { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH" }
        ]
    }
    
    try:
        print(f"\n[AiProxy] 调用多图合成: {endpoint}")
        print(f"[AiProxy] 模型: {model_name}")
        print(f"[AiProxy] 图片数量: {len(images_data)}")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=180
        )
        
        if response.status_code != 200:
            print(f"[ERROR] AiProxy 调用失败: {response.status_code}")
            print(f"        {response.text[:200]}")
            return None
        
        result = response.json()
        
        # 提取图像数据
        reply = result.get("reply", "")
        from aiproxy_client import extract_image_from_reply
        image_data = extract_image_from_reply(reply)
        
        if not image_data:
            print("[ERROR] AiProxy 响应中未找到图像数据")
            return None
        
        image_bytes, _ = image_data
        
        # 保存合成后的图像
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        if output_name:
            filename = output_name if output_name.endswith('.png') else f"{output_name}.png"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"composite_{timestamp}.png"
        
        output_path = Path(output_dir) / filename
        
        with open(output_path, 'wb') as f:
            f.write(image_bytes)
        
        print(f"✅ 合成完成: {output_path}")
        return str(output_path)
        
    except Exception as e:
        print(f"[ERROR] 代理合成失败: {e}")
        return None


def _composite_via_direct(
    image_paths: list,
    instruction: str,
    api_key: str,
    model_name: str,
    output_dir: str,
    output_name: str = None
) -> Optional[str]:
    """直连 Gemini API 进行多图合成"""
    from pathlib import Path
    from PIL import Image
    
    try:
        # 使用新的 google.genai SDK
        from google import genai as new_genai
        
        client = new_genai.Client(api_key=api_key)
        
        # 加载所有图片
        images = []
        for img_path in image_paths:
            img = Image.open(img_path)
            images.append(img)
        
        # 构建内容: [image1, image2, ..., instruction]
        contents = images + [instruction]
        
        print(f"\n[Gemini] 调用多图合成 API...")
        print(f"[Gemini] 模型: {model_name}")
        
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
        )
        
        # 提取生成的图像
        for part in response.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                # 保存合成后的图像
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                
                if output_name:
                    filename = output_name if output_name.endswith('.png') else f"{output_name}.png"
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"composite_{timestamp}.png"
                
                output_path = Path(output_dir) / filename
                
                image = part.as_image()
                image.save(str(output_path))
                
                print(f"✅ 合成完成: {output_path}")
                return str(output_path)
            elif hasattr(part, 'text') and part.text:
                print(f"[Gemini 响应] {part.text[:200]}...")
        
        print("[ERROR] API 未返回图像数据")
        return None
        
    except ImportError:
        # 回退到旧的 google.generativeai
        print("[INFO] 使用旧版 google.generativeai SDK")
        
        _ensure_imports()
        
        if api_key:
            genai.configure(api_key=api_key)
        
        # 加载图片并转为 base64
        import base64
        
        contents = []
        for img_path in image_paths:
            with open(img_path, 'rb') as f:
                image_bytes = f.read()
            
            suffix = Path(img_path).suffix.lower()
            mime_type = "image/png" if suffix == ".png" else "image/jpeg"
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            
            contents.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_image
                }
            })
        
        contents.append(instruction)
        
        try:
            model = genai.GenerativeModel(model_name)
            
            print(f"\n[Gemini] 调用多图合成 API...")
            response = model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4096,
                    temperature=0.7,
                ),
                safety_settings=[]
            )
            
            if not response or not response.candidates:
                print("[ERROR] 合成失败: 无返回内容")
                return None
            
            # 提取生成的图像
            image_data = None
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    if part.inline_data.mime_type.startswith('image/'):
                        image_data = part.inline_data.data
                        break
            
            if not image_data:
                print("[ERROR] API 未返回图像数据")
                return None
            
            # 保存合成后的图像
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            if output_name:
                filename = output_name if output_name.endswith('.png') else f"{output_name}.png"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"composite_{timestamp}.png"
            
            output_path = Path(output_dir) / filename
            
            if isinstance(image_data, str):
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            with open(output_path, 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ 合成完成: {output_path}")
            return str(output_path)
            
        except Exception as e:
            print(f"[ERROR] 合成失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    except Exception as e:
        print(f"[ERROR] 合成失败: {e}")
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
