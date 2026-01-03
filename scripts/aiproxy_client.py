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
    build_multiview_prompt
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
    base_url: str = AIPROXY_BASE_URL
) -> Optional[Tuple[bytes, str]]:
    """
    通过 AiProxy 服务生成图像
    
    Args:
        prompt: 图像生成提示词
        token: AiProxy 客户端认证令牌
        model: 模型名称 (默认: nano-banana-pro)
        base_url: AiProxy 服务地址
    
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
        "model": model
    }
    
    print(f"[AiProxy] 调用 {endpoint}")
    print(f"[AiProxy] 模型: {model}")
    
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=120  # 图像生成可能需要较长时间
        )
        
        if response.status_code == 401:
            print("[ERROR] AiProxy 认证失败 - 请检查 token")
            return None
        
        if response.status_code != 200:
            print(f"[ERROR] AiProxy 返回错误: {response.status_code}")
            print(response.text[:500])
            return None
        
        data = response.json()
        reply = data.get("reply", "")
        
        # 从 HTML 响应中提取 base64 图像数据
        # AiProxy 返回格式: ```html-image-hidden ... <img src="data:image/png;base64,..." ...
        image_data = extract_image_from_reply(reply)
        
        if image_data:
            return image_data
        else:
            print("[WARNING] AiProxy 返回中未找到图像数据")
            print(f"[DEBUG] 返回内容预览: {reply[:200]}...")
            return None
            
    except requests.exceptions.Timeout:
        print("[ERROR] AiProxy 请求超时")
        return None
    except Exception as e:
        print(f"[ERROR] AiProxy 请求失败: {e}")
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


    # 自动切割
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
        except ImportError:
            print("[WARNING] 无法导入 image_processor，跳过自动切割")
        except Exception as e:
            print(f"[WARNING] 切割失败: {e}")
    
    return str(filepath)


def generate_character_multiview(
    character_description: str,
    token: str,
    output_dir: str = "test_images",
    auto_cut: bool = True,
    model: str = DEFAULT_MODEL,
    style: str = "cinematic character",
    asset_id: Optional[str] = None
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
    print("-"*60)
    
    # 构建提示词
    prompt = build_multiview_prompt(character_description, style=style)
    
    # 调用 AiProxy (实际生成)
    result = generate_image_via_proxy(
        prompt=prompt,
        token=token,
        model=model
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
