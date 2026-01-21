#!/usr/bin/env python3
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


def main():
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
        help="Style description. Default: 'cinematic character'. Presets: see --photorealistic, --anime"
    )
    
    parser.add_argument(
        "--photorealistic", "--real",
        dest="photorealistic",
        action="store_true",
        help="Preset: Generate photorealistic images (8k, raw photo, realistic texture)"
    )
    
    parser.add_argument(
        "--anime",
        action="store_true",
        help="Preset: Generate anime style images"
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
    
    args = parser.parse_args()
    
    # 根据模式自动设置token(如果未提供)
    if args.token is None:
        if args.mode == "proxy":
            args.token = os.environ.get("AIPROXY_TOKEN")
        else:  # direct mode
            args.token = os.environ.get("GEMINI_API_KEY")
    
    # Banner
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    Cortex3d 角色生成器                         ║
║         AI 多视角图像生成 → 切割 → 去背景 → 3D建模             ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
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

    # 确定风格
    style = args.style
    
    # 优先处理 Preset 参数
    if args.photorealistic:
        preset = "Photorealistic, 8k, raw photo, realistic texture, hyperrealistic photography, highly detailed skin texture, cinematic lighting"
        style = f"{preset}, {style}" if style else preset
        print(f"[预设风格] Photorealistic ({style})")
    elif args.anime:
        preset = "Anime style, cell shaded, vibrant colors, 2D art style, studio ghibli style"
        style = f"{preset}, {style}" if style else preset
        print(f"[预设风格] Anime ({style})")
    
    if not style:
        # 简单的关键词风格匹配
        desc_lower = description.lower()
        if "cyberpunk" in desc_lower or "neon" in desc_lower or "mech" in desc_lower:
            style = "Cyberpunk sci-fi style"
        elif "knight" in desc_lower or "magic" in desc_lower or "fantasy" in desc_lower or "dragon" in desc_lower:
            style = "High fantasy style"
        elif "anime" in desc_lower or "manga" in desc_lower:
            style = "Anime style"
        else:
            style = "Cinematic character design"
        print(f"[自动匹配风格] {style}")
    else:
        print(f"[指定风格] {style}")

    # 自动增强提示词 (特别是面部)
    enhancements = ", detailed face, delicate features, high resolution, 8k, masterpiece, photorealistic, sharp focus"
    if "face" not in description.lower() and "feature" not in description.lower():
         description += enhancements
         print(f"[提示词增强] {description}")
    
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
            negative_categories=args.negative_categories
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
            
        result = generate_character_views(
            character_description=description,
            api_key=args.token,
            model_name=model,
            output_dir=args.output,
            auto_cut=not args.no_cut,
            style=style,
            view_mode=view_mode,
            custom_views=custom_views,
            negative_prompt=negative_prompt,
            reference_image_path=ref_image_path,
            use_strict_mode=args.strict,
            resolution=args.resolution,
            original_args=args,
            export_prompt=args.export_prompt
        )
    
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
        
    else:
        print("\n❌ 生成失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
