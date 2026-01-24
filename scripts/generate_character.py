#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cortex3d - 完整的多视角角色图像生成脚本
支持两种模式:
  1. AiProxy 模式 (推荐) - 通过 bot.bigjj.click/aiproxy 调用 NanoBanana
  2. 直连模式 - 直接调用 Google Gemini API

使用方法:
    # AiProxy 模式 (推荐)
    export AIPROXY_TOKEN="your-token"
    python generate_character.py "赛博朋克女战士"
    
    # 直连 Gemini API 模式
    export GEMINI_API_KEY="your-key"
    python generate_character.py "末日幸存者" --mode direct
"""

import argparse
import os
import sys
from pathlib import Path

# 添加 scripts 目录到 path
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

# 导入配置 (会自动加载 .env)
try:
    import config
except ImportError:
    pass # 如果找不到 config 也没关系，可能用户手动 export 了


def _iterative_360_generation(
    initial_reference_image: str,
    character_description: str,
    api_key: str,
    model_name: str,
    output_dir: str,
    auto_cut: bool,
    style: str,
    negative_prompt: str,
    use_strict_mode: bool,
    resolution: str,
    original_args,
    export_prompt: bool,
    subject_only: bool,
    with_props: list,
) -> str:
    """
    迭代 360 度生成模式：按顺序生成多个视图
    每个视图使用前一个生成的图像作为参考，以最大化 Gemini API 的一致性
    
    支持视角数量: 4 (FRONT/RIGHT/BACK/LEFT)
                  6 (FRONT/FRONT_RIGHT/RIGHT/BACK/BACK_LEFT/LEFT)
                  8 (6 views + TOP/BOTTOM)
    
    参考: Gemini API 文档 "Character Consistency: 360 view"
    https://ai.google.dev/gemini-api/docs/image-generation
    """
    from gemini_generator import generate_character_views
    import shutil
    
    output_path = Path(output_dir)
    
    # 根据 original_args.iterative_360 确定视角数量和序列
    view_count = int(original_args.iterative_360)
    
    if view_count == 4:
        angle_sequence = [
            {"angle": 0,   "name": "FRONT",      "description": "camera looking directly at the subject's front"},
            {"angle": 90,  "name": "RIGHT",      "description": "camera positioned to the RIGHT side of the subject"},
            {"angle": 180, "name": "BACK",       "description": "camera looking at the subject's back"},
            {"angle": 270, "name": "LEFT",       "description": "camera positioned to the LEFT side of the subject"},
        ]
    elif view_count == 6:
        angle_sequence = [
            {"angle": 0,   "name": "FRONT",      "description": "camera looking directly at the subject's front"},
            {"angle": 45,  "name": "FRONT_RIGHT","description": "camera at 45-degree angle between front and right side"},
            {"angle": 90,  "name": "RIGHT",      "description": "camera positioned to the RIGHT side of the subject"},
            {"angle": 180, "name": "BACK",       "description": "camera looking at the subject's back"},
            {"angle": 225, "name": "BACK_LEFT",  "description": "camera at 45-degree angle between back and left side"},
            {"angle": 270, "name": "LEFT",       "description": "camera positioned to the LEFT side of the subject"},
        ]
    elif view_count == 8:
        angle_sequence = [
            {"angle": 0,   "name": "FRONT",      "description": "camera looking directly at the subject's front"},
            {"angle": 45,  "name": "FRONT_RIGHT","description": "camera at 45-degree angle between front and right side"},
            {"angle": 90,  "name": "RIGHT",      "description": "camera positioned to the RIGHT side of the subject"},
            {"angle": 180, "name": "BACK",       "description": "camera looking at the subject's back"},
            {"angle": 225, "name": "BACK_LEFT",  "description": "camera at 45-degree angle between back and left side"},
            {"angle": 270, "name": "LEFT",       "description": "camera positioned to the LEFT side of the subject"},
            {"angle": 90,  "name": "TOP",        "description": "camera positioned ABOVE the subject, looking down"},
            {"angle": 270, "name": "BOTTOM",     "description": "camera positioned BELOW the subject, looking up"},
        ]
    else:
        raise ValueError(f"Unsupported view count: {view_count}")
    
    # ===================================================================
    # 导出提示词模式：仅导出第一个视图的提示词
    # ===================================================================
    if export_prompt:
        # 对于迭代 360 模式，仅导出第一个视图的提示词
        print("\n" + "="*70)
        print("📋 迭代 360 度模式 - 导出提示词参数")
        print("="*70)
        print(f"[视角数量] {view_count}-view")
        print(f"[模式] 迭代生成 - 每个视角单独生成，使用前一个作为参考")
        print(f"\n本次导出为第一个视角 ({angle_sequence[0]['name']}) 的提示词示例。")
        print(f"后续视角将自动生成，并强调保持一致性。\n")
        
        # 调用单次生成以获得提示词导出（仅第一个视角）
        temp_args = argparse.Namespace(**vars(original_args))
        temp_args.views = "1"
        temp_args.no_cut = True
        temp_args.custom_views = [angle_sequence[0]["name"].lower()]
        
        result = generate_character_views(
            character_description=character_description,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            auto_cut=False,
            style=style,
            view_mode="1-view",
            custom_views=[angle_sequence[0]["name"].lower()],
            negative_prompt=negative_prompt,
            reference_image_path=initial_reference_image,
            use_strict_mode=use_strict_mode,
            resolution=resolution,
            original_args=temp_args,
            export_prompt=True,  # 导出模式
            subject_only=subject_only,
            with_props=with_props
        )
        return None
    
    current_reference = initial_reference_image
    generated_images = []
    
    print("\n" + "="*70)
    print(f"🔄 迭代 360 度生成启动 ({view_count}-view Gemini Character Consistency Mode)")
    print("="*70)
    
    for idx, view_config in enumerate(angle_sequence, 1):
        angle = view_config["angle"]
        view_name = view_config["name"]
        view_description = view_config["description"]
        total_steps = len(angle_sequence)
        
        print(f"\n【第 {idx}/{total_steps} 步】 生成 {view_name} 视图 ({angle}°)")
        print("-" * 70)
        
        # 修改提示词以强调保持姿势一致性，仅改变相机角度
        if idx == 1:
            # 第一步：初始生成
            modified_description = character_description
            reference_context = ""
        else:
            # 后续步骤：强调一致性
            modified_description = character_description
            reference_context = f"\n\n⚠️ **CRITICAL for Consistency**: Keep the subject's pose, expression, and positioning IDENTICAL to the previous view. Only the camera angle changes to {angle}°."
        
        # 调用单视角生成（使用简化流程：生成 -> 不切割 -> 去背景）
        # 强制设置为不切割，因为迭代模式生成的是单个视角的单张图
        temp_args = argparse.Namespace(**vars(original_args))
        temp_args.views = "1"  # 单视角
        temp_args.no_cut = True  # 不切割（单张图不需要切割）
        temp_args.custom_views = [view_name.lower()]
        
        result = generate_character_views(
            character_description=modified_description + reference_context,
            api_key=api_key,
            model_name=model_name,
            output_dir=output_dir,
            auto_cut=False,  # 强制不切割
            style=style,
            view_mode="1-view",  # 单视角
            custom_views=[view_name.lower()],  # 指定单个视角
            negative_prompt=negative_prompt,
            reference_image_path=current_reference,
            use_strict_mode=use_strict_mode,
            resolution=resolution,
            original_args=temp_args,
            export_prompt=export_prompt,
            subject_only=subject_only,
            with_props=with_props
        )
        
        if result:
            # result 应该是去背景后的单个视角图像路径
            generated_images.append((view_name, result))
            print(f"✅ {view_name} 视图生成成功: {result}")
            
            # 为下一轮做准备：使用当前生成的图像作为参考
            if idx < len(angle_sequence):
                current_reference = result
                print(f"   └─ 下一步将使用此图像作为参考")
        else:
            print(f"❌ {view_name} 视图生成失败")
            return None
    
    # 合成多视角到一张图
    print("\n" + "="*70)
    print(f"📦 合成最终 {view_count} 视角图像")
    print("="*70)
    
    try:
        from PIL import Image
        
        images = []
        for view_name, img_path in generated_images:
            img = Image.open(img_path)
            images.append(img)
        
        # 根据视角数量确定布局
        img_width, img_height = images[0].size
        
        if view_count == 4:
            # 4 视角：1 行 4 列
            combined = Image.new('RGB', (img_width * 4, img_height))
            for idx, img in enumerate(images):
                combined.paste(img, (idx * img_width, 0))
            composite_name = "iterative_360_composite_4view.png"
        elif view_count == 6:
            # 6 视角：2 行 3 列
            combined = Image.new('RGB', (img_width * 3, img_height * 2))
            for idx, img in enumerate(images):
                row = idx // 3
                col = idx % 3
                combined.paste(img, (col * img_width, row * img_height))
            composite_name = "iterative_360_composite_6view.png"
        elif view_count == 8:
            # 8 视角：2 行 4 列（6个水平视图 + TOP + BOTTOM）
            combined = Image.new('RGB', (img_width * 4, img_height * 2))
            
            # 前 6 个水平视图放在第一行和第二行
            # TOP 和 BOTTOM 放在右下角
            for idx in range(6):
                row = idx // 3
                col = idx % 3
                combined.paste(images[idx], (col * img_width, row * img_height))
            
            # TOP 在右上角
            combined.paste(images[6], (3 * img_width, 0))
            # BOTTOM 在右下角
            combined.paste(images[7], (3 * img_width, img_height))
            composite_name = "iterative_360_composite_8view.png"
        else:
            raise ValueError(f"Unsupported view count: {view_count}")
        
        # 保存合成图
        composite_path = output_path / composite_name
        combined.save(str(composite_path))
        print(f"✅ 合成图已保存: {composite_path}")
        
        return str(composite_path)
    except Exception as e:
        print(f"⚠️  合成失败: {e}，但单个视图已生成")
        # 返回最后一张生成的图像
        return generated_images[-1][1]


def main():
    # 设置标准输出编码为 UTF-8（处理 Windows CP932 编码问题）
    if sys.stdout.encoding and 'utf' not in sys.stdout.encoding.lower():
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, RuntimeError):
            # 某些环境中 reconfigure 可能不可用
            pass
    
    parser = argparse.ArgumentParser(
        description="Cortex3d - Generate multi-view character images from description"
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Character description"
    )
    parser.add_argument(
        "--from-image",
        dest="from_image",
        default=None,
        help="Extract character features from reference image. Example: photo.jpg"
    )
    parser.add_argument(
        "--mode",
        choices=["proxy", "direct"],
        default="proxy",
        help="生成模式: proxy=AiProxy服务, direct=直连Gemini API"
    )
    parser.add_argument(
        "--token",
        default=None,  # 将根据 mode 自动选择环境变量
        help="认证 Token: proxy模式使用 AIPROXY_TOKEN, direct模式使用 GEMINI_API_KEY"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name. Default: models/nano-banana-pro-preview (same for both proxy and direct mode)"
    )
    parser.add_argument(
        "--output", "-o",
        default="test_images",
        help="Output directory"
    )
    parser.add_argument(
        "--no-cut",
        action="store_true",
        help="Disable auto-cutting"
    )
    parser.add_argument(
        "--to-3d",
        action="store_true",
        help="Auto-convert to 3D model after generation"
    )
    parser.add_argument(
        "--algo",
        choices=["hunyuan3d", "hunyuan3d-2.1", "hunyuan3d-omni", "trellis", "trellis2"],
        default="hunyuan3d",
        help="3D algorithm. Default: hunyuan3d. Use omni for pose control"
    )
    parser.add_argument(
        "--quality",
        choices=["balanced", "high", "ultra"],
        default="high",
        help="3D quality: balanced(fast)/high(default)/ultra(best but slow)"
    )
    parser.add_argument(
        "--geometry-only", "--fast",
        dest="geometry_only",
        action="store_true",
        help="Generate geometry only, no texture (much faster)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Auto-open preview after generation"
    )
    parser.add_argument(
        "--pose",
        default=None,
        help="Pose control file path (only for hunyuan3d-omni). Example: poses/t_pose.json"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict copy mode: generate multi-view 100%% based on reference image, no AI creativity. Use with --from-image"
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Preprocess input image: remove background for better AI quality. Use with --from-image"
    )
    parser.add_argument(
        "--preprocess-model",
        dest="preprocess_model",
        choices=["birefnet-general", "isnet-general-use", "u2net"],
        default="birefnet-general",
        help="Background removal model for preprocessing. Default: birefnet-general"
    )
    
    parser.add_argument(
        "--resolution",
        choices=["1K", "2K", "4K"],
        default="2K",
        help="Image resolution: 1K(fast)/2K(default)/4K(high quality but slow)"
    )
    
    parser.add_argument(
        "--export-prompt",
        action="store_true",
        help="Export prompt and parameters instead of calling API. Use this to manually copy to Gemini App when API quota is limited."
    )
    
    parser.add_argument(
        "--style",
        default=None,
        help="Style description or preset name. Use --list-styles to see all presets."
    )
    
    parser.add_argument(
        "--photorealistic", "--real",
        dest="photorealistic",
        action="store_true",
        help="Preset: Photorealistic (8k, raw photo, realistic texture)"
    )
    
    parser.add_argument(
        "--anime",
        action="store_true",
        help="Preset: Anime/manga style (cel shaded, vibrant colors)"
    )
    
    # =========================================================================
    # 扩展风格预设参数
    # =========================================================================
    parser.add_argument(
        "--ghibli",
        action="store_true",
        help="Preset: Studio Ghibli / Miyazaki style (watercolor, whimsical)"
    )
    
    parser.add_argument(
        "--pixel",
        action="store_true",
        help="Preset: Pixel art / retro game style (16-bit, crisp pixels)"
    )
    
    parser.add_argument(
        "--minecraft", "--voxel",
        dest="minecraft",
        action="store_true",
        help="Preset: Minecraft / voxel block style (cubic geometry)"
    )
    
    parser.add_argument(
        "--clay", "--claymation",
        dest="clay",
        action="store_true",
        help="Preset: Claymation / plasticine style (stop-motion aesthetic)"
    )
    
    parser.add_argument(
        "--plush", "--felt",
        dest="plush",
        action="store_true",
        help="Preset: Plush toy / felt fabric style (soft, kawaii)"
    )
    
    parser.add_argument(
        "--paper", "--papercraft",
        dest="paper",
        action="store_true",
        help="Preset: Paper cutout / Paper Mario style (flat 2.5D)"
    )
    
    parser.add_argument(
        "--cyberpunk", "--neon",
        dest="cyberpunk",
        action="store_true",
        help="Preset: Cyberpunk / neon sci-fi style"
    )
    
    parser.add_argument(
        "--fantasy", "--medieval",
        dest="fantasy",
        action="store_true",
        help="Preset: High fantasy / medieval RPG style"
    )
    
    parser.add_argument(
        "--watercolor",
        action="store_true",
        help="Preset: Traditional watercolor painting style"
    )
    
    parser.add_argument(
        "--oil", "--oil-painting",
        dest="oil",
        action="store_true",
        help="Preset: Classical oil painting style"
    )
    
    parser.add_argument(
        "--3d-toon", "--pixar",
        dest="toon3d",
        action="store_true",
        help="Preset: 3D cartoon / Pixar-Disney style"
    )
    
    parser.add_argument(
        "--comic", "--marvel",
        dest="comic",
        action="store_true",
        help="Preset: American comic book / superhero style"
    )
    
    parser.add_argument(
        "--minimal", "--flat",
        dest="minimal",
        action="store_true",
        help="Preset: Minimalist / flat design style"
    )
    
    parser.add_argument(
        "--lowpoly",
        action="store_true",
        help="Preset: Low poly / geometric 3D style"
    )
    
    parser.add_argument(
        "--list-styles",
        dest="list_styles",
        action="store_true",
        help="List all available style presets and exit"
    )
    
    parser.add_argument(
        "--from-id",
        dest="from_id",
        default=None,
        help="Skip 2D generation, use existing image ID for 3D. Example: a7af1af9-a592-4499-a456-2bea8428fe49"
    )
    
    # =========================================================================
    # Multi-view mode parameters
    # =========================================================================
    parser.add_argument(
        "--views",
        choices=["4", "6", "8"],
        default="4",
        help="Number of views: 4(default)=standard, 6=with 45-degree angles, 8=with top/bottom"
    )
    
    parser.add_argument(
        "--custom-views",
        dest="custom_views",
        nargs="+",
        default=None,
        metavar="VIEW",
        help="Custom view list (overrides --views). Options: front, front_right, right, back, left, front_left, top, bottom"
    )
    
    # =========================================================================
    # Subject isolation parameters (主体隔离参数)
    # =========================================================================
    parser.add_argument(
        "--subject-only", "--isolate",
        dest="subject_only",
        action="store_true",
        help="Only process the main subject (person/character), remove all background objects like cars, furniture, etc."
    )
    
    parser.add_argument(
        "--with-props",
        dest="with_props",
        nargs="+",
        default=None,
        metavar="PROP",
        help="Include specific props/objects with the subject. Examples: --with-props bicycle basketball guitar"
    )
    
    # =========================================================================
    # Negative prompt parameters
    # =========================================================================
    parser.add_argument(
        "--no-negative",
        dest="no_negative",
        action="store_true",
        help="Disable negative prompts"
    )
    
    parser.add_argument(
        "--negative-categories",
        dest="negative_categories",
        nargs="+",
        default=["anatomy", "quality", "layout"],
        choices=["anatomy", "quality", "layout"],
        help="Negative prompt categories (default: anatomy quality layout)"
    )
    
    # =========================================================================
    # 360-degree iterative mode (Gemini API best practice)
    # =========================================================================
    parser.add_argument(
        "--iterative-360",
        choices=["4", "6", "8"],
        dest="iterative_360",
        default=None,
        help="Iterative 360-degree mode with specified view count (4/6/8). Generate views sequentially, using each output as reference for the next. Requires --from-image."
    )
    
    # =========================================================================
    # 智能视角验证与自动补全 (Auto View Validation & Completion)
    # =========================================================================
    parser.add_argument(
        "--auto-complete",
        action="store_true",
        dest="auto_complete",
        help="自动验证生成的多视角图并补全缺失视角。AI会检测每个面板的实际视角，发现缺失则自动补生成。"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        dest="validate_only",
        help="仅验证生成的图片视角，不进行补全。输出检测结果和建议。"
    )
    
    parser.add_argument(
        "--max-completion-retries",
        type=int,
        dest="max_completion_retries",
        default=3,
        help="自动补全的最大重试次数 (默认: 3)"
    )
    
    # =========================================================================
    # P0 高优先级编辑功能 - 添加/移除元素
    # =========================================================================
    parser.add_argument(
        "--mode-edit",
        action="store_true",
        dest="mode_edit",
        help="激活编辑模式: 添加/移除/修改角色元素。需要配合 --edit-elements 和 --from-edited"
    )
    
    parser.add_argument(
        "--edit-elements",
        type=str,
        dest="edit_elements",
        help="编辑指令。格式: 'add:xxx' 或 'remove:xxx' 或 'modify:xxx'。例: 'add:肩部火焰翅膀'"
    )
    
    parser.add_argument(
        "--from-edited",
        type=str,
        dest="from_edited",
        help="要编辑的源图像路径"
    )
    
    # =========================================================================
    # P0 高优先级编辑功能 - 语义遮盖/细节修复
    # =========================================================================
    parser.add_argument(
        "--mode-refine",
        action="store_true",
        dest="mode_refine",
        help="激活优化模式: 修复特定细节(脸部/手指/姿势等)。需要配合 --refine-details 和 --from-refine"
    )
    
    parser.add_argument(
        "--refine-details",
        choices=["face", "hands", "pose", "eyes", "custom"],
        dest="refine_details",
        help="要优化的细节部位"
    )
    
    parser.add_argument(
        "--detail-issue",
        type=str,
        dest="detail_issue",
        help="具体问题描述。例: '左手有6根手指，需要改为5根'"
    )
    
    parser.add_argument(
        "--from-refine",
        type=str,
        dest="from_refine",
        help="要优化的源图像路径"
    )
    
    # ========================================
    # P1: 风格转换模式参数
    # ========================================
    parser.add_argument(
        "--mode-style",
        action="store_true",
        dest="mode_style",
        help="激活风格转换模式: 改变角色整体美学风格。需要配合 --style-preset/--custom-style 和 --from-style"
    )
    
    parser.add_argument(
        "--style-preset",
        type=str,
        dest="style_preset",
        choices=["anime", "cinematic", "oil-painting", "watercolor", "comic", "3d"],
        help="风格预设: anime(日本动画) | cinematic(电影级) | oil-painting(油画) | watercolor(水彩) | comic(漫画) | 3d(3D渲染)"
    )
    
    parser.add_argument(
        "--custom-style",
        type=str,
        dest="custom_style",
        help="自定义风格描述(覆盖 --style-preset)。例: 'impressionist Renaissance painting'"
    )
    
    parser.add_argument(
        "--from-style",
        type=str,
        dest="from_style",
        help="要进行风格转换的源图像路径"
    )
    
    parser.add_argument(
        "--preserve-details",
        action="store_true",
        dest="preserve_details",
        default=True,
        help="风格转换时是否保留原始细节 (默认: 是)"
    )
    
    # =========================================================================
    # P0 高优先级功能 - 高级合成：组合多张图片
    # =========================================================================
    parser.add_argument(
        "--mode-composite",
        action="store_true",
        dest="mode_composite",
        help="激活合成模式: 组合多张图片创建新场景。用于换衣服、换配饰、创意拼贴等"
    )
    
    parser.add_argument(
        "--composite-images",
        nargs="+",
        dest="composite_images",
        metavar="IMAGE",
        help="要合成的多张图片路径。例: model.png dress.png hat.png"
    )
    
    parser.add_argument(
        "--composite-instruction",
        type=str,
        dest="composite_instruction",
        help="合成指令。例: '让第二张图的人穿上第一张图的裙子' 或 'Put the hat from image 2 on the person in image 1'"
    )
    
    parser.add_argument(
        "--composite-output-name",
        type=str,
        dest="composite_output_name",
        default=None,
        help="合成输出文件名 (可选，默认自动生成)"
    )
    
    # =========================================================================
    # P0 功能: 高保真细节保留 (Detail Preserve Edit)
    # =========================================================================
    parser.add_argument(
        "--mode-preserve",
        action="store_true",
        dest="mode_preserve",
        help="激活高保真编辑模式: 在修改图像时保留关键细节(面部、徽标等)。比普通编辑更适合需要保留精细特征的场景"
    )
    
    parser.add_argument(
        "--preserve-image",
        type=str,
        dest="preserve_image",
        metavar="IMAGE",
        help="主图片路径 (包含要保留细节的图片)"
    )
    
    parser.add_argument(
        "--preserve-element",
        type=str,
        dest="preserve_element",
        metavar="IMAGE",
        default=None,
        help="元素图片路径 (可选，要添加到主图的元素，如 logo、配饰等)"
    )
    
    parser.add_argument(
        "--preserve-detail-desc",
        type=str,
        dest="preserve_detail_desc",
        help="要保留的关键细节描述。例: '保持女性的面部特征完全不变'"
    )
    
    parser.add_argument(
        "--preserve-instruction",
        type=str,
        dest="preserve_instruction",
        help="修改指令。例: '将 logo 添加到她的黑色 T 恤上'"
    )
    
    parser.add_argument(
        "--preserve-output-name",
        type=str,
        dest="preserve_output_name",
        default=None,
        help="输出文件名 (可选)"
    )
    
    # 在解析参数前，检查常见的参数错误并提供友好提示
    friendly_hint_shown = False
    for arg in sys.argv[1:]:
        if arg.startswith('--'):
            # 检查常见拼写错误
            if arg == '--view':
                print(f"\n[ERROR] Parameter '--view' does not exist")
                print(f"[HINT] Did you mean '--views'?")
                print(f"       Example: python scripts/generate_character.py --views 8\n")
                friendly_hint_shown = True
                break
            # 检查带数字的无效参数（如 --14, --360 等）
            elif len(arg) > 2 and arg[2:].replace('-', '').isdigit():
                print(f"\n[ERROR] Invalid parameter: '{arg}'")
                print(f"[HINT] To generate multi-view images, use one of:")
                print(f"       --views 8              # Standard multi-view (8 fixed angles)")
                print(f"       --iterative-360 8      # Iterative 360 (8 sequential angles, better consistency)\n")
                friendly_hint_shown = True
                break
    
    # 解析参数（如果显示了友好提示，argparse 会继续显示完整的 usage）
    try:
        args = parser.parse_args()
    except SystemExit as e:
        # 如果已经显示了友好提示，重新抛出让 argparse 显示完整帮助
        if friendly_hint_shown:
            pass  # argparse 已经打印了 usage，我们的提示在上面
        raise
    
    # 根据模式自动设置token(如果未提供)
    if args.token is None:
        if args.mode == "proxy":
            args.token = os.environ.get("AIPROXY_TOKEN")
        else:  # direct mode
            args.token = os.environ.get("GEMINI_API_KEY")
    
    # Banner
    try:
        print("""
╔═══════════════════════════════════════════════════════════════╗
║                    Cortex3d 角色生成器                         ║
║         AI 多视角图像生成 → 切割 → 去背景 → 3D建模             ║
╚═══════════════════════════════════════════════════════════════╝
        """)
    except UnicodeEncodeError:
        # 在某些终端中使用 ASCII 艺术代替
        print("""
============================================================
                     Cortex3d Character Generator
        AI Multi-view Image Generation → Cropping → Background Removal → 3D Modeling
============================================================
        """)
    
    # =========================================================================
    # 列出所有可用风格预设
    # =========================================================================
    if getattr(args, 'list_styles', False):
        from prompts.styles import STYLE_PRESETS, list_all_styles
        
        print("\n📎 可用风格预设:")
        print("=" * 70)
        
        seen = set()
        for preset in STYLE_PRESETS.values():
            if preset.name not in seen:
                aliases = ", ".join([f"--{a}" for a in preset.aliases[:2]])
                print(f"\n  --{preset.name:<14} {preset.description}")
                print(f"      别名: {aliases}")
                print(f"      关键词: {', '.join(preset.keywords[:4])}")
                seen.add(preset.name)
        
        print("\n" + "=" * 70)
        print("💡 使用方法:")
        print("   python scripts/generate_character.py --from-image img.png --pixel")
        print("   python scripts/generate_character.py --from-image img.png --style minecraft")
        print("   python scripts/generate_character.py --from-image img.png --ghibli --custom-views front left")
        print("")
        sys.exit(0)
    
    # =========================================================================
    # 图像编辑模式：使用 Gemini 对角色图像进行编辑
    # =========================================================================
    if args.mode_edit:
        print("[图像编辑模式]")
        
        # 验证必需参数
        if not args.from_edited:
            print("[ERROR] --mode-edit 需要 --from-edited 参数（源图像路径）")
            sys.exit(1)
        
        if not args.edit_elements:
            print("[ERROR] --mode-edit 需要 --edit-elements 参数（操作指令）")
            print("        格式示例: 'add:肩部炮台' 或 'remove:头顶绶带' 或 'modify:左手')\"")
            sys.exit(1)
        
        # 验证源图像存在
        source_path = Path(args.from_edited)
        if not source_path.exists():
            print(f"[ERROR] 源图像不存在: {args.from_edited}")
            sys.exit(1)
        
        print(f"  └─ 源图像: {args.from_edited}")
        print(f"  └─ 编辑操作: {args.edit_elements}")
        print(f"  └─ 输出目录: {args.output}")
        print(f"  └─ 调用模式: {args.mode.upper()}")
        print("")
        
        # 导入编辑函数
        from gemini_generator import edit_character_elements
        
        # 执行编辑 (遵守 proxy/direct 设置)
        character_desc = args.character if args.character else "a character"
        try:
            output_path = edit_character_elements(
                source_image_path=str(source_path),
                edit_instruction=args.edit_elements,
                character_description=character_desc,
                api_key=args.token,
                model_name=args.model if args.model else "gemini-2.5-flash-image",
                output_dir=args.output,
                mode=args.mode  # 传入 proxy/direct 模式
            )
            
            if output_path:
                print(f"\n✅ 编辑完成！")
                print(f"   输出: {output_path}")
            else:
                print(f"\n❌ 编辑失败，请检查日志")
                sys.exit(1)
            
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] 编辑过程出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # =========================================================================
    # 图像细节优化模式：使用 Gemini 对特定部分进行细节修复
    # =========================================================================
    if args.mode_refine:
        print("[图像细节优化模式]")
        
        # 验证必需参数
        if not args.from_refine:
            print("[ERROR] --mode-refine 需要 --from-refine 参数（源图像路径）")
            sys.exit(1)
        
        if not args.refine_details:
            print("[ERROR] --mode-refine 需要 --refine-details 参数")
            print("        选项: face | hands | pose | eyes | custom")
            sys.exit(1)
        
        # 验证源图像存在
        source_path = Path(args.from_refine)
        if not source_path.exists():
            print(f"[ERROR] 源图像不存在: {args.from_refine}")
            sys.exit(1)
        
        print(f"  └─ 源图像: {args.from_refine}")
        print(f"  └─ 优化部分: {args.refine_details}")
        if args.detail_issue:
            print(f"  └─ 问题描述: {args.detail_issue}")
        print(f"  └─ 输出目录: {args.output}")
        print(f"  └─ 调用模式: {args.mode.upper()}")
        print("")
        
        # 导入细节修复函数
        from gemini_generator import refine_character_details
        
        # 执行细节修复 (遵守 proxy/direct 设置)
        character_desc = args.character if args.character else "a character"
        detail_issue = args.detail_issue if args.detail_issue else "please improve the quality"
        
        try:
            output_path = refine_character_details(
                source_image_path=str(source_path),
                detail_part=args.refine_details,
                issue_description=detail_issue,
                character_description=character_desc,
                api_key=args.token,
                model_name=args.model if args.model else "gemini-2.5-flash-image",
                output_dir=args.output,
                mode=args.mode  # 传入 proxy/direct 模式
            )
            
            if output_path:
                print(f"\n✅ 细节优化完成！")
                print(f"   输出: {output_path}")
            else:
                print(f"\n❌ 优化失败，请检查日志")
                sys.exit(1)
            
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] 优化过程出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # =========================================================================
    # P1 风格转换模式：对角色应用艺术风格转换
    # =========================================================================
    if args.mode_style:
        print("[风格转换模式]")
        
        # 验证必需参数
        if not args.from_style:
            print("[ERROR] --mode-style 需要 --from-style 参数（源图像路径）")
            sys.exit(1)
        
        if not args.style_preset and not args.custom_style:
            print("[ERROR] --mode-style 需要 --style-preset 或 --custom-style 参数")
            print("        预设选项: anime | cinematic | oil-painting | watercolor | comic | 3d")
            sys.exit(1)
        
        # 检查源图像是否存在
        source_path = Path(args.from_style)
        if not source_path.exists():
            print(f"[ERROR] 源图像不存在: {args.from_style}")
            sys.exit(1)
        
        # 确定风格预设
        style_preset = args.custom_style if args.custom_style else args.style_preset
        
        print(f"  └─ 源图像: {args.from_style}")
        print(f"  └─ 风格: {style_preset}")
        print(f"  └─ 保留细节: {'是' if args.preserve_details else '否'}")
        print(f"  └─ 输出目录: {args.output}")
        print(f"  └─ 调用模式: {args.mode.upper()}")
        print("")
        
        # 导入风格转换函数
        from gemini_generator import style_transfer_character
        
        # 执行风格转换 (遵守 proxy/direct 设置)
        character_desc = args.character if args.character else "a character"
        try:
            output_path = style_transfer_character(
                source_image_path=str(source_path),
                style_preset=style_preset if not args.custom_style else "custom",
                character_description=character_desc,
                api_key=args.token,
                model_name=args.model if args.model else "gemini-2.5-flash-image",
                output_dir=args.output,
                custom_style=args.custom_style if args.custom_style else None,
                preserve_details=args.preserve_details,
                mode=args.mode  # 传入 proxy/direct 模式
            )
            
            if output_path:
                print(f"\n✅ 风格转换完成！")
                print(f"   输出: {output_path}")
            else:
                print(f"\n❌ 风格转换失败，请检查日志")
                sys.exit(1)
            
            sys.exit(0)
        except Exception as e:
            print(f"[ERROR] 风格转换过程出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # =========================================================================
    # 高级合成模式：组合多张图片创建新场景
    # 可作为预处理步骤，结果可继续用于后续生成流程
    # =========================================================================
    preprocessed_image = None  # 用于存储预处理后的图片路径
    
    if args.mode_composite:
        print("[高级合成模式]")
        print("  用途: 换衣服、换配饰、创意拼贴、产品模型等")
        
        # 验证必需参数
        if not args.composite_images or len(args.composite_images) < 1:
            print("[ERROR] --mode-composite 需要 --composite-images 参数（至少1张图片）")
            print("        示例: --composite-images model.png dress.png")
            print("        或配合 --from-image: --from-image model.png --composite-images dress.png")
            sys.exit(1)
        
        if not args.composite_instruction:
            print("[ERROR] --mode-composite 需要 --composite-instruction 参数（合成指令）")
            print("        示例: --composite-instruction '让模特穿上这件裙子'")
            sys.exit(1)
        
        # 如果有 --from-image，将其作为第一张图片
        if args.from_image:
            all_images = [args.from_image] + args.composite_images
        else:
            all_images = args.composite_images
            if len(all_images) < 2:
                print("[ERROR] --mode-composite 需要至少2张图片")
                print("        示例: --composite-images model.png dress.png")
                print("        或: --from-image model.png --composite-images dress.png")
                sys.exit(1)
        
        # 验证所有图片存在
        image_paths = []
        for img_path in all_images:
            p = Path(img_path)
            if not p.exists():
                # 尝试在常见目录查找
                for search_dir in [Path("."), Path("test_images"), Path("reference_images"), Path(args.output)]:
                    candidate = search_dir / img_path
                    if candidate.exists():
                        p = candidate
                        break
            
            if not p.exists():
                print(f"[ERROR] 图片不存在: {img_path}")
                sys.exit(1)
            
            image_paths.append(str(p))
        
        print(f"\n  └─ 输入图片 ({len(image_paths)} 张):")
        for i, img in enumerate(image_paths, 1):
            print(f"      [{i}] {Path(img).name}")
        print(f"  └─ 合成指令: {args.composite_instruction}")
        print(f"  └─ 输出目录: {args.output}")
        print(f"  └─ 调用模式: {args.mode.upper()}")
        print("")
        
        # 导入合成函数
        from gemini_generator import composite_images
        
        # 执行合成 (遵守 proxy/direct 设置)
        try:
            output_path = composite_images(
                image_paths=image_paths,
                instruction=args.composite_instruction,
                api_key=args.token,
                model_name=args.model if args.model else "gemini-2.5-flash-image",
                output_dir=args.output,
                output_name=args.composite_output_name,
                mode=args.mode
            )
            
            if output_path:
                print(f"\n✅ 合成完成！")
                print(f"   输出: {output_path}")
                preprocessed_image = output_path
            else:
                print(f"\n❌ 合成失败，请检查日志")
                sys.exit(1)
            
            # 判断是否继续后续处理
            # 如果有其他生成参数（如 custom_views, 风格等），则继续；否则退出
            has_further_processing = (
                args.custom_views or 
                args.generate_3d or 
                args.iterative_360 or
                getattr(args, 'style_3d_toon', False) or
                getattr(args, 'style_ghibli', False) or
                getattr(args, 'style_chibi', False) or
                getattr(args, 'style_real', False)
            )
            
            if not has_further_processing:
                sys.exit(0)
            else:
                # 将合成结果设置为后续处理的输入
                args.from_image = output_path
                print(f"\n🔄 继续后续处理流程，使用合成结果作为输入...")
                print("")
        except Exception as e:
            print(f"[ERROR] 合成过程出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # =========================================================================
    # 高保真细节保留模式检查 (--mode-preserve)
    # 可作为预处理步骤，结果可继续用于后续生成流程
    # =========================================================================
    if args.mode_preserve:
        print("\n" + "═"*60)
        print("🔍 激活高保真细节保留模式")
        print("═"*60)
        print("  用途: 在修改图像时保留关键细节 (面部、徽标、特定元素)")
        print("  示例: 给人物 T 恤添加 logo 但保持面部不变")
        
        # 验证必需参数 - 如果有 --from-image，可以用它作为主图片
        preserve_source = args.preserve_image or args.from_image
        if not preserve_source:
            print("[ERROR] --mode-preserve 需要 --preserve-image 或 --from-image 参数（主图片路径）")
            print("        示例: --preserve-image person.png")
            print("        或: --from-image person.png --mode-preserve ...")
            sys.exit(1)
        
        if not args.preserve_instruction:
            print("[ERROR] --mode-preserve 需要 --preserve-instruction 参数（修改指令）")
            print("        示例: --preserve-instruction '将 logo 添加到 T 恤上'")
            sys.exit(1)
        
        # 查找主图片
        main_image = Path(preserve_source)
        if not main_image.exists():
            for search_dir in [Path("."), Path("test_images"), Path("reference_images"), Path(args.output)]:
                candidate = search_dir / preserve_source
                if candidate.exists():
                    main_image = candidate
                    break
        
        if not main_image.exists():
            print(f"[ERROR] 主图片不存在: {preserve_source}")
            sys.exit(1)
        
        # 查找元素图片 (可选)
        element_image = None
        if args.preserve_element:
            element_path = Path(args.preserve_element)
            if not element_path.exists():
                for search_dir in [Path("."), Path("test_images"), Path("reference_images"), Path(args.output)]:
                    candidate = search_dir / args.preserve_element
                    if candidate.exists():
                        element_path = candidate
                        break
            
            if not element_path.exists():
                print(f"[ERROR] 元素图片不存在: {args.preserve_element}")
                sys.exit(1)
            
            element_image = str(element_path)
        
        print(f"\n  └─ 主图片: {main_image.name}")
        if element_image:
            print(f"  └─ 元素图片: {Path(element_image).name}")
        if args.preserve_detail_desc:
            print(f"  └─ 保留细节: {args.preserve_detail_desc[:60]}{'...' if len(args.preserve_detail_desc) > 60 else ''}")
        print(f"  └─ 修改指令: {args.preserve_instruction[:60]}{'...' if len(args.preserve_instruction) > 60 else ''}")
        print(f"  └─ 调用模式: {args.mode.upper()}")
        print("")
        
        # 导入高保真编辑函数
        from gemini_generator import preserve_detail_edit
        
        # 执行高保真编辑
        try:
            output_path = preserve_detail_edit(
                main_image_path=str(main_image),
                instruction=args.preserve_instruction,
                preserve_details=args.preserve_detail_desc,
                element_image_path=element_image,
                api_key=args.token,
                model_name=args.model if args.model else "gemini-2.5-flash-image",
                output_dir=args.output,
                output_name=args.preserve_output_name,
                mode=args.mode
            )
            
            if output_path:
                print(f"\n✅ 高保真编辑完成！")
                print(f"   输出: {output_path}")
                preprocessed_image = output_path
            else:
                print(f"\n❌ 编辑失败，请检查日志")
                sys.exit(1)
            
            # 判断是否继续后续处理
            has_further_processing = (
                args.custom_views or 
                args.generate_3d or 
                args.iterative_360 or
                getattr(args, 'style_3d_toon', False) or
                getattr(args, 'style_ghibli', False) or
                getattr(args, 'style_chibi', False) or
                getattr(args, 'style_real', False)
            )
            
            if not has_further_processing:
                sys.exit(0)
            else:
                # 将编辑结果设置为后续处理的输入
                args.from_image = output_path
                print(f"\n🔄 继续后续处理流程，使用编辑结果作为输入...")
                print("")
        except Exception as e:
            print(f"[ERROR] 高保真编辑出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # =========================================================================
    # 迭代 360 度模式检查
    # =========================================================================
    if args.iterative_360:
        if not args.from_image:
            print("[ERROR] --iterative-360 requires --from-image parameter")
            sys.exit(1)
        
        # 强制单视图模式用于迭代
        args.views = "1"
        view_count = int(args.iterative_360)
        print("\n[迭代 360 度模式]")
        print(f"  └─ 将按顺序生成: {view_count} 个视图")
        print(f"  └─ 每个视图使用前一个生成的图像作为参考")
        print(f"  └─ 目的: 最大化 Gemini API 生成的角色一致性")
        print("")
    
    # =========================================================================
    # 快速模式：从已有ID直接生成3D
    # =========================================================================
    if args.from_id:
        image_id = args.from_id.strip()
        output_path = Path(args.output)
        
        # 查找 front 视图
        front_img = output_path / f"{image_id}_front.png"
        
        if not front_img.exists():
            # 尝试查找任何匹配的文件
            matches = list(output_path.glob(f"{image_id}*_front.png"))
            if matches:
                front_img = matches[0]
                image_id = front_img.stem.replace("_front", "")
            else:
                print(f"[ERROR] 找不到ID为 '{image_id}' 的图片")
                print(f"        请确认 {output_path}/{image_id}_front.png 存在")
                print(f"\n可用的图片ID:")
                for f in sorted(output_path.glob("*_front.png"))[-10:]:
                    print(f"  • {f.stem.replace('_front', '')}")
                sys.exit(1)
        
        # 检查所有视图
        views = ["front", "back", "left", "right"]
        available_views = []
        for view in views:
            view_path = output_path / f"{image_id}_{view}.png"
            if view_path.exists():
                available_views.append(view)
        
        print(f"[ID模式] 使用已有图片: {image_id}")
        print(f"[可用视图] {', '.join(available_views)}")
        print(f"[Front图片] {front_img}")
        
        # 直接进入 3D 生成
        print("\n" + "═" * 50)
        print(f"🚀 启动 3D 生成流水线 ({args.algo.upper()})...")
        print("═" * 50)
        
        reconstructor_script = script_dir / "reconstructor.py"
        cmd = [
            sys.executable,
            str(reconstructor_script),
            str(front_img),
            "--algo", args.algo,
            "--quality", args.quality,
            "--output_dir", str(Path("outputs"))
        ]
        
        # 添加几何模型Only选项
        if getattr(args, 'geometry_only', False):
            cmd.append("--no-texture")
        
        # 添加姿势控制 (仅 hunyuan3d-omni 支持)
        if args.algo == "hunyuan3d-omni" and args.pose:
            cmd.extend(["--control-type", "pose", "--control-input", str(args.pose)])
        
        try:
            import subprocess
            subprocess.run(cmd, check=True)
            print("\n[SUCCESS] 3D 生成完成！")
            
            # 根据算法确定输出路径
            algo_dir = "hunyuan3d" if args.algo.startswith("hunyuan") else args.algo
            glb_path = Path(f"outputs/{algo_dir}") / f"{image_id}_front.glb"
            obj_path = Path(f"outputs/{algo_dir}") / f"{image_id}_front.obj"
            
            print(f"\n生成的3D模型:")
            if glb_path.exists():
                print(f"  📦 GLB: {glb_path}")
            if obj_path.exists():
                print(f"  📦 OBJ: {obj_path}")
                
            # 自动预览
            if args.preview and glb_path.exists():
                if sys.platform == "darwin":
                    subprocess.run(["open", str(glb_path)])
                elif sys.platform == "win32":
                    os.startfile(str(glb_path))
                    
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] 3D 生成失败 (Exit Code {e.returncode})")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] 3D 生成异常: {e}")
            sys.exit(1)
            
        sys.exit(0)  # 成功退出，不继续执行后面的2D生成逻辑
    
    # =========================================================================
    # 正常模式：2D生成 + 可选3D
    # =========================================================================
    
    # 导出模式不需要token验证（不会实际调用API）
    if not args.export_prompt:
        # 检查认证
        if args.mode == "proxy":
            if not args.token:
                print("\n⚠️  未设置 AiProxy 令牌\n")
                
                # 构建基于实际命令的建议
                base_cmd_parts = ["python scripts\\generate_character.py"]
                if args.from_image:
                    base_cmd_parts.append(f"--from-image {args.from_image}")
                elif args.description:
                    base_cmd_parts.append(f'"{args.description}"')
                if args.strict:
                    base_cmd_parts.append("--strict")
                
                proxy_cmd_with_token = " ".join(base_cmd_parts + ["--mode proxy --token 'your-aiproxy-token'"])
                direct_cmd = " ".join(base_cmd_parts + ["--mode direct --token 'your-gemini-api-key'"])
                export_cmd = " ".join(base_cmd_parts + ["--export-prompt"])
                
                print("💡 解决方案:")
                print(f"\n   选项 1: 直接传递 AiProxy Token (推荐)")
                print(f"   {proxy_cmd_with_token}")
                print(f"\n   选项 2: 使用直连模式")
                print(f"   {direct_cmd}")
                print(f"\n   选项 3: 导出提示词 (不消耗API配额)")
                print(f"   {export_cmd}")
                print(f"\n   选项 4: 设置环境变量")
                print(f"   $env:AIPROXY_TOKEN='your-token'  # PowerShell")
                print(f"   {' '.join(base_cmd_parts + ['--mode proxy'])}\n")
                sys.exit(1)
        else:
            if not args.token:
                print("\n⚠️  未设置 Gemini API Key\n")
                
                # 构建基于实际命令的建议
                base_cmd_parts = ["python scripts\\generate_character.py"]
                if args.from_image:
                    base_cmd_parts.append(f"--from-image {args.from_image}")
                elif args.description:
                    base_cmd_parts.append(f'"{args.description}"')
                if args.strict:
                    base_cmd_parts.append("--strict")
                
                direct_cmd_with_key = " ".join(base_cmd_parts + ["--mode direct --token 'your-gemini-api-key'"])
                proxy_cmd = " ".join(base_cmd_parts + ["--mode proxy --token 'your-aiproxy-token'"])
                export_cmd = " ".join(base_cmd_parts + ["--export-prompt"])
                
                print("💡 解决方案:")
                print(f"\n   选项 1: 直接传递 Gemini API Key (推荐)")
                print(f"   {direct_cmd_with_key}")
                print(f"\n   选项 2: 使用代理模式")
                print(f"   {proxy_cmd}")
                print(f"\n   选项 3: 导出提示词 (不消耗API配额)")
                print(f"   {export_cmd}")
                print(f"\n   选项 4: 设置环境变量")
                print(f"   $env:GEMINI_API_KEY='your-api-key'  # PowerShell")
                print(f"   {' '.join(base_cmd_parts + ['--mode direct'])}\n")
                sys.exit(1)
    
    # 设置模型
    model = args.model or "models/nano-banana-pro-preview"
    
    # 显示模式信息（导出模式除外）
    if not args.export_prompt:
        if args.mode == "proxy":
            print(f"[模式] AiProxy (bot.bigjj.click/aiproxy)")
        else:
            print(f"[模式] 直连 Gemini API")
        print(f"[模型] {model}")
    else:
        print(f"[导出模式] 准备提示词参数...")
    
    # 获取角色描述
    if args.description:
        description = args.description
    elif args.from_image:
        # 使用图片参考模式时，描述是可选的（会从图片分析获取）
        description = ""
        print("[INFO] 图片参考模式：将从图片中自动提取描述")
    else:
        print("\n请输入角色描述:")
        print("示例: 赛博朋克女骇客，霓虹灯外套，机械义肢")
        print("示例: 中世纪骑士，银色铠甲，红色披风")
        print("-" * 50)
        description = input("\n角色描述: ").strip()
        
        if not description:
            print("[错误] 描述不能为空")
            sys.exit(1)

    # 确定风格 - 使用新的风格预设系统
    from prompts.styles import get_style_preset, find_matching_style, get_style_help
    
    style = args.style
    active_preset = None  # 记录激活的预设
    
    # 风格参数映射表
    style_flags = {
        'photorealistic': args.photorealistic,
        'anime': args.anime,
        'ghibli': getattr(args, 'ghibli', False),
        'pixel': getattr(args, 'pixel', False),
        'minecraft': getattr(args, 'minecraft', False),
        'clay': getattr(args, 'clay', False),
        'plush': getattr(args, 'plush', False),
        'paper': getattr(args, 'paper', False),
        'cyberpunk': getattr(args, 'cyberpunk', False),
        'fantasy': getattr(args, 'fantasy', False),
        'watercolor': getattr(args, 'watercolor', False),
        'oil': getattr(args, 'oil', False),
        '3d-toon': getattr(args, 'toon3d', False),
        'comic': getattr(args, 'comic', False),
        'minimal': getattr(args, 'minimal', False),
        'lowpoly': getattr(args, 'lowpoly', False),
    }
    
    # 查找激活的风格预设
    for preset_name, is_active in style_flags.items():
        if is_active:
            active_preset = get_style_preset(preset_name)
            if active_preset:
                preset_prompt = active_preset.prompt
                style = f"{preset_prompt}, {style}" if style else preset_prompt
                print(f"[预设风格] {active_preset.name.upper()} ({active_preset.description})")
                break
    
    # 如果没有预设激活，尝试从 --style 参数匹配预设
    if not active_preset and style:
        matched = find_matching_style(style)
        if matched:
            active_preset = matched
            style = matched.prompt
            print(f"[匹配风格] {matched.name.upper()} ({matched.description})")
    
    # 如果仍然没有风格，使用自动匹配
    if not style:
        desc_lower = description.lower()
        if "cyberpunk" in desc_lower or "neon" in desc_lower or "mech" in desc_lower:
            active_preset = get_style_preset("cyberpunk")
            style = active_preset.prompt if active_preset else "Cyberpunk sci-fi style"
        elif "knight" in desc_lower or "magic" in desc_lower or "fantasy" in desc_lower or "dragon" in desc_lower:
            active_preset = get_style_preset("fantasy")
            style = active_preset.prompt if active_preset else "High fantasy style"
        elif "anime" in desc_lower or "manga" in desc_lower:
            active_preset = get_style_preset("anime")
            style = active_preset.prompt if active_preset else "Anime style"
        elif "pixel" in desc_lower or "8bit" in desc_lower or "retro" in desc_lower:
            active_preset = get_style_preset("pixel")
            style = active_preset.prompt if active_preset else "Pixel art style"
        else:
            style = "Cinematic character design"
        print(f"[自动匹配风格] {style}")
    else:
        if not active_preset:
            print(f"[自定义风格] {style}")

    # 自动增强提示词 (根据风格预设选择合适的增强词)
    if active_preset:
        enhancements = active_preset.enhancements
    else:
        # 回退：根据关键词检测
        style_lower = style.lower() if style else ""
        non_realistic_keywords = ["anime", "manga", "cartoon", "2d", "cel", "ghibli", "pixel", 
                                   "minecraft", "clay", "plush", "paper", "comic", "minimal", 
                                   "lowpoly", "watercolor", "oil"]
        if any(kw in style_lower for kw in non_realistic_keywords):
            enhancements = ", detailed, high resolution, masterpiece, sharp, clean"
        else:
            enhancements = ", detailed face, delicate features, high resolution, 8k, masterpiece, photorealistic, sharp focus"
    
    if "face" not in description.lower() and "feature" not in description.lower():
         description += enhancements
         print(f"[提示词增强] {enhancements.strip(', ')}")
    
    # =========================================================================
    # 从参考图片生成多视角图
    # =========================================================================
    if args.from_image:
        image_path = Path(args.from_image)
        
        # 如果直接路径不存在，尝试在 reference_images/ 文件夹中查找
        if not image_path.exists():
            ref_folder = Path("reference_images")
            alt_path = ref_folder / args.from_image
            if alt_path.exists():
                image_path = alt_path
                print(f"[INFO] 在 reference_images/ 中找到图片")
            else:
                print(f"[ERROR] 图片不存在: {args.from_image}")
                print(f"        也没有在 reference_images/{args.from_image} 找到")
                print(f"\n请将图片放入 reference_images/ 文件夹，或提供完整路径")
                sys.exit(1)
        
        # =====================================================================
        # 预处理：去除背景让主体更突出
        # =====================================================================
        if args.preprocess:
            print(f"\n[预处理] 去除背景，突出主体...")
            print(f"[模型] {args.preprocess_model}")
            
            try:
                from image_processor import remove_background
                import cv2
                import numpy as np
                
                # 读取图片
                img = cv2.imread(str(image_path))
                if img is None:
                    print(f"[ERROR] 无法读取图片: {image_path}")
                    sys.exit(1)
                
                # 去除背景
                processed = remove_background(img, model_name=args.preprocess_model)
                
                # 保存预处理后的图片
                preprocess_dir = Path(args.output) / "preprocessed"
                preprocess_dir.mkdir(parents=True, exist_ok=True)
                preprocessed_path = preprocess_dir / f"{image_path.stem}_preprocessed.png"
                cv2.imwrite(str(preprocessed_path), processed)
                
                print(f"[预处理完成] 保存到: {preprocessed_path}")
                
                # 使用预处理后的图片
                image_path = preprocessed_path
                
            except ImportError as e:
                print(f"[WARNING] 预处理依赖缺失: {e}")
                print("[INFO] 跳过预处理，使用原图继续")
            except Exception as e:
                print(f"[WARNING] 预处理失败: {e}")
                print("[INFO] 跳过预处理，使用原图继续")
        
        args.from_image = str(image_path)  # 更新为实际路径（可能已被预处理）
    
    # 调用生成器
    if args.mode == "proxy":
        from aiproxy_client import generate_character_multiview, analyze_image_for_character as analyze_via_proxy
        
        # 处理图像参考模式（代理模式）
        if args.from_image and not args.strict:
            print(f"\\n[图片参考模式] 分析图片: {args.from_image}")
            print("="*50)
            
            user_guidance = args.description if args.description else None
            
            extracted_description = analyze_via_proxy(
                image_path=args.from_image,
                token=args.token,
                user_guidance=user_guidance
            )
            
            if extracted_description:
                print(f"\n[提取的描述]")
                print("-"*50)
                print(extracted_description[:500] + "..." if len(extracted_description) > 500 else extracted_description)
                print("-"*50)
                
                if args.description:
                    modification_note = f"\n\n**USER MODIFICATION REQUEST**: {args.description}\nApply this modification to the character description above."
                    description = extracted_description + modification_note
                    print(f"\n[用户修改需求已融入] {args.description}")
                else:
                    description = extracted_description
            else:
                print("[WARNING] 图片分析失败，使用默认描述")
                if not args.description:
                    print("[ERROR] 图片分析失败且未提供描述，无法继续")
                    sys.exit(1)
        elif args.from_image and args.strict:
            print(f"\n[严格复制模式] 跳过图片分析，100%基于原图生成")
            description = "(strict mode - no description needed)"
        
        # 确定是否使用图片参考模式
        ref_image_path = args.from_image if args.from_image else None
        
        # 确定视角模式
        view_mode = f"{args.views}-view"  # "4" -> "4-view"
        custom_views = args.custom_views
        if custom_views:
            view_mode = "custom"
            
        # 只有在标准 4 视图且没有自定义视角时，才使用"图片参考专用提示词"
        # 否则（如 8 视图或自定义），我们使用通用多视角模板来强制生成指定视角
        use_ref_prompt = bool(args.from_image) and view_mode == "4-view" and not custom_views
        
        use_strict = bool(args.strict and args.from_image)  # 严格模式需要配合 --from-image
        
        if use_strict:
            print("[MODE] 严格复制模式 (100% 基于原图)")
        
        print(f"[视角模式] {view_mode}")
        if custom_views:
            print(f"[自定义视角] {custom_views}")
        
        result = generate_character_multiview(
            character_description=description,
            token=args.token,
            output_dir=args.output,
            auto_cut=not args.no_cut,
            model=model,
            style=style,
            reference_image_path=ref_image_path,
            use_image_reference_prompt=use_ref_prompt,
            use_strict_mode=use_strict,
            resolution=args.resolution,
            view_mode=view_mode,
            custom_views=custom_views,
            use_negative_prompt=not args.no_negative,
            negative_categories=args.negative_categories,
            subject_only=args.subject_only,
            with_props=args.with_props,
            export_prompt=args.export_prompt
        )
    else:
        # Gemini 直连模式 - 完整支持所有参数
        from gemini_generator import generate_character_views, analyze_image_for_character
        
        # 处理图像参考模式
        ref_image_path = None
        if args.from_image:
            ref_image_path = args.from_image
            
            # 如果不是严格模式，先分析图像（导出模式除外）
            if not args.strict and not args.export_prompt:
                print(f"\n[图片分析] 使用 Gemini 分析图像: {args.from_image}")
                print("="*50)
                
                user_guidance = args.description if args.description else None
                
                extracted_description = analyze_image_for_character(
                    image_path=args.from_image,
                    api_key=args.token,
                    user_guidance=user_guidance,
                    original_args=args
                )
                
                if extracted_description:
                    print(f"\n[提取的描述]")
                    print("-"*50)
                    print(extracted_description[:500] + "..." if len(extracted_description) > 500 else extracted_description)
                    print("-"*50)
                    
                    if args.description:
                        modification_note = f"\n\n**USER MODIFICATION REQUEST**: {args.description}\nApply this modification to the character description above."
                        description = extracted_description + modification_note
                        print(f"\n[用户修改需求已融入] {args.description}")
                    else:
                        description = extracted_description
                else:
                    if not args.description:
                        print("\n[ERROR] 图片分析失败且未提供描述，无法继续")
                        sys.exit(1)
                    else:
                        print(f"[INFO] 将使用提供的描述继续: {args.description}")
                        description = args.description
            elif args.export_prompt and not args.strict:
                # 导出模式且非严格模式：跳过分析，使用默认或用户提供的描述
                print(f"\n[导出模式] 跳过图片分析")
                if args.description:
                    description = args.description
                    print(f"[描述] {args.description}")
                else:
                    description = "Character extracted from the reference image"
                    print(f"[默认描述] {description}")
                    print(f"[提示] 建议使用 --strict 模式或提供描述以获得更好效果")
            else:
                # 严格模式：跳过分析
                print(f"\n[严格复制模式] 跳过图片分析，100% 基于原图生成")
                description = "(strict mode - no description needed)"
        
        # 确定视角模式
        view_mode = f"{args.views}-view"
        custom_views = args.custom_views
        if custom_views:
            view_mode = "custom"
        
        # 获取负面提示词
        negative_prompt = None
        if not args.no_negative:
            negative_prompt = config.get_negative_prompt(args.negative_categories)
        
        # ===================================================================
        # 迭代 360 度模式
        # ===================================================================
        if args.iterative_360:
            result = _iterative_360_generation(
                initial_reference_image=ref_image_path,
                character_description=description,
                api_key=args.token,
                model_name=model,
                output_dir=args.output,
                auto_cut=not args.no_cut,
                style=style,
                negative_prompt=negative_prompt,
                use_strict_mode=args.strict,
                resolution=args.resolution,
                original_args=args,
                export_prompt=args.export_prompt,
                subject_only=args.subject_only,
                with_props=args.with_props
            )
        else:
            # 标准多视角模式
            result = generate_character_views(
                character_description=description,
                api_key=args.token,
                model_name=model,
                output_dir=args.output,
                auto_cut=not args.no_cut,
                style=style,
                view_mode=view_mode,  # 使用已计算的 view_mode（支持 custom）
                custom_views=custom_views,  # 使用已计算的 custom_views
                negative_prompt=negative_prompt,
                reference_image_path=ref_image_path,
                use_strict_mode=args.strict,
                resolution=args.resolution,
                original_args=args,
                export_prompt=args.export_prompt,
                subject_only=args.subject_only,
                with_props=args.with_props
            )
    
    # =========================================================================
    # 视角验证与自动补全
    # =========================================================================
    if result and (args.auto_complete or args.validate_only):
        print("\n" + "═" * 50)
        print("🔍 启动视角验证...")
        print("═" * 50)
        
        try:
            from view_validator import ViewValidator
            
            # 从生成结果中提取资源 ID
            result_path = Path(result)
            asset_id = result_path.stem  # 如 294829fb-6da7-45a7-bbfe-5318999084c7
            
            # 确定期望的视角列表
            if custom_views:
                expected_views = custom_views
            elif args.views == "8":
                expected_views = ["front", "front_right", "right", "back", "back_left", "left", "top", "bottom"]
            elif args.views == "6":
                expected_views = ["front", "front_right", "right", "back", "back_left", "left"]
            else:  # 默认 4 视角
                expected_views = ["front", "right", "back", "left"]
            
            print(f"  └─ 资源 ID: {asset_id}")
            print(f"  └─ 期望视角: {expected_views}")
            print(f"  └─ 验证模式: {args.mode.upper()}")
            
            # 创建验证器 (遵守 proxy/direct 设置)
            validator = ViewValidator(
                api_key=args.token,
                verbose=True,
                mode=args.mode,
                proxy_base_url=None  # 使用默认的 AIPROXY_BASE_URL
            )
            
            if args.validate_only:
                # 仅验证模式
                validation = validator.validate(result, expected_views)
                
                print("\n" + "-" * 40)
                print("📊 验证结果:")
                print("-" * 40)
                print(f"  检测到的视角: {validation.detected_views}")
                print(f"  期望的视角: {validation.expected_views}")
                print(f"  缺失的视角: {validation.missing_views}")
                print(f"  重复的视角: {validation.duplicate_views}")
                print(f"  验证通过: {'✅ 是' if validation.is_complete else '❌ 否'}")
                
                if validation.suggestions:
                    print("\n💡 建议:")
                    for suggestion in validation.suggestions:
                        print(f"  - {suggestion}")
            else:
                # 自动补全模式
                # 优先使用切割后的 front 视图作为参考图，保证角色一致性
                # 如: test_images/294829fb-xxx_front.png
                front_reference = None
                output_path = Path(args.output)
                for ext in ['.png', '.jpg', '.webp']:
                    front_path = output_path / f"{asset_id}_front{ext}"
                    if front_path.exists():
                        front_reference = str(front_path)
                        print(f"  └─ 参考图: {front_path.name} (切割后的 front 视图)")
                        break
                
                if not front_reference:
                    # 回退到用户指定的参考图或原始生成图
                    front_reference = args.from_image if args.from_image else result
                    print(f"  └─ 参考图: {Path(front_reference).name} (未找到 front 视图)")
                
                completion_result = validator.validate_and_complete(
                    image_path=result,
                    expected_views=expected_views,
                    reference_image=front_reference,
                    style=style,
                    output_dir=args.output,
                    max_iterations=args.max_completion_retries,
                    asset_id=asset_id
                )
                
                print("\n" + "-" * 40)
                print("📊 补全结果:")
                print("-" * 40)
                print(f"  资源 ID: {completion_result.get('asset_id', asset_id)}")
                print(f"  状态: {completion_result['final_status']}")
                print(f"  迭代次数: {completion_result['iterations']}")
                print(f"  验证通过: {'✅ 是' if completion_result['validation_passed'] else '❌ 否'}")
                
                if completion_result['generated_panels']:
                    print("\n📁 生成的补全面板:")
                    for panel in completion_result['generated_panels']:
                        print(f"  - {panel['view']}: {panel['path']}")
                
                if completion_result['missing_views']:
                    print(f"\n⚠️ 仍缺失的视角: {completion_result['missing_views']}")
                    print("   提示: 可以手动使用 --custom-views 单独生成这些视角")
                    
        except ImportError as e:
            print(f"\n" + "─" * 50)
            print("⚠️ 视角验证模块加载失败")
            print("─" * 50)
            print(f"  原因: {e}")
            print("  解决: pip install google-generativeai Pillow requests")
            print("\n  (2D 生成已完成，仅验证功能不可用)")
        except Exception as e:
            error_msg = str(e)
            print(f"\n" + "─" * 50)
            print("⚠️ 视角验证失败")
            print("─" * 50)
            
            # 根据错误类型给出友好提示
            if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
                print("  原因: API Key 无效或未配置")
                if args.mode == "proxy":
                    print("  解决: 检查 --token 参数或 AiProxy 服务配置")
                else:
                    print("  解决: 设置有效的 GEMINI_API_KEY 环境变量")
            elif "quota" in error_msg.lower() or "rate" in error_msg.lower():
                print("  原因: API 配额耗尽或请求频率过高")
                print("  解决: 稍后重试，或升级 API 配额")
            elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
                print("  原因: 网络连接超时")
                print("  解决: 检查网络连接，或稍后重试")
            elif "permission" in error_msg.lower() or "403" in error_msg:
                print("  原因: 权限不足")
                print("  解决: 检查 API Key 是否有正确的权限")
            else:
                # 通用错误，显示简化信息
                print(f"  错误: {error_msg[:200]}")
                if len(error_msg) > 200:
                    print("  (错误信息已截断)")
            
            print("\n  (2D 生成已完成，仅验证功能出错)")
            print("  提示: 可稍后使用 validate_views.py 单独验证")
    
    if result:
        print("\n" + "═" * 50)
        print("✅ 2D 生成完成!")
        print("═" * 50)
        
        output_path = Path(args.output)
        master_path = Path(result)
        
        # 确定 Front 视图路径 (即使没有切割，result也是master图片)
        # 如果 auto_cut 为 True (args.no_cut 为 False)，则会有 _front.png
        front_img = None
        if not args.no_cut:
            front_img = master_path.parent / (master_path.stem + "_front.png")
        
        # 1. 自动预览
        if args.preview:
            import subprocess
            print("\n[INFO] 打开预览...")
            try:
                if sys.platform == "darwin": # macOS
                    subprocess.run(["open", str(master_path)])
                elif sys.platform == "win32":
                    os.startfile(str(master_path))
                else: # linux
                    subprocess.run(["xdg-open", str(master_path)])
            except Exception as e:
                print(f"[WARNING] 无法打开预览: {e}")

        # 2. 自动转 3D
        if args.to_3d:
            if not front_img or not front_img.exists():
                print("\n[ERROR] 无法找到 Front 视图进行 3D 生成 (请确保未设置 --no-cut 且切割成功)")
            else:
                print("\n" + "═" * 50)
                print("🚀 启动 3D 生成流水线 (Hunyuan3D Multi-View)...")
                print("═" * 50)
                
                # 调用 scripts/reconstructor.py
                reconstructor_script = script_dir / "reconstructor.py"
                cmd = [
                    sys.executable,
                    str(reconstructor_script),
                    str(front_img),
                    "--algo", args.algo,
                    "--quality", args.quality,
                    "--output_dir", str(Path("outputs"))
                ]
                
                # 添加几何模型Only选项 (跳过纹理生成，速度快很多)
                if getattr(args, 'geometry_only', False):
                    cmd.append("--no-texture")
                
                # 添加姿势控制 (仅 hunyuan3d-omni 支持)
                if args.algo == "hunyuan3d-omni" and args.pose:
                    cmd.extend(["--control-type", "pose", "--control-input", str(args.pose)])
                
                try:
                    import subprocess
                    subprocess.run(cmd, check=True)
                    print("\n[SUCCESS] 全流程完成！")
                    
                    # 尝试打开 3D 结果 (Hunyuan3D output, _front is removed from filename)
                    output_name = front_img.stem.replace('_front', '')
                    glb_path = Path("outputs/hunyuan3d") / (output_name + ".glb")
                    if args.preview and glb_path.exists():
                         if sys.platform == "darwin":
                            subprocess.run(["open", str(glb_path)])
                            
                except subprocess.CalledProcessError as e:
                    print(f"\n[ERROR] 3D 生成失败 (Exit Code {e.returncode})")
                except Exception as e:
                    print(f"\n[ERROR] 3D 生成异常: {e}")

        # 列出生成的文件 - 仅列出当前生成的 ID 相关文件
        if output_path.exists():
            # result 是 master 图片的绝对路径，我们只需要 ID (文件名 stem)
            asset_id_prefix = master_path.stem
            
            # 使用 glob 匹配 ID 开头的所有文件
            files = list(output_path.glob(f"{asset_id_prefix}*.*"))
            
            if files:
                print("\n生成的文件列表:")
                # 按名称排序，确保列表整洁
                for f in sorted(files):
                     print(f"  📷 {f.name}")
        
    elif args.export_prompt:
        # 导出模式下，返回 None 是正常的行为（已导出提示词）
        print("\n✅ 提示词导出完成！")
        print("   您现在可以将提示词复制到 Gemini App 中使用")
        sys.exit(0)
    else:
        print("\n❌ 生成失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
