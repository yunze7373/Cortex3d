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
        description="🎨 Cortex3d Character Generator - AI多视角角色图像生成与3D转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  基础生成:
    %(prog)s "赛博朋克女战士" --style cyberpunk --views 8
    
  图像参考:
    %(prog)s --input photo.jpg --style anime --to-3d
    
  换装功能:
    %(prog)s --input model.jpg --wear dress.png --accessory hat.png
    
  高质量输出:
    %(prog)s "魔法师" --quality ultra --resolution 4K --pro
    
  本地模式:
    %(prog)s "机器人" --mode local --style pixel
    
环境变量:
  AIPROXY_TOKEN     - AiProxy服务令牌 (proxy模式)
  GEMINI_API_KEY    - Google Gemini API密钥 (direct模式) 
  ZIMAGE_URL        - 本地Z-Image服务地址 (local模式)
        """
    )
    
    # =========================================================================
    # 📝 基础参数组 (Basic Arguments)
    # =========================================================================
    basic_group = parser.add_argument_group('📝 基础设置', '基本生成参数和认证设置')
    
    basic_group.add_argument(
        "description",
        nargs="?",
        help="角色描述文本，如 '赛博朋克女战士' 或 '可爱的机器人'"
    )
    
    basic_group.add_argument(
        "--mode",
        choices=["proxy", "direct", "local"],
        default="proxy",
        metavar="MODE",
        help="生成模式 (默认: proxy)\n"
             "proxy  - AiProxy云服务 (推荐)\n"
             "direct - 直连Gemini API\n"  
             "local  - 本地Z-Image服务"
    )
    
    basic_group.add_argument(
        "--token", "--auth",
        dest="token",
        metavar="TOKEN",
        help="认证令牌 (自动选择环境变量)\n"
             "proxy模式: AIPROXY_TOKEN\n"
             "direct模式: GEMINI_API_KEY"
    )
    
    basic_group.add_argument(
        "--output", "-o",
        default="test_images",
        metavar="DIR",
        help="输出目录 (默认: test_images)"
    )
    
    basic_group.add_argument(
        "--preview",
        action="store_true",
        help="生成后自动预览结果"
    )
    
    # =========================================================================
    # 📥 输入源参数组 (Input Sources)
    # =========================================================================
    input_group = parser.add_argument_group('📥 输入源设置', '指定输入图像和数据源')
    
    input_group.add_argument(
        "--input", "--from-image",
        dest="from_image",
        metavar="IMAGE",
        help="参考图像路径，支持从图像提取角色特征\n"
             "示例: photo.jpg 或 reference_images/model.png"
    )
    
    input_group.add_argument(
        "--from-id",
        metavar="ID", 
        help="使用已存在的图像ID跳过2D生成直接进行3D转换\n"
             "示例: a7af1af9-a592-4499-a456-2bea8428fe49"
    )
    
    input_group.add_argument(
        "--strict",
        action="store_true",
        help="严格复制模式: 100%%基于参考图像生成，无AI创意\n"
             "适用于精确复制现有角色外观"
    )
    
    input_group.add_argument(
        "--random",
        action="store_true",
        help="随机生成模式: 无需参考图，AI自由创作随机角色\n"
             "生成符合多视角标准的全新角色图像\n"
             "示例: --random --views 4 --style anime"
    )
    
    input_group.add_argument(
        "--random-theme",
        metavar="THEME",
        help="随机模式的主题提示 (可选)\n"
             "示例: --random --random-theme '科幻战士'"
    )
    
    input_group.add_argument(
        "--random-character",
        action="store_true",
        help="随机人物+固定衣服: 配合 --composite-images 使用\n"
             "人物由AI随机生成，穿上指定的衣服图片\n"
             "示例: --random-character --composite-images dress.png"
    )
    
    input_group.add_argument(
        "--random-clothing",
        metavar="STYLE",
        help="固定人物+随机衣服: 配合 --from-image 使用\n"
             "人物来自参考图，衣服由AI根据描述随机生成\n"
             "示例: --from-image model.png --random-clothing '时尚连衣裙'"
    )
    
    # =========================================================================
    # 👁️ 视角参数组 (View Configuration)  
    # =========================================================================
    view_group = parser.add_argument_group('👁️ 视角配置', '控制多视角生成的视角数量和方向')
    
    view_group.add_argument(
        "--views", "-v",
        choices=["4", "6", "8"],
        default="4",
        metavar="N",
        help="标准视角数量 (默认: 4)\n"
             "4 - 前后左右四视角\n"
             "6 - 增加前右、后左45度角\n"
             "8 - 增加顶部、底部视角"
    )
    
    view_group.add_argument(
        "--custom-views",
        nargs="+",
        metavar="VIEW",
        help="自定义视角列表 (覆盖--views设置)\n"
             "可选: front, front_right, right, back, back_left, left, top, bottom\n"
             "示例: --custom-views front right back"
    )
    
    view_group.add_argument(
        "--iterative-360",
        choices=["4", "6", "8"],
        metavar="N",
        help="迭代360度模式，按顺序生成提高一致性\n"
             "每个视图使用前一个作为参考，需配合--input使用"
    )
    
    # =========================================================================
    # ✨ 质量参数组 (Quality Settings)
    # =========================================================================
    quality_group = parser.add_argument_group('✨ 质量设置', '控制生成质量和模型选择')
    
    quality_group.add_argument(
        "--resolution", "--res",
        dest="resolution",
        choices=["1K", "2K", "4K"],
        default="2K", 
        help="图像分辨率 (默认: 2K)\n"
             "1K - 快速生成\n"
             "2K - 平衡质量\n"
             "4K - 高质量但较慢"
    )
    
    quality_group.add_argument(
        "--model", "--engine",
        dest="model",
        metavar="MODEL",
        help="指定生成模型 (默认: gemini-3.1-flash-image-preview)\n"
             "留空使用 Nano Banana 2 推荐模型"
    )
    
    quality_group.add_argument(
        "--pro", "--high-quality",
        dest="pro", 
        action="store_true",
        help="启用Pro模型获得更高保真 (gemini-3-pro-image-preview)\n"
             "速度较慢但效果更好"
    )
    
    quality_group.add_argument(
        "--aspect-ratio", "--ratio",
        dest="aspect_ratio",
        choices=["1:1", "3:2", "2:3", "16:9", "9:16", "4:3", "3:4"],
        metavar="RATIO",
        help="图像宽高比\n"
             "默认: 多视角用3:2，合成图用1:1"
    )
    
    # =========================================================================
    # 🎨 风格参数组 (Style Configuration)
    # =========================================================================
    style_group = parser.add_argument_group('🎨 风格配置', '选择角色的艺术风格和视觉效果')
    
    style_group.add_argument(
        "--style",
        metavar="STYLE",
        help="自定义风格描述或预设名称\n"
             "示例: 'cyberpunk' 或 'watercolor painting style'"
    )
    
    # 风格预设 - 基础类型
    style_basic = style_group.add_mutually_exclusive_group()
    style_basic.add_argument("--photorealistic", "--real", dest="photorealistic", action="store_true", help="写实摄影风格")
    style_basic.add_argument("--anime", action="store_true", help="日式动漫风格")
    style_basic.add_argument("--comic", "--marvel", dest="comic", action="store_true", help="美式漫画风格")
    style_basic.add_argument("--3d-toon", "--pixar", dest="toon3d", action="store_true", help="3D卡通风格")
    
    # 风格预设 - 艺术类型
    style_art = style_group.add_mutually_exclusive_group()
    style_art.add_argument("--watercolor", action="store_true", help="水彩画风格")
    style_art.add_argument("--oil", "--oil-painting", dest="oil", action="store_true", help="油画风格")
    style_art.add_argument("--ghibli", action="store_true", help="宫崎骏/吉卜力风格")
    style_art.add_argument("--minimal", "--flat", dest="minimal", action="store_true", help="极简扁平风格")
    
    # 风格预设 - 游戏/数字类型  
    style_game = style_group.add_mutually_exclusive_group()
    style_game.add_argument("--pixel", action="store_true", help="像素艺术风格")
    style_game.add_argument("--minecraft", "--voxel", dest="minecraft", action="store_true", help="体素方块风格")
    style_game.add_argument("--lowpoly", action="store_true", help="低多边形3D风格")
    
    # 风格预设 - 材质类型
    style_material = style_group.add_mutually_exclusive_group()
    style_material.add_argument("--clay", "--claymation", dest="clay", action="store_true", help="粘土动画风格")
    style_material.add_argument("--plush", "--felt", dest="plush", action="store_true", help="毛绒玩具风格")
    style_material.add_argument("--paper", "--papercraft", dest="paper", action="store_true", help="纸质工艺风格")
    
    # 风格预设 - 主题类型
    style_theme = style_group.add_mutually_exclusive_group()
    style_theme.add_argument("--cyberpunk", "--neon", dest="cyberpunk", action="store_true", help="赛博朋克风格")
    style_theme.add_argument("--fantasy", "--medieval", dest="fantasy", action="store_true", help="奇幻中世纪风格")
    
    style_group.add_argument(
        "--list-styles",
        action="store_true",
        help="列出所有可用风格预设并退出"
    )
    
    
    # =========================================================================
    # 🚀 3D转换参数组 (3D Conversion)
    # =========================================================================
    d3_group = parser.add_argument_group('🚀 3D转换设置', '控制3D模型生成和质量')
    
    d3_group.add_argument(
        "--to-3d", "--3d",
        dest="to_3d",
        action="store_true",
        help="生成2D图像后自动转换为3D模型"
    )
    
    d3_group.add_argument(
        "--algo", "--algorithm",
        dest="algo",
        choices=["hunyuan3d", "hunyuan3d-2.1", "hunyuan3d-omni", "trellis", "trellis2"],
        default="hunyuan3d",
        metavar="ALGO",
        help="3D重建算法 (默认: hunyuan3d)\n"
             "hunyuan3d      - 标准版，速度快\n"
             "hunyuan3d-2.1  - 改进版，质量更好\n"
             "hunyuan3d-omni - 全能版，支持姿势控制\n"
             "trellis/trellis2 - 高质量重建"
    )
    
    d3_group.add_argument(
        "--3d-quality", "--quality",
        dest="quality",
        choices=["balanced", "high", "ultra"],
        default="high",
        help="3D生成质量 (默认: high)\n"
             "balanced - 快速生成\n"
             "high     - 平衡质量\n"
             "ultra    - 最佳质量但最慢"
    )
    
    d3_group.add_argument(
        "--geometry-only", "--fast-3d",
        dest="geometry_only",
        action="store_true", 
        help="仅生成几何体，跳过纹理生成 (大幅提升速度)"
    )
    
    d3_group.add_argument(
        "--pose",
        metavar="FILE",
        help="姿势控制文件 (仅hunyuan3d-omni支持)\n"
             "示例: poses/t_pose.json"
    )
    
    # =========================================================================
    # 👗 换装编辑参数组 (Wardrobe & Editing)
    # =========================================================================
    edit_group = parser.add_argument_group('👗 换装编辑设置', '服装更换和角色编辑功能')
    
    edit_group.add_argument(
        "--wear", "--outfit", 
        dest="wear_image",
        nargs="+",
        metavar="IMAGE",
        help="换装模式: 让角色穿上指定服装\n"
             "支持: --wear dress.png 或 --wear dress.png '说明文字'"
    )
    
    edit_group.add_argument(
        "--accessory", "--add-item",
        dest="accessory_images", 
        nargs="+",
        metavar="IMAGE",
        help="配饰模式: 为角色添加配饰\n"
             "示例: --accessory hat.png bag.png"
    )
    
    edit_group.add_argument(
        "--wear-strict",
        action="store_true",
        default=True,
        help="换装严格模式: 完全保留原角色特征 (默认开启)"
    )
    
    edit_group.add_argument(
        "--wear-model",
        choices=["flash", "pro"],
        default="flash",
        help="换装所用模型 (默认: flash)\n"
             "flash - 快速模式\n"
             "pro   - 高保真模式"
    )
    
    
    # =========================================================================
    # 🔧 处理参数组 (Processing Options)
    # =========================================================================
    proc_group = parser.add_argument_group('🔧 处理选项', '图像处理和输出控制')
    
    proc_group.add_argument(
        "--no-cut", "--no-crop",
        dest="no_cut",
        action="store_true",
        help="禁用自动切割功能"
    )
    
    proc_group.add_argument(
        "--no-rembg", "--keep-bg",
        dest="no_rembg",
        action="store_true",
        help="切割时跳过背景去除（保留道具/行李箱等）"
    )
    
    proc_group.add_argument(
        "--preprocess", "--clean",
        dest="preprocess",
        action="store_true",
        help="预处理输入图像: 去除背景提高AI生成质量"
    )
    
    proc_group.add_argument(
        "--preprocess-model",
        choices=["birefnet-general", "isnet-general-use", "u2net"],
        default="birefnet-general",
        metavar="MODEL",
        help="预处理(输入图片)的背景去除模型 (默认: birefnet-general)"
    )
    
    proc_group.add_argument(
        "--rembg-model", "--remove-bg-model",
        dest="rembg_model",
        choices=["birefnet-general", "isnet-general-use", "u2net"],
        default="isnet-general-use",
        metavar="MODEL",
        help="后处理(切割后)的背景去除模型。推荐选择: isnet-general-use(保守,保留道具), u2net(经典), birefnet-general(激进) (默认: isnet-general-use)"
    )
    
    proc_group.add_argument(
        "--subject-only", "--isolate",
        dest="subject_only",
        action="store_true",
        help="仅处理主体角色，移除所有背景对象"
    )
    
    proc_group.add_argument(
        "--with-props",
        nargs="+",
        metavar="PROP",
        help="指定要保留的道具/对象\n"
             "示例: --with-props bicycle guitar hat"
    )
    
    proc_group.add_argument(
        "--export-prompt", "--dry-run",
        dest="export_prompt",
        action="store_true",
        help="仅导出提示词不调用API (用于调试或手动使用)"
    )
    
    # =========================================================================
    # 🔍 智能验证参数组 (Smart Validation)
    # =========================================================================
    valid_group = parser.add_argument_group('🔍 智能验证设置', '自动检测和补全缺失视角')
    
    valid_group.add_argument(
        "--auto-complete", "--smart-fix",
        dest="auto_complete",
        action="store_true",
        help="自动验证并补全缺失的视角"
    )
    
    valid_group.add_argument(
        "--validate-only", "--check-only", 
        dest="validate_only",
        action="store_true",
        help="仅验证视角完整性，不进行补全"
    )
    
    valid_group.add_argument(
        "--max-retries",
        dest="max_completion_retries",
        type=int,
        default=3,
        metavar="N",
        help="自动补全的最大重试次数 (默认: 3)"
    )
    
    
    # =========================================================================
    # ⚙️ 高级参数组 (Advanced Settings)
    # =========================================================================
    advanced_group = parser.add_argument_group('⚙️ 高级设置', '专业用户和特殊用途的高级选项')
    
    # 本地服务设置
    local_sub = advanced_group.add_mutually_exclusive_group()
    local_sub.add_argument(
        "--local-url",
        metavar="URL",
        help="本地Z-Image服务地址 (默认: http://localhost:8199)"
    )
    
    advanced_group.add_argument(
        "--local-steps",
        type=int,
        default=9,
        metavar="N", 
        help="本地模型推理步数 (默认: 9)"
    )
    
    # API设置
    advanced_group.add_argument(
        "--analysis-api",
        choices=["auto", "proxy", "direct", "local"],
        default="auto",
        metavar="API",
        help="图像分析API选择 (默认: auto)\n"
             "auto   - 跟随--mode设置\n"
             "proxy  - 强制使用AiProxy\n"
             "direct - 强制直连Gemini\n"
             "local  - 跳过分析"
    )
    
    # 负面提示词控制
    neg_group = advanced_group.add_mutually_exclusive_group()
    neg_group.add_argument(
        "--no-negative",
        action="store_true",
        help="完全禁用负面提示词"
    )
    neg_group.add_argument(
        "--negative-categories",
        nargs="+",
        default=["anatomy", "quality", "layout"],
        choices=["anatomy", "quality", "layout"],
        metavar="CAT",
        help="负面提示词类别 (默认: anatomy quality layout)"
    )
    
    # 换装高级设置
    advanced_group.add_argument(
        "--wear-instruction",
        metavar="TEXT",
        help="自定义换装指令 (可选，默认自动生成)"
    )
    
    advanced_group.add_argument(
        "--wear-no-rembg",
        action="store_true", 
        help="跳过服装图片的背景去除预处理"
    )
    
    
    # =========================================================================
    # 🛠️ 编辑模式参数组 (Edit Modes) - P0高优先级功能
    # =========================================================================
    edit_mode_group = parser.add_argument_group('🛠️ 专业编辑模式', 'P0高优先级图像编辑和修复功能')
    
    # 编辑模式选择 (互斥)
    edit_mode_select = edit_mode_group.add_mutually_exclusive_group()
    
    edit_mode_select.add_argument(
        "--mode-edit",
        action="store_true",
        help="元素编辑模式: 添加/移除/修改角色元素"
    )
    
    edit_mode_select.add_argument(
        "--mode-refine", 
        action="store_true",
        help="细节修复模式: 修复面部/手部/姿势等问题"
    )
    
    edit_mode_select.add_argument(
        "--mode-style",
        action="store_true", 
        help="风格转换模式: 改变整体艺术风格"
    )
    
    edit_mode_select.add_argument(
        "--mode-composite",
        action="store_true",
        help="图像合成模式: 组合多张图片创建新场景"
    )
    
    edit_mode_select.add_argument(
        "--mode-preserve",
        action="store_true",
        help="高保真编辑模式: 保留关键细节的精确编辑"
    )

    edit_mode_select.add_argument(
        "--mode-extract",
        action="store_true",
        help="服装/道具提取模式: 提取图中人穿着的衣物或手持的道具"
    )
    
    # 编辑参数 (根据不同模式使用)
    edit_mode_group.add_argument(
        "--extract-props",
        action="store_true",
        help="提取服装饰品时也一并提取道具 (--mode-extract)"
    )
    edit_mode_group.add_argument(
        "--edit-elements",
        metavar="ACTION",
        help="编辑指令 (--mode-edit)\n"
             "格式: 'add:描述' 'remove:描述' 'modify:描述'\n"
             "示例: 'add:火焰翅膀'"
    )
    
    edit_mode_group.add_argument(
        "--from-edited", "--edit-source",
        dest="from_edited",
        metavar="IMAGE",
        help="编辑源图像路径"
    )
    
    edit_mode_group.add_argument(
        "--refine-details", "--fix-part",
        dest="refine_details",
        choices=["face", "hands", "pose", "eyes", "custom"],
        help="要修复的部位 (--mode-refine)"
    )
    
    edit_mode_group.add_argument(
        "--detail-issue", "--problem",
        dest="detail_issue",
        metavar="DESC",
        help="具体问题描述 (--mode-refine)\n"
             "示例: '左手有6根手指，需要改为5根'"
    )
    
    edit_mode_group.add_argument(
        "--from-refine", "--fix-source",
        dest="from_refine", 
        metavar="IMAGE",
        help="修复源图像路径"
    )
    
    # 风格转换参数
    edit_mode_group.add_argument(
        "--style-preset",
        choices=["anime", "cinematic", "oil-painting", "watercolor", "comic", "3d"],
        metavar="PRESET",
        help="风格预设 (--mode-style)"
    )
    
    edit_mode_group.add_argument(
        "--custom-style",
        metavar="DESC",
        help="自定义风格描述 (--mode-style)\n"
             "示例: 'impressionist Renaissance painting'"
    )
    
    edit_mode_group.add_argument(
        "--from-style", "--style-source",
        dest="from_style",
        metavar="IMAGE", 
        help="风格转换源图像路径"
    )
    
    edit_mode_group.add_argument(
        "--preserve-details",
        action="store_true",
        default=True,
        help="风格转换时保留原始细节 (默认: 开启)"
    )
    
    
    # 合成模式参数
    edit_mode_group.add_argument(
        "--composite-images",
        nargs="+",
        metavar="IMAGE",
        help="要合成的多张图片路径 (--mode-composite)\n"
             "示例: model.png dress.png hat.png"
    )
    
    edit_mode_group.add_argument(
        "--composite-instruction",
        metavar="TEXT",
        help="合成指令 (--mode-composite)\n"
             "示例: '让第二张图的人穿上第一张图的裙子'"
    )
    
    edit_mode_group.add_argument(
        "--composite-type",
        choices=["auto", "clothing", "accessory", "general"],
        default="auto",
        help="合成类型 (默认: auto)"
    )
    
    # 高保真编辑参数
    edit_mode_group.add_argument(
        "--preserve-image",
        metavar="IMAGE",
        help="主图片路径 (--mode-preserve)\n"
             "包含要保留细节的图片"
    )
    
    edit_mode_group.add_argument(
        "--preserve-element",
        metavar="IMAGE", 
        help="元素图片路径 (--mode-preserve)\n"
             "要添加的元素，如logo、配饰等"
    )
    
    edit_mode_group.add_argument(
        "--preserve-detail-desc",
        metavar="DESC",
        help="要保留的关键细节描述 (--mode-preserve)\n"
             "示例: '保持女性的面部特征完全不变'"
    )
    
    edit_mode_group.add_argument(
        "--preserve-instruction",
        metavar="TEXT",
        help="修改指令 (--mode-preserve)\n"
             "示例: '将logo添加到她的黑色T恤上'"
    )
    
    # 通用输出设置
    edit_mode_group.add_argument(
        "--edit-output-name",
        metavar="NAME",
        help="编辑输出文件名 (可选，默认自动生成)"
    )
    
    
    # =========================================================================
    # 🤖 智能助手参数组 (AI Assistant)
    # =========================================================================
    ai_group = parser.add_argument_group('🤖 智能助手', '通过AI对话自动生成最佳参数组合')
    
    ai_group.add_argument(
        "--ai-assistant", "--smart", "--interactive",
        dest="ai_assistant",
        action="store_true",
        help="启动高级智能对话助手，通过自然语言生成最佳参数组合"
    )
    
    ai_group.add_argument(
        "--smart-chat", "--chat",
        dest="smart_chat",
        action="store_true",
        help="启动简化智能助手，快速参数推荐和意图识别"
    )
    
    ai_group.add_argument(
        "--analyze-image", "--ai-analyze",
        type=str, metavar='IMAGE',
        dest="analyze_image",
        help="智能分析图像特征并推荐最佳参数配置"
    )
    
    ai_group.add_argument(
        "--quick-setup",
        choices=["beginner", "fast", "quality", "3d"],
        help="快速设置预设\n"
             "beginner - 新手友好设置\n"
             "fast     - 快速预览模式\n" 
             "quality  - 高质量模式\n"
             "3d       - 3D生成优化"
    )
    friendly_hint_shown = False
    for arg in sys.argv[1:]:
        if arg.startswith('--'):
            # 检查常见拼写错误
            if arg == '--view':
                print(f"\n[ERROR] 参数 '--view' 不存在")
                print(f"[提示] 您可能想使用 '--views' 或 '-v'")
                print(f"       示例: python scripts/generate_character.py --views 8\n")
                friendly_hint_shown = True
                break
            # 检查旧版参数提示
            elif arg in ['--from-image']:
                print(f"\n[提示] 参数 '{arg}' 仍然可用")
                print(f"       新版本推荐使用: '--input' (功能相同)\n")
                break
            elif arg in ['--geometry-only']:
                print(f"\n[提示] 参数 '{arg}' 仍然可用")  
                print(f"       新版本推荐使用: '--fast-3d' (功能相同)\n")
                break
            # 检查带数字的无效参数（如 --14, --360 等）
            elif len(arg) > 2 and arg[2:].replace('-', '').isdigit():
                print(f"\n[ERROR] 无效参数: '{arg}'")
                print(f"[提示] 要生成多视角图像，请使用以下选项:")
                print(f"       --views 8              # 标准多视角 (8个固定角度)")
                print(f"       --iterative-360 8      # 迭代360度 (8个连续角度，更好的一致性)\n")
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
    
    # 参数后处理 - 确保别名兼容性
    if hasattr(args, 'edit_output_name') and args.edit_output_name:
        # 将通用编辑输出名应用到具体的编辑模式
        if not hasattr(args, 'composite_output_name'):
            args.composite_output_name = args.edit_output_name
        if not hasattr(args, 'preserve_output_name'):
            args.preserve_output_name = args.edit_output_name
    
    # 确保 composite_output_name 总是存在
    if not hasattr(args, 'composite_output_name') or args.composite_output_name is None:
        args.composite_output_name = None  # 使用默认名称
    
    # 确保旧参数名的兼容性
    if not hasattr(args, 'custom_views'):
        args.custom_views = getattr(args, 'custom_views', None)
    if not hasattr(args, 'composite_smart_extract'):
        args.composite_smart_extract = True
    if not hasattr(args, 'composite_prompt_template'):
        args.composite_prompt_template = None
    
    
    # =========================================================================
    # 🤖 智能助手功能检查
    # =========================================================================
    
    # 高级智能助手
    if getattr(args, 'ai_assistant', False):
        print("\n🧠 启动高级智能对话助手...")
        try:
            from smart_assistant import AdvancedParameterAssistant
            assistant = AdvancedParameterAssistant()
            print(assistant.start_intelligent_conversation())
            
            while True:
                try:
                    user_input = input("\n🗣️ 请描述您的需求: ").strip()
                    
                    if not user_input:
                        continue
                        
                    if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                        print("\n👋 感谢使用Cortex3d智能助手！")
                        sys.exit(0)
                        
                    if user_input.lower() == 'restart':
                        assistant = AdvancedParameterAssistant()
                        print(assistant.start_intelligent_conversation())
                        continue
                        
                    response, continue_chat, command_args = assistant.process_natural_language_input(user_input)
                    
                    if continue_chat:
                        print(response)
                    else:
                        # 显示最终推荐
                        recommendation = response if isinstance(response, dict) else assistant._generate_smart_recommendation()
                        print(assistant.format_smart_recommendation(recommendation))
                        
                        # 询问是否执行
                        while True:
                            choice = input("\n🤔 是否立即执行推荐命令? (y/n/modify): ").lower()
                            if choice in ['y', 'yes', '是', '执行']:
                                print("\n✅ 请复制上面的命令到新终端执行，或按Ctrl+C退出助手后执行。")
                                sys.exit(0)
                            elif choice in ['n', 'no', '否', '不']:
                                print("\n📋 命令已生成，您可以稍后手动执行。")
                                sys.exit(0)
                            elif choice in ['modify', 'adjust', '修改', '调整']:
                                print("\n🔧 请描述您希望如何调整参数：")
                                break
                            else:
                                print("请输入 y/n/modify")
                        
                except KeyboardInterrupt:
                    print("\n\n👋 感谢使用智能助手！")
                    sys.exit(0)
                    
        except ImportError:
            print("❌ 找不到高级智能助手模块，请检查 smart_assistant.py 文件")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 智能助手出现错误: {e}")
            sys.exit(1)
    
    # 简化智能助手
    if getattr(args, 'smart_chat', False):
        print("\n🤖 启动简化智能助手...")
        try:
            from intelligent_assistant import IntelligentParameterAssistant
            assistant = IntelligentParameterAssistant()
            print(assistant.start_conversation())
            
            while True:
                try:
                    user_input = input("\n💬 您的回答: ").strip()
                    
                    if not user_input:
                        continue
                        
                    if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                        print("\n👋 感谢使用智能助手！")
                        sys.exit(0)
                        
                    response, continue_chat = assistant.analyze_user_input(user_input)
                    print(response)
                    
                    if not continue_chat:
                        print("\n✅ 智能助手配置完成！请复制上面的命令来执行。")
                        sys.exit(0)
                        
                except KeyboardInterrupt:
                    print("\n\n👋 感谢使用智能助手！")
                    sys.exit(0)
        except ImportError:
            print("❌ 智能助手模块未找到，请确保 intelligent_assistant.py 在 scripts 目录下")
            sys.exit(1)
    
    # 图像智能分析
    if getattr(args, 'analyze_image', None):
        print(f"\n🖼️ 开始智能分析图像: {args.analyze_image}")
        try:
            from smart_assistant import AdvancedParameterAssistant
            assistant = AdvancedParameterAssistant()
            
            # 分析图像并推荐参数
            if not Path(args.analyze_image).exists():
                print(f"❌ 图像文件不存在: {args.analyze_image}")
                sys.exit(1)
                
            print("🔍 正在分析图像特征...")
            
            # 模拟图像分析（实际可以集成计算机视觉模型）
            analysis_input = f"我有一张图片 {args.analyze_image}，请帮我分析并推荐最佳的角色生成参数"
            
            response, continue_chat, command_args = assistant.process_natural_language_input(analysis_input)
            
            if not continue_chat:
                recommendation = response if isinstance(response, dict) else assistant._generate_smart_recommendation()
                print("\n📊 图像分析完成！")
                print(assistant.format_smart_recommendation(recommendation))
                
                # 自动设置输入图像参数
                if hasattr(args, 'input_image'):
                    args.input_image = args.analyze_image
                
                choice = input("\n🤔 是否使用推荐参数继续生成? (y/n): ").lower()
                if choice not in ['y', 'yes', '是']:
                    sys.exit(0)
            
        except ImportError:
            print("❌ 找不到智能分析模块")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 图像分析失败: {e}")
            sys.exit(1)
    
    # =========================================================================
    # 🚀 快速设置预设
    # =========================================================================
    if getattr(args, 'quick_setup', None):
        print(f"\n🚀 应用快速设置: {args.quick_setup}")
        
        if args.quick_setup == "beginner":
            # 新手友好设置
            args.views = "4"
            args.resolution = "2K"
            args.preview = True
            if not hasattr(args, 'anime') or not args.anime:
                args.anime = True
            print("  ✅ 新手模式：4视角，2K分辨率，动漫风格，自动预览")
            
        elif args.quick_setup == "fast":
            # 快速预览模式
            args.views = "4"
            args.resolution = "1K"
            args.no_negative = True
            args.preview = True
            print("  ⚡ 快速模式：4视角，1K分辨率，无负面提示词，快速预览")
            
        elif args.quick_setup == "quality":
            # 高质量模式
            args.views = "8"
            args.resolution = "4K"
            args.pro = True
            args.auto_complete = True
            args.preview = True
            print("  💎 高质量模式：8视角，4K分辨率，Pro模型，智能补全")
            
        elif args.quick_setup == "3d":
            # 3D优化模式
            args.views = "8"
            args.resolution = "4K"
            args.to_3d = True
            args.algo = "hunyuan3d-2.1"
            args.quality = "high"
            args.auto_complete = True
            args.preview = True
            print("  🚀 3D模式：8视角，4K分辨率，HunYuan3D-2.1，高质量3D")
        
        print("────────────────────────────────────────")
    
    # 根据模式自动设置token(如果未提供)
    if args.token is None:
        if args.mode == "proxy":
            args.token = os.environ.get("AIPROXY_TOKEN")
        elif args.mode == "direct":
            args.token = os.environ.get("GEMINI_API_KEY")
        # local 模式不需要 token
    
    # Banner 显示
    try:
        print("""
╔══════════════════════════════════════════════════════════════════╗
║                    🎨 Cortex3d 角色生成器 v2.0                     ║
║            AI多视角图像生成 → 智能切割 → 3D建模 → 换装编辑            ║
║                                                                  ║
║  💡 使用提示: --help 查看完整参数  --list-styles 查看所有风格        ║
╚══════════════════════════════════════════════════════════════════╝
        """)
    except UnicodeEncodeError:
        # 在某些终端中使用 ASCII 艺术代替
        print("""
=================================================================
                 Cortex3d Character Generator v2.0
   AI Multi-view Generation -> Smart Cropping -> 3D Modeling -> Wardrobe Editing
   
   Tips: Use --help for full parameters  --list-styles for all styles
=================================================================
        """)
    
    # 显示当前配置概览
    print(f"🔧 模式: {args.mode.upper()}")
    if getattr(args, 'random', False):
        random_theme = getattr(args, 'random_theme', None)
        if random_theme:
            print(f"🎲 随机生成: 主题 '{random_theme}'")
        else:
            print(f"🎲 随机生成: AI自由创作")
    elif getattr(args, 'random_character', False):
        print(f"🎲 随机人物: AI生成人物 + 指定衣服")
    elif getattr(args, 'random_clothing', None):
        print(f"🎲 随机衣服: 指定人物 + AI生成 '{args.random_clothing}'")
    elif args.from_image:
        print(f"📥 输入: {args.from_image}")
    if args.description:
        print(f"📝 描述: {args.description[:50]}{'...' if len(args.description) > 50 else ''}")
    
    style_info = []
    for style_attr in ['photorealistic', 'anime', 'pixel', 'cyberpunk', 'ghibli', 'clay', 'watercolor', 'oil']:
        if hasattr(args, style_attr) and getattr(args, style_attr):
            style_info.append(style_attr)
    if args.style:
        style_info.append(f"custom({args.style[:20]})")
    if style_info:
        print(f"🎨 风格: {', '.join(style_info)}")
    
    print(f"👁️  视角: {args.views}视角" + (f" (迭代360°)" if args.iterative_360 else ""))
    print(f"📐 分辨率: {args.resolution}")
    
    if args.to_3d:
        print(f"🚀 3D转换: {args.algo} ({args.quality}质量)")
    
    print("─" * 65)
    
    # =========================================================================
    # 列出所有可用风格预设
    # =========================================================================
    if getattr(args, 'list_styles', False):
        from prompts.styles import STYLE_PRESETS, list_all_styles
        
        print("\n🎨 可用风格预设:")
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
        print("   python scripts/generate_character.py --input img.png --pixel")
        print("   python scripts/generate_character.py --input img.png --style minecraft") 
        print("   python scripts/generate_character.py --input img.png --ghibli --custom-views front left")
        print("   python scripts/generate_character.py 'warrior' --cyberpunk --to-3d")
        print("")
        sys.exit(0)
    
    # =========================================================================
    # 👗 换装预处理 (--wear / --accessory)
    # 类似 --anime 一样简单使用，作为预处理步骤
    # 换装完成后自动继续多视图生成流程
    # =========================================================================
    if args.wear_image or args.accessory_images:
        # Local 模式现在支持换装（使用 Z-Image 的 img2img 功能）
        if args.mode == "local":
            print("\n" + "=" * 60)
            print("📌 Local 模式换装 (使用 Z-Image img2img)")
            print("=" * 60)
            print("  Z-Image 将使用图生图方式进行换装处理")
            print("  注意: 效果可能与云端 API 有所不同")
            print("=" * 60)
        
        print("\n" + "═"*60)
        print("👗 换装预处理 (Wardrobe Preprocessing)")
        print("═"*60)
        
        # 导入换装模块
        try:
            from prompts.wardrobe import build_wardrobe_prompt, detect_wardrobe_task, get_wardrobe_help
        except ImportError:
            print("[ERROR] 无法加载换装模块，请确保 prompts/wardrobe.py 存在")
            sys.exit(1)
        
        # 确定主体图片
        if not args.from_image:
            print("[ERROR] 换装需要 --from-image 参数（主体图片路径）")
            print("        示例: --from-image model.png --wear dress.png")
            sys.exit(1)
        
        # 检查主体图片是否存在
        main_image = Path(args.from_image)
        if not main_image.exists():
            for search_dir in [Path("."), Path("test_images"), Path("reference_images"), Path(args.output)]:
                candidate = search_dir / args.from_image
                if candidate.exists():
                    main_image = candidate
                    break
        
        if not main_image.exists():
            print(f"[ERROR] 主体图片不存在: {args.from_image}")
            sys.exit(1)
        
        # 确定任务类型和图片
        if args.wear_image:
            task_type = "clothing"
            # 解析 --wear 参数：可以是 "dress.png" 或 "dress.png '自定义指令'"
            wear_args = args.wear_image
            clothing_path = wear_args[0]
            custom_instruction = wear_args[1] if len(wear_args) > 1 else None
            target_images = [clothing_path]
            print(f"  ✨ 任务类型: 换装 (Clothing Change)")
        else:
            task_type = "accessory"
            target_images = args.accessory_images
            custom_instruction = None
            print(f"  ✨ 任务类型: 配饰 (Accessory Addition)")
        
        # 验证目标图片
        resolved_targets = []
        for img_path in target_images:
            p = Path(img_path)
            if not p.exists():
                for search_dir in [Path("."), Path("test_images"), Path("reference_images"), Path(args.output)]:
                    candidate = search_dir / img_path
                    if candidate.exists():
                        p = candidate
                        break
            
            if not p.exists():
                print(f"[ERROR] 图片不存在: {img_path}")
                sys.exit(1)
            resolved_targets.append(str(p))
        
        # =================================================================
        # 🔪 智能切割预处理：对主体人物和衣服/配饰图片去除背景
        # 这样可以让 AI 更清晰地识别人物和衣服/配饰
        # =================================================================
        if not getattr(args, 'wear_no_rembg', False):
            print(f"\n  🔪 图片预处理 (智能切割去背景)...")
            try:
                from image_processor import remove_background
                import cv2
                
                output_dir = Path(args.output)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 1. 处理主体人物图片
                print(f"     [主体] 处理: {main_image.name}...")
                main_img = cv2.imread(str(main_image))
                if main_img is not None:
                    try:
                        processed_main = remove_background(main_img, model_name="birefnet-general")
                        processed_main_path = output_dir / f"_wear_preprocessed_main_{main_image.name}"
                        if not str(processed_main_path).lower().endswith('.png'):
                            processed_main_path = processed_main_path.with_suffix('.png')
                        cv2.imwrite(str(processed_main_path), processed_main)
                        main_image = processed_main_path
                        print(f"            ✅ 已去除背景 -> {processed_main_path.name}")
                    except Exception as e:
                        print(f"            [警告] 去背景失败: {e}，使用原图")
                else:
                    print(f"            [警告] 无法读取图片，跳过预处理")
                
                # 2. 处理衣服/配饰图片
                processed_targets = []
                for i, target_path in enumerate(resolved_targets, 1):
                    target_name = Path(target_path).name
                    print(f"     [衣物{i}] 处理: {target_name}...")
                    
                    # 读取图片
                    img = cv2.imread(target_path)
                    if img is None:
                        print(f"            [警告] 无法读取图片，跳过预处理")
                        processed_targets.append(target_path)
                        continue
                    
                    # 去除背景
                    try:
                        processed_img = remove_background(img, model_name="birefnet-general")
                        
                        # 保存处理后的图片到临时文件
                        processed_path = output_dir / f"_wear_preprocessed_{i}_{target_name}"
                        
                        # 转换为 PNG 以保留透明度
                        if not str(processed_path).lower().endswith('.png'):
                            processed_path = processed_path.with_suffix('.png')
                        
                        cv2.imwrite(str(processed_path), processed_img)
                        processed_targets.append(str(processed_path))
                        print(f"            ✅ 已去除背景 -> {processed_path.name}")
                    except Exception as e:
                        print(f"            [警告] 去背景失败: {e}，使用原图")
                        processed_targets.append(target_path)
                
                # 用处理后的图片替换原目标列表
                resolved_targets = processed_targets
                print(f"")
            except ImportError as e:
                print(f"     [警告] 无法加载去背景模块: {e}")
                print(f"     [警告] 跳过预处理，使用原图")
        else:
            print(f"\n  ⏭️  跳过图片预处理 (--wear-no-rembg)")
        
        # 构建指令（全英文，以获得最佳效果）
        if args.wear_instruction:
            instruction = args.wear_instruction
        elif custom_instruction:
            instruction = custom_instruction
        else:
            if task_type == "clothing":
                instruction = "Put the clothing from Image 2 onto the person in Image 1. Keep the person's face, hair, pose, and background exactly the same."
            else:
                instruction = "Add the accessory from Image 2 to the person in Image 1. Keep the person's appearance exactly the same."
        
        print(f"  📷 主体图片: {main_image.name}")
        for i, t in enumerate(resolved_targets, 1):
            print(f"  👗 目标图片 [{i}]: {Path(t).name}")
        print(f"  📝 指令: {instruction[:60]}{'...' if len(instruction) > 60 else ''}")
        print(f"  🔒 严格模式: {'开启' if args.wear_strict else '关闭'}")
        
        # 确定使用的模型（支持 --pro 或 --wear-model pro）
        use_pro_model = getattr(args, 'pro', False) or getattr(args, 'wear_model', 'flash') == 'pro'
        if use_pro_model:
            wear_model_name = "gemini-3-pro-image-preview"
            print(f"  🎯 模型: {wear_model_name} (Pro 高保真)")
        else:
            wear_model_name = args.model if args.model else "gemini-3.1-flash-image-preview"
            print(f"  🎯 模型: {wear_model_name}")
        
        print(f"  🔄 调用模式: {args.mode.upper()}")
        
        # =================================================================
        # 检测风格参数（与 --anime, --real 等共享同一系统）
        # ⚠️ 警告：对于换装任务，风格参数可能会改变原图外观！
        # =================================================================
        from prompts.styles import get_style_preset, find_matching_style
        
        wear_style = None
        active_preset = None
        style_warning_shown = False
        
        # 风格参数映射表
        style_flags = {
            'photorealistic': getattr(args, 'photorealistic', False),
            'anime': getattr(args, 'anime', False),
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
            'chibi': getattr(args, 'chibi', False),
        }
        
        # 查找激活的风格预设
        for preset_name, is_active in style_flags.items():
            if is_active:
                active_preset = get_style_preset(preset_name)
                if active_preset:
                    wear_style = active_preset.prompt
                    print(f"  🎨 风格: {active_preset.name.upper()} ({active_preset.description})")
                    # ⚠️ 重要警告：风格参数可能完全改变原图外观
                    if active_preset.name.lower() in ['anime', 'ghibli', 'pixel', 'minecraft', 'clay', 'paper']:
                        print(f"")
                        print(f"  ⚠️  警告: 使用 --{active_preset.name} 风格会将写实照片转换为该风格！")
                        print(f"  ⚠️  如果原图是写实照片，建议去掉 --{active_preset.name} 参数以保持原图外观。")
                        print(f"  ⚠️  或使用 --real / --photorealistic 保持写实风格。")
                        print(f"")
                        style_warning_shown = True
                    break
        
        # 如果没有预设激活，尝试从 --style 参数匹配预设
        if not active_preset and getattr(args, 'style', None):
            matched = find_matching_style(args.style)
            if matched:
                active_preset = matched
                wear_style = matched.prompt
                print(f"  🎨 匹配风格: {matched.name.upper()}")
            else:
                wear_style = args.style
                print(f"  🎨 自定义风格: {wear_style}")
        
        if not wear_style:
            print(f"  🎨 风格: 默认 (photorealistic)")
        
        print("")
        
        # 构建提示词（使用 PromptLibrary 系统，与多视图共享风格预设）
        final_prompt = build_wardrobe_prompt(
            task_type=task_type,
            instruction=instruction,
            num_images=1 + len(resolved_targets),
            strict_mode=args.wear_strict,
            style=wear_style  # 传递风格参数
        )
        
        # 打印最终提示词（如果启用导出）
        if args.export_prompt:
            print("\n[最终换装提示词]")
            print("-" * 60)
            print(final_prompt)
            print("-" * 60 + "\n")
        
        # 组合所有图片路径
        all_images = [str(main_image)] + resolved_targets
        
        # 调用合成 API
        from gemini_generator import composite_images
        
        try:
            # 注意：final_prompt 已经是完整填充好的提示词（由 build_wardrobe_prompt 构建）
            # 使用 instruction_is_final=True 跳过二次模板处理
            output_path = composite_images(
                image_paths=all_images,
                instruction=final_prompt,  # 完整的换装提示词
                api_key=args.token,
                model_name=wear_model_name,  # 使用选定的模型
                output_dir=args.output,
                output_name=None,
                mode=args.mode,
                composite_type=task_type,  # clothing 或 accessory
                composite_prompt_template=None,  # 不使用额外模板
                export_prompt=args.export_prompt,  # 允许在 composite_images 中打印
                instruction_is_final=True,  # 重要：标记提示词已经是完整的
            )
            
            if output_path:
                print(f"\n✅ 换装预处理完成！")
                print(f"   输出: {output_path}")
                
                # 将换装结果设置为后续处理的输入
                args.from_image = output_path
                print(f"\n🔄 继续后续多视图生成流程...")
                print(f"   使用换装结果作为输入: {Path(output_path).name}")
                print("")
            else:
                print(f"\n❌ 换装失败，请检查日志")
                sys.exit(1)
                
        except Exception as e:
            print(f"[ERROR] 换装过程出错: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
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
                model_name=args.model if args.model else "gemini-3.1-flash-image-preview",
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
                model_name=args.model if args.model else "gemini-3.1-flash-image-preview",
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
                model_name=args.model if args.model else "gemini-3.1-flash-image-preview",
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
        # Local 模式现在支持合成操作（使用 Z-Image 的 img2img 功能）
        if args.mode == "local":
            print("\n" + "=" * 60)
            print("📌 Local 模式合成 (使用 Z-Image img2img)")
            print("=" * 60)
            print("  Z-Image 将使用图生图方式进行合成处理")
            print("  注意: 效果可能与云端 API 有所不同")
            print("=" * 60)
        
        print("[高级合成模式]")
        print("  用途: 换衣服、换配饰、创意拼贴、产品模型等")
        
        # =====================================================================
        # 🎲 随机人物 + 固定衣服模式
        # =====================================================================
        random_character_mode = getattr(args, 'random_character', False)
        if random_character_mode:
            print("\n[🎲 随机人物模式]")
            print("  人物: AI随机生成")
            print("  衣服: 使用指定图片")
            
            if not args.composite_images:
                print("[ERROR] --random-character 需要 --composite-images 指定衣服图片")
                print("        示例: --random-character --composite-images dress.png")
                sys.exit(1)
            
            # 为随机人物生成描述
            random_theme = getattr(args, 'random_theme', None) or ''
            if random_theme:
                character_desc = f"a unique {random_theme} character"
            else:
                character_desc = "a unique and attractive character with distinctive features"
            
            # 自动生成合成指令
            if not args.composite_instruction:
                args.composite_instruction = f"Generate {character_desc} wearing the clothing from the provided image. The character should be in a natural pose showing the outfit clearly."
                print(f"  [自动指令] {args.composite_instruction[:80]}...")
        
        # =====================================================================
        # 🎲 固定人物 + 随机衣服模式
        # =====================================================================
        random_clothing_style = getattr(args, 'random_clothing', None)
        if random_clothing_style:
            print("\n[🎲 随机衣服模式]")
            print(f"  人物: 使用参考图片")
            print(f"  衣服: AI随机生成 ({random_clothing_style})")
            
            if not args.from_image:
                print("[ERROR] --random-clothing 需要 --from-image 指定人物图片")
                print("        示例: --from-image model.png --random-clothing '时尚连衣裙'")
                sys.exit(1)
            
            # 自动生成合成指令
            if not args.composite_instruction:
                args.composite_instruction = f"Keep the person exactly as shown in the image, but dress them in {random_clothing_style}. The clothing should be stylish, well-fitted, and match the character's style."
                print(f"  [自动指令] {args.composite_instruction[:80]}...")
            
            # 不需要额外的图片，只用 from_image
            if not args.composite_images:
                args.composite_images = []  # 空列表，单图模式
        
        # 验证必需参数（除非是特殊随机模式）
        if not random_character_mode and not random_clothing_style:
            if not args.composite_images or len(args.composite_images) < 1:
                print("[ERROR] --mode-composite 需要 --composite-images 参数（至少1张图片）")
                print("        示例: --composite-images model.png dress.png")
                print("        或配合 --from-image: --from-image model.png --composite-images dress.png")
                print("        或单图模式: --composite-images model.png --composite-instruction '让这个人穿上JNBY的衣服'")
                print("\n        🎲 随机模式:")
                print("        --random-character --composite-images dress.png (随机人物穿指定衣服)")
                print("        --from-image model.png --random-clothing '连衣裙' (指定人物穿随机衣服)")
                sys.exit(1)
        
        if not args.composite_instruction:
            print("[ERROR] --mode-composite 需要 --composite-instruction 参数（合成指令）")
            print("        示例: --composite-instruction '让模特穿上这件裙子'")
            sys.exit(1)
        
        # 如果有 --from-image，将其作为第一张图片
        if args.from_image:
            all_images = [args.from_image] + (args.composite_images or [])
        else:
            all_images = args.composite_images or []
        
        # 判断是单图模式还是多图模式
        single_image_mode = len(all_images) == 1
        
        if single_image_mode:
            print("\n[单图智能合成模式]")
            print("  检测到只有1张图片，将使用文字描述直接生成并合成衣服...")
            print(f"  主体图片: {Path(all_images[0]).name}")
            print(f"  衣服描述: {args.composite_instruction}")
            print("")
        
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
        
        # =====================================================================
        # 🧠 智能衣服提取预处理
        # 如果有多张图片且启用了智能提取，对衣服图片进行AI分析和处理
        # 支持混合模式: --mode local --analysis-api proxy 可以用AiProxy分析+本地生成
        # =====================================================================
        
        # 确定是否使用云端API进行图像分析
        use_cloud_analysis = (
            args.analysis_api in ["proxy", "direct"] or 
            (args.analysis_api == "auto" and args.mode != "local")
        )
        
        # 确定分析用的模式和 API key
        if args.analysis_api in ["proxy", "direct"]:
            # 显式指定了分析模式
            analysis_mode = args.analysis_api
        elif args.analysis_api == "auto":
            # auto 模式跟随 --mode
            analysis_mode = args.mode if args.mode != "local" else "proxy"
        else:
            analysis_mode = None
        
        # 获取分析用的 API key
        analysis_api_key = args.token
        if use_cloud_analysis and args.mode == "local":
            # local 生成模式但需要云端分析，尝试获取对应 API key
            if analysis_mode == "proxy":
                analysis_api_key = os.environ.get("AIPROXY_TOKEN") or args.token
            else:
                analysis_api_key = os.environ.get("GEMINI_API_KEY") or args.token
            
            if not analysis_api_key:
                print(f"\n⚠️  混合模式需要 API Key 用于图像分析")
                if analysis_mode == "proxy":
                    print(f"   请设置 AIPROXY_TOKEN 环境变量")
                else:
                    print(f"   请设置 GEMINI_API_KEY 环境变量")
                print(f"   或改用: --analysis-api local 跳过智能分析")
                use_cloud_analysis = False
        
        if args.composite_smart_extract and len(image_paths) >= 2:
            if not use_cloud_analysis:
                print(f"\n⏭️  跳过智能衣服提取 (未启用云端分析)")
                print(f"   提示: 使用 --analysis-api proxy 或 --analysis-api direct 启用")
                print(f"   将直接使用原图进行合成\n")
            else:
                print(f"\n🧠 智能衣服提取预处理")
                print(f"  检测到 {len(image_paths)} 张图片，开始分析...")
                print(f"  分析模式: {analysis_mode.upper()}")
                if args.mode == "local":
                    print(f"  📌 混合模式: 使用云端API分析 + 本地模型生成")
                
                # 导入智能提取函数
                from gemini_generator import smart_extract_clothing
                
                # 处理所有非第一张的图片（第一张通常是主体人物）
                processed_paths = [image_paths[0]]  # 保留主体图片
                
                for i, clothing_img in enumerate(image_paths[1:], 2):
                    print(f"\n  [图片 {i}] 分析: {Path(clothing_img).name}")
                    
                    try:
                        # 调用智能提取 (始终使用云端API进行分析)
                        extracted_path = smart_extract_clothing(
                            image_path=clothing_img,
                            api_key=analysis_api_key,
                            model_name=args.model if args.model else "gemini-3.1-flash-image-preview",
                            output_dir=args.output,
                            mode=analysis_mode,  # 分析始终用云端
                        )
                        
                        if extracted_path:
                            print(f"  ✅ 提取完成: {Path(extracted_path).name}")
                            processed_paths.append(extracted_path)
                        else:
                            print(f"  ⚠️  提取失败，使用原图")
                            processed_paths.append(clothing_img)
                            
                    except Exception as e:
                        print(f"  ⚠️  智能提取出错: {e}")
                        print(f"     使用原图继续")
                        processed_paths.append(clothing_img)
                
                # 用处理后的路径替换原路径
                image_paths = processed_paths
                print(f"\n  ✅ 预处理完成，准备进行合成...\n")
        elif not args.composite_smart_extract:
            print(f"\n  ⏭️  跳过智能提取 (--composite-no-smart-extract)\n")
        
        print(f"\n  └─ 输入图片 ({len(image_paths)} 张):")
        for i, img in enumerate(image_paths, 1):
            print(f"      [{i}] {Path(img).name}")
        print(f"  └─ 合成指令: {args.composite_instruction}")
        print(f"  └─ 输出目录: {args.output}")
        print(f"  └─ 调用模式: {args.mode.upper()}")
        
        # 确定使用的模型（支持 --pro 参数）
        if getattr(args, 'pro', False):
            composite_model = "gemini-3-pro-image-preview"
            print(f"  └─ 模型: {composite_model} (Pro 高保真模式)")
        else:
            composite_model = args.model if args.model else "gemini-3.1-flash-image-preview"
            print(f"  └─ 模型: {composite_model}")
        
        # 确定分辨率和宽高比
        composite_resolution = getattr(args, 'resolution', '2K') or '2K'
        composite_aspect_ratio = getattr(args, 'aspect_ratio', None) or '1:1'  # 合成默认用 1:1 正方形
        print(f"  └─ 分辨率: {composite_resolution}, 宽高比: {composite_aspect_ratio}")
        print("")
        
        # 导入合成函数
        from gemini_generator import composite_images
        
        # 根据图片数量选择合成类型
        composite_type_to_use = args.composite_type
        if single_image_mode:
            # 单图模式使用文字描述模板
            composite_type_to_use = "clothing_text"
            print(f"  └─ 使用单图模式模板: {composite_type_to_use}")
        else:
            print(f"  └─ 合成类型: {composite_type_to_use}")
        
        # 执行合成 (遵守 proxy/direct 设置)
        try:
            output_path = composite_images(
                image_paths=image_paths,
                instruction=args.composite_instruction,
                api_key=args.token,
                model_name=composite_model,
                output_dir=args.output,
                output_name=args.composite_output_name,
                mode=args.mode,
                composite_type=composite_type_to_use,
                composite_prompt_template=args.composite_prompt_template,
                export_prompt=args.export_prompt,
                resolution=composite_resolution,
                aspect_ratio=composite_aspect_ratio,
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
                args.iterative_360 or
                getattr(args, 'toon3d', False) or
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
        
        if not args.preserve_instructions:
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
                model_name=args.model if args.model else "gemini-3.1-flash-image-preview",
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
                args.iterative_360 or
                getattr(args, 'toon3d', False) or
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
    # 服装提取模式检查 (--mode-extract)
    # =========================================================================
    if args.mode_extract:
        print("\n" + "═"*60)
        print("🔍 激活服装提取模式")
        print("═"*60)
        print("  用途: 提取图中人穿着的衣物或手持的道具")
        
        # 验证必需参数
        extract_source = args.from_image
        if not extract_source:
            print("[ERROR] --mode-extract 需要 --from-image 参数（输入图片路径）")
            print("        示例: --from-image person.png --mode-extract")
            sys.exit(1)
            
        # 查找图片
        main_image = Path(extract_source)
        if not main_image.exists():
            for search_dir in [Path("."), Path("test_images"), Path("reference_images"), Path(args.output)]:
                candidate = search_dir / extract_source
                if candidate.exists():
                    main_image = candidate
                    break
                    
        if not main_image.exists():
            print(f"[ERROR] 提取源图片不存在: {extract_source}")
            sys.exit(1)
            
        print(f"\n  └─ 源图片: {main_image.name}")
        print(f"  └─ 提取道具: {'是' if args.extract_props else '否'}")
        print(f"  └─ 模型: {args.model if args.model else 'gemini-3.1-flash-image-preview'}")
        print(f"  └─ 调用模式: {args.mode.upper()}")
        print("")
        
        # 导入提取函数
        from gemini_generator import smart_extract_clothing
        
        try:
            result = smart_extract_clothing(
                image_path=str(main_image),
                api_key=args.token,
                model_name=args.model if args.model else "gemini-3.1-flash-image-preview",
                output_dir=args.output,
                mode=args.mode,
                extract_props=args.extract_props,
                export_prompt=args.export_prompt
            )
            
            if result:
                output_path, props = result
                print(f"\n✅ 提取完成！")
                print(f"   输出文件: {output_path}")
                if args.extract_props:
                    print(f"   提取的道具: {', '.join(props) if props else '无'}")
            else:
                print(f"\n❌ 提取失败，请检查日志")
                sys.exit(1)
                
            # 提取模式本身就是一个独立的功能，执行完毕后直接退出
            sys.exit(0)
            
        except Exception as e:
            print(f"[ERROR] 提取出错: {e}")
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
    # local 模式也不需要token验证（使用本地 Z-Image 服务）
    if not args.export_prompt and args.mode != "local":
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
                local_cmd = " ".join(base_cmd_parts + ["--mode local"])
                export_cmd = " ".join(base_cmd_parts + ["--export-prompt"])
                
                print("💡 解决方案:")
                print(f"\n   选项 1: 直接传递 AiProxy Token (推荐)")
                print(f"   {proxy_cmd_with_token}")
                print(f"\n   选项 2: 使用直连模式")
                print(f"   {direct_cmd}")
                print(f"\n   选项 3: 使用本地 Z-Image 模式 (无需 Token)")
                print(f"   {local_cmd}")
                print(f"\n   选项 4: 导出提示词 (不消耗API配额)")
                print(f"   {export_cmd}")
                print(f"\n   选项 5: 设置环境变量")
                print(f"   $env:AIPROXY_TOKEN='your-token'  # PowerShell")
                print(f"   {' '.join(base_cmd_parts + ['--mode proxy'])}\n")
                sys.exit(1)
        elif args.mode == "direct":
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
                local_cmd = " ".join(base_cmd_parts + ["--mode local"])
                export_cmd = " ".join(base_cmd_parts + ["--export-prompt"])
                
                print("💡 解决方案:")
                print(f"\n   选项 1: 直接传递 Gemini API Key (推荐)")
                print(f"   {direct_cmd_with_key}")
                print(f"\n   选项 2: 使用代理模式")
                print(f"   {proxy_cmd}")
                print(f"\n   选项 3: 使用本地 Z-Image 模式 (无需 Token)")
                print(f"   {local_cmd}")
                print(f"\n   选项 4: 导出提示词 (不消耗API配额)")
                print(f"   {export_cmd}")
                print(f"\n   选项 5: 设置环境变量")
                print(f"   $env:GEMINI_API_KEY='your-api-key'  # PowerShell")
                print(f"   {' '.join(base_cmd_parts + ['--mode direct'])}\n")
                sys.exit(1)
    
    # 设置模型 (Nano Banana 2 为默认)
    model = args.model or "gemini-3.1-flash-image-preview"
    
    # 显示模式信息（导出模式除外）
    if not args.export_prompt:
        if args.mode == "proxy":
            print(f"[模式] AiProxy (bot.bigjj.click/aiproxy)")
            print(f"[模型] {model}")
        elif args.mode == "local":
            local_url = getattr(args, 'local_url', None) or os.environ.get("ZIMAGE_URL", "http://localhost:8199")
            print(f"[模式] 本地 Z-Image-Turbo")
            print(f"[服务] {local_url}")
        else:
            print(f"[模式] 直连 Gemini API")
            print(f"[模型] {model}")
    else:
        print(f"[导出模式] 准备提示词参数...")
    
    # 获取角色描述
    if args.description:
        description = args.description
    elif getattr(args, 'random', False):
        # 随机生成模式：AI自由创作，无需参考图
        random_theme = getattr(args, 'random_theme', None) or ''
        if random_theme:
            description = f"Create a unique and creative character: {random_theme}"
            print(f"[INFO] 随机生成模式：主题 '{random_theme}'")
        else:
            description = "Create a unique, creative, and visually interesting character with distinctive features and outfit"
            print("[INFO] 随机生成模式：AI自由创作全新角色")
        print("[特点] 无参考图输入，生成符合多视角标准的随机角色")
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
    
    # =========================================================================
    # 本地 Z-Image 模式
    # =========================================================================
    if args.mode == "local":
        from zimage_client import ZImageClient, generate_character_local
        
        print("\n" + "=" * 60)
        print("🖥️  本地 Z-Image-Turbo 模式")
        print("=" * 60)
        
        local_url = args.local_url or os.environ.get("ZIMAGE_URL", "http://localhost:8199")
        print(f"   服务地址: {local_url}")
        
        # 检查服务是否可用
        client = ZImageClient(base_url=local_url)
        if not client.health_check():
            print("\n❌ Z-Image 服务不可用!")
            print("   请先启动服务:")
            print("   ")
            print("   docker compose up -d zimage")
            print("   ")
            print("   查看日志:")
            print("   docker compose logs -f zimage")
            print("")
            sys.exit(1)
        
        print("   ✅ 服务已就绪")
        
        # 确定视角模式
        view_mode = f"{args.views}-view"
        multi_view = args.views != "1"  # 除了单视角都是多视角
        
        print(f"   角色: {description[:50]}{'...' if len(description) > 50 else ''}")
        print(f"   风格: {style}")
        print(f"   多视角: {'是 (' + view_mode + ')' if multi_view else '否'}")
        print("")
        
        # 调用本地生成
        result = generate_character_local(
            character_description=description,
            style=style,
            output_dir=args.output,
            multi_view=multi_view,
            view_mode=view_mode,
            seed=None,  # 可以添加 --seed 参数
            auto_cut=not args.no_cut,
        )
        
        if result:
            print(f"\n✅ 本地生成成功: {result}")
        else:
            print("\n❌ 本地生成失败")
            sys.exit(1)
    
    # 调用生成器 (proxy/direct 模式)
    elif args.mode == "proxy":
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
            # 如果用户提供了描述，将其作为额外指令传递
            if args.description:
                description = f"(strict mode) User instruction: {args.description}"
                print(f"[用户指令] {args.description}")
            else:
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
            export_prompt=args.export_prompt,
            remove_bg=not getattr(args, 'no_rembg', False),
            rembg_model=getattr(args, 'rembg_model', 'isnet-general-use')
        )
    elif args.mode == "direct":
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
                # 严格模式：跳过分析，但保留用户指令
                print(f"\n[严格复制模式] 跳过图片分析，100% 基于原图生成")
                # 如果用户提供了描述，将其作为额外指令传递
                if args.description:
                    description = f"(strict mode) User instruction: {args.description}"
                    print(f"[用户指令] {args.description}")
                else:
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
                with_props=args.with_props,
                remove_bg=not getattr(args, 'no_rembg', False),
                rembg_model=getattr(args, 'rembg_model', 'isnet-general-use')
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
