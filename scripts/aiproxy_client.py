#!/usr/bin/env python3
"""
AiProxy 客户端
调用 bot.bigjj.click/aiproxy 服务生成图像

使用共享配置: 从 config.py 导入提示词模板和模型名称
"""

import os
import re
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# 导入共享配置
from config import (
    AIPROXY_BASE_URL,
    IMAGE_MODEL,
    build_multiview_prompt,
    build_image_reference_prompt,
    build_strict_copy_prompt
)

# Lazy imports
requests = None
PIL_Image = None


def _ensure_imports():
    """延迟导入依赖库"""
    global requests, PIL_Image
    
    if requests is None:
        try:
            import requests as _requests
            from PIL import Image as _Image
            requests = _requests
            PIL_Image = _Image
        except ImportError as e:
            raise ImportError(
                f"缺少必要依赖: {e}\n"
                "请运行: pip install requests pillow"
            )


# 使用共享配置中的默认模型
DEFAULT_MODEL = IMAGE_MODEL


# =============================================================================
# AiProxy API 调用
# =============================================================================

def generate_image_via_proxy(
    prompt: str,
    token: str,
    model: str = DEFAULT_MODEL,
    base_url: str = AIPROXY_BASE_URL,
    reference_image: str = None,
    resolution: str = "2K",  # 默认请求 2K 分辨率 (性价比最高)
    aspect_ratio: str = "2:3"  # 默认 2:3 适合全身人像四视图
) -> Optional[Tuple[bytes, str]]:
    """
    通过 AiProxy 服务生成图像
    
    Args:
        prompt: 图像生成提示词
        token: AiProxy 客户端认证令牌
        model: 模型名称 (默认: nano-banana-pro)
        base_url: AiProxy 服务地址
        reference_image: 参考图片的 base64 data URL (可选，用于图生图)
        resolution: 图像分辨率，可选 "4K", "2K", "1K" (默认: "2K")
        aspect_ratio: 宽高比，可选 "1:1", "2:3", "3:2", "16:9" 等 (默认: "2:3")
    
    Returns:
        (image_bytes, mime_type) 或 None
    """
    _ensure_imports()
    
    endpoint = f"{base_url.rstrip('/')}/generate"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "model": model,
        "image_size": resolution,
        "aspect_ratio": aspect_ratio
    }
    
    print(f"[AiProxy] 请求参数: image_size={resolution}, aspect_ratio={aspect_ratio}")
    
    # 如果提供了参考图片，添加到 payload（图生图模式）
    if reference_image:
        payload["image"] = reference_image
        print(f"[AiProxy] 使用图生图模式 (image-to-image)")
    
    MAX_RETRIES = 1
    
    # 定义回退模型 map
    FALLBACK_MODELS = {
        "models/nano-banana-pro-preview": "gemini-2.5-flash-image",
        "nano-banana-pro-preview": "gemini-2.5-flash-image",
        IMAGE_MODEL: "gemini-2.5-flash-image"
    }

    current_model = model
    
    for attempt in range(MAX_RETRIES + 1):
        payload["model"] = current_model
        print(f"[AiProxy] 调用 {endpoint}")
        print(f"[AiProxy] 模型: {current_model} (尝试 {attempt+1}/{MAX_RETRIES+1})")
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("reply", "")
                image_data = extract_image_from_reply(reply)
                
                if image_data:
                    return image_data
                else:
                    print("[WARNING] AiProxy 返回中未找到图像数据")
                    # 如果这只是看起来像成功的空响应，也许我们应该重试？
                    # 但通常 200 OK 意味着模型生成了文本但没生成图片
            
            elif response.status_code == 401:
                print("[ERROR] AiProxy 认证失败 - 请检查 token")
                return None
            
            else:
                print(f"[ERROR] AiProxy 返回错误: {response.status_code}")
                # 继续下面检查是否需要 fallback
        
        except requests.exceptions.Timeout:
            print("[ERROR] AiProxy 请求超时")
        except Exception as e:
            print(f"[ERROR] AiProxy 请求失败: {e}")

        # 如果失败了，检查是否可以回退模型
        if attempt < MAX_RETRIES:
            fallback_model = FALLBACK_MODELS.get(current_model)
            if not fallback_model and "banana" in current_model:
                 fallback_model = "gemini-2.5-flash-image"
            
            if fallback_model and fallback_model != current_model:
                print(f"⚠️ 模型 {current_model} 调用失败，自动切换到 fallback 模型: {fallback_model}")
                current_model = fallback_model
                continue # Retry loop
        
        # 如果到了这里还没 continue，说明是最后一次尝试或者无法回退，不再重试
        break

    return None


def extract_image_from_reply(reply: str) -> Optional[Tuple[bytes, str]]:
    """
    从 AiProxy 返回的 HTML 中提取 base64 图像数据
    
    AiProxy 返回格式:
    ```html-image-hidden
    ...
    <img ... src="data:image/png;base64,..." ...>
    ...
    ```
    
    Returns:
        (image_bytes, mime_type) 或 None
    """
    # 匹配 data:image/xxx;base64,xxxxxx 格式
    pattern = r'data:(image/[^;]+);base64,([A-Za-z0-9+/=]+)'
    
    match = re.search(pattern, reply)
    if match:
        mime_type = match.group(1)
        b64_data = match.group(2)
        
        try:
            image_bytes = base64.b64decode(b64_data)
            print(f"[AiProxy] 成功提取图像: {len(image_bytes)} bytes, {mime_type}")
            return (image_bytes, mime_type)
        except Exception as e:
            print(f"[ERROR] Base64 解码失败: {e}")
            return None
    
    return None


def analyze_image_for_character(
    image_path: str,
    token: str,
    user_guidance: str = None,
    base_url: str = AIPROXY_BASE_URL
) -> Optional[str]:
    """
    使用 AI 分析图片，提取角色的详细描述
    
    Args:
        image_path: 参考图片路径
        token: AiProxy 客户端令牌
        user_guidance: 用户指导词（可选），用于指定分析哪个人物或关注什么细节
        base_url: AiProxy 服务地址
    
    Returns:
        角色详细描述文本 或 None
    """
    _ensure_imports()
    
    print(f"[图片分析] 正在分析参考图片: {image_path}")
    if user_guidance:
        print(f"[用户指导] {user_guidance}")
    
    # 读取并编码图片
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"[ERROR] 图片不存在: {image_path}")
        return None
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # 判断 MIME 类型
    suffix = image_path.suffix.lower()
    if suffix in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif suffix == ".png":
        mime_type = "image/png"
    elif suffix == ".webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"  # 默认
    
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    # 构建分析提示词（根据用户指导动态调整）
    if user_guidance:
        subject_instruction = f"""
**USER GUIDANCE**: {user_guidance}
Please focus on the person/subject specified above. If there are multiple people in the image, 
only describe the one matching the user's description.
"""
    else:
        subject_instruction = """
If there are multiple people in the image, describe the most prominent/central one.
"""

    analysis_prompt = f"""Analyze this image and extract a detailed character description for 3D modeling.
{subject_instruction}

Please describe in detail:

1. **PHYSICAL APPEARANCE**
   - Gender, approximate age, ethnicity
   - Height/body type (slim, athletic, curvy, etc.)
   - Face shape, hairstyle, hair color and length
   - Any distinctive facial features

2. **CLOTHING & OUTFIT** (Be very specific!)
   - Top: exact type (T-shirt/blouse/jacket), style, color, fit (loose/tight/cropped), visible logos/text
   - Bottom: pants/skirt/shorts type, color, fit, length, material appearance
   - Footwear: type, color, heel height, style details
   - Layer details: what's worn over what

3. **ACCESSORIES** (Include everything visible)
   - Bags: type (crossbody/shoulder/handbag), color, size, how it's carried
   - Jewelry: earrings, necklaces, bracelets, rings - describe each
   - Headwear: hats, caps, with any text/logos/brand visible
   - Other: watches, belts, glasses, scarves, etc.

4. **POSE & BODY LANGUAGE**
   - Standing/walking/sitting/leaning
   - Weight distribution (which leg)
   - Arm positions (where are the hands?)
   - Head direction and tilt
   - Overall vibe/attitude

5. **KEY VISUAL DETAILS FOR 3D** (Important for accurate recreation)
   - Fabric textures and materials (cotton, silk, denim, leather)
   - How clothes drape and fold
   - Any patterns or prints
   - Color variations and gradients

Output a comprehensive description in a single detailed paragraph, in English. 
Be extremely specific about colors (not just "blue" but "navy blue" or "light sky blue"), 
materials, and spatial positions. This will be used to generate a 3D model."""

    # 调用 AiProxy 的 VLM 分析功能
    endpoint = f"{base_url.rstrip('/')}/generate"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 使用 Gemini 模型进行图片分析
    payload = {
        "prompt": analysis_prompt,
        "model": "gemini-2.0-flash",  # 使用文本/视觉模型
        "image": f"data:{mime_type};base64,{b64_image}"
    }
    
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"[ERROR] 图片分析失败: {response.status_code}")
            print(response.text[:300])
            return None
        
        data = response.json()
        description = data.get("reply", "").strip()
        
        if description:
            # 清理可能的 markdown 格式
            description = re.sub(r'^```.*\n?', '', description)
            description = re.sub(r'\n?```$', '', description)
            print(f"[图片分析] 提取描述成功 ({len(description)} 字符)")
            return description
        else:
            print("[WARNING] AI 未返回描述")
            return None
            
    except Exception as e:
        print(f"[ERROR] 图片分析请求失败: {e}")
        return None


# 保留旧代码的兼容性（这段代码看起来是重复的，应该删除）
# 自动切割部分已经在 generate_character_multiview 中实现


def generate_character_multiview(
    character_description: str,
    token: str,
    output_dir: str = "test_images",
    auto_cut: bool = True,
    model: str = DEFAULT_MODEL,
    style: str = "cinematic character",
    asset_id: Optional[str] = None,
    reference_image_path: str = None,
    use_image_reference_prompt: bool = False,
    use_strict_mode: bool = False
) -> Optional[str]:
    """
    生成多视角角色图像并保存
    
    Args:
        character_description: 角色描述
        token: AiProxy 客户端令牌
        output_dir: 输出目录
        auto_cut: 是否自动切割
        model: 模型名称
        style: 风格描述
        asset_id: 指定的资产ID (如果不给则自动生成 UUID)
        reference_image_path: 参考图片路径 (可选，用于图生图模式)
        use_image_reference_prompt: 是否使用图片参考专用提示词（保留原图动作）
        use_strict_mode: 严格复制模式，100%基于原图，不允许AI创意改动
    
    Returns:
        保存的图像路径 或 None
    """
    _ensure_imports()
    import uuid
    import json
    
    # 1. 生成唯一 ID
    if not asset_id:
        # 使用 UUID + 时间戳前缀确保绝对有序和唯一
        # 格式: 20260103_uuid
        # 或者直接 UUID。用户要求作为 "Asset ID"。UUID 更像 ID。
        # 结合一下：timestamp_shortuuid?
        # 为了简洁和唯一性，直接用 UUID4 string
        asset_id = str(uuid.uuid4())
        
    print("="*60)
    print(f"Cortex3d - Asset Generation [{asset_id}]")
    print("="*60)
    print(f"[角色] {character_description[:80]}...")
    print(f"[风格] {style}")
    print(f"[模型] {model}")
    print(f"[ID]   {asset_id}")
    if reference_image_path:
        print(f"[参考图] {reference_image_path}")
    if use_strict_mode:
        print(f"[严格模式] 100%复制原图")
    print("-"*60)
    
    # 构建提示词（根据模式选择不同模板）
    if use_strict_mode:
        print("[MODE] 严格复制模式 (100%基于原图，不允许创意改动)")
        prompt = build_strict_copy_prompt()
    elif use_image_reference_prompt:
        print("[MODE] 使用图片参考模式提示词 (保留原图动作)")
        prompt = build_image_reference_prompt(character_description)
    else:
        prompt = build_multiview_prompt(character_description, style=style)
    
    # 准备参考图片 (如果提供)
    reference_image_data = None
    if reference_image_path:
        try:
            ref_path = Path(reference_image_path)
            if ref_path.exists():
                with open(ref_path, "rb") as f:
                    img_bytes = f.read()
                suffix = ref_path.suffix.lower()
                if suffix in [".jpg", ".jpeg"]:
                    mime = "image/jpeg"
                elif suffix == ".png":
                    mime = "image/png"
                else:
                    mime = "image/jpeg"
                reference_image_data = f"data:{mime};base64,{base64.b64encode(img_bytes).decode()}"
                print(f"[参考图] 已加载 ({len(img_bytes)} bytes)")
        except Exception as e:
            print(f"[WARNING] 参考图片加载失败: {e}")
    
    # 调用 AiProxy (实际生成)
    result = generate_image_via_proxy(
        prompt=prompt,
        token=token,
        model=model,
        reference_image=reference_image_data
    )
    
    if not result:
        print("[FAILED] 图像生成失败")
        return None
    
    image_bytes, mime_type = result
    
    # 确定文件扩展名
    ext = "png"
    if "jpeg" in mime_type or "jpg" in mime_type:
        ext = "jpg"
    elif "webp" in mime_type:
        ext = "webp"
    
    # 保存图像
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{asset_id}.{ext}"
    filepath = output_path / filename
    
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    
    print(f"[保存图像] {filepath}")
    
    # 2. 保存元数据 (Metadata Sidecar)
    metadata = {
        "asset_id": asset_id,
        "created_at": datetime.now().isoformat(),
        "description": character_description,
        "style": style,
        "model": model,
        "prompt": prompt,
        "files": {
            "master": str(filename),
        }
    }
    
    # 3. 自动切割
    if auto_cut:
        try:
            from image_processor import process_quadrant_image
            print("\n[INFO] 自动切割四视图...")
            process_quadrant_image(
                input_path=str(filepath),
                output_dir=output_dir,
                remove_bg_flag=True,
                margin=5
            )
            # 记录切割后的文件
            metadata["files"]["front"] = f"{asset_id}_front.png"
            metadata["files"]["side"] = f"{asset_id}_left.png" # 左右等
            
        except ImportError:
            print("[WARNING] 无法导入 image_processor，跳过自动切割")
        except Exception as e:
            print(f"[WARNING] 切割失败: {e}")
            
    # 写入 JSON
    json_path = output_path / f"{asset_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[保存元数据] {json_path}")
    
    return str(filepath)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="通过 AiProxy 生成多视角角色图像"
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="角色描述"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("AIPROXY_TOKEN"),
        help="AiProxy 客户端令牌 (或设置 AIPROXY_TOKEN 环境变量)"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"模型名称 (默认: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--output", "-o",
        default="test_images",
        help="输出目录"
    )
    parser.add_argument(
        "--no-cut",
        action="store_true",
        help="不自动切割"
    )
    
    args = parser.parse_args()
    
    if not args.token:
        print("[ERROR] 请设置 AiProxy 令牌:")
        print("  export AIPROXY_TOKEN='your-token'")
        return 1
    
    if not args.description:
        print("请输入角色描述:")
        args.description = input("> ").strip()
        if not args.description:
            args.description = "末日幸存者，穿着破旧西装的商人"
    
    result = generate_character_multiview(
        character_description=args.description,
        token=args.token,
        output_dir=args.output,
        auto_cut=not args.no_cut,
        model=args.model
    )
    
    if result:
        print("\n✅ 完成!")
        return 0
    else:
        print("\n❌ 生成失败")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
