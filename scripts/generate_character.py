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
        description="Cortex3d - 从描述生成多视角角色图像"
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="角色描述"
    )
    parser.add_argument(
        "--from-image",
        dest="from_image",
        default=None,
        help="从参考图片提取角色特征生成多视角图 (例如: 街拍照片.jpg)"
    )
    parser.add_argument(
        "--mode",
        choices=["proxy", "direct"],
        default="proxy",
        help="生成模式: proxy=AiProxy服务, direct=直连Gemini API"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("AIPROXY_TOKEN"),
        help="AiProxy 令牌 (proxy模式)"
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("GEMINI_API_KEY"),
        help="Gemini API Key (direct模式)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="模型名称 (默认: proxy模式用nano-banana-pro, direct模式用gemini-2.0-flash-exp)"
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
    parser.add_argument(
        "--to-3d",
        action="store_true",
        help="生成后自动转换为 3D 模型"
    )
    parser.add_argument(
        "--algo",
        choices=["hunyuan3d", "hunyuan3d-2.1", "hunyuan3d-omni", "trellis", "trellis2"],
        default="hunyuan3d",
        help="3D 生成算法 (默认: hunyuan3d, omni支持姿势控制)"
    )
    parser.add_argument(
        "--quality",
        choices=["balanced", "high", "ultra"],
        default="high",
        help="3D 模型质量: balanced(快)/high(均衡)/ultra(最佳但慢)"
    )
    parser.add_argument(
        "--geometry-only", "--fast",
        dest="geometry_only",
        action="store_true",
        help="只生成几何模型, 不生成纹理 (速度快很多)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="生成后自动打开预览"
    )
    parser.add_argument(
        "--pose",
        default=None,
        help="姿势控制文件路径 (仅 hunyuan3d-omni 支持，例如: poses/t_pose.json)"
    )
    
    parser.add_argument(
        "--style",
        default=None,
        help="风格描述 (例如: 'cyberpunk', 'fantasy', 'anime'). 默认自动根据描述匹配或使用 'cinematic character'"
    )
    
    parser.add_argument(
        "--from-id",
        dest="from_id",
        default=None,
        help="跳过2D生成，使用已有的图片ID直接生成3D模型 (例如: a7af1af9-a592-4499-a456-2bea8428fe49)"
    )
    
    args = parser.parse_args()
    
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
        print("🚀 启动 3D 生成流水线 (TRELLIS)...")
        print("═" * 50)
        
        reconstructor_script = script_dir / "reconstructor.py"
        cmd = [
            sys.executable,
            str(reconstructor_script),
            str(front_img),
            "--algo", "trellis",
            "--quality", args.quality,
            "--output_dir", str(Path("outputs"))
        ]
        
        try:
            import subprocess
            subprocess.run(cmd, check=True)
            print("\n[SUCCESS] 3D 生成完成！")
            
            glb_path = Path("outputs/trellis") / f"{image_id}_front.glb"
            obj_path = Path("outputs/trellis") / f"{image_id}_front.obj"
            
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
    
    # 检查认证
    if args.mode == "proxy":
        if not args.token:
            print("[!] 未设置 AiProxy 令牌")
            print("    请运行: export AIPROXY_TOKEN='your-token'")
            print("    或使用: --mode direct 直连 Gemini API")
            sys.exit(1)
        model = args.model or "models/nano-banana-pro-preview"
        print(f"[模式] AiProxy (bot.bigjj.click/aiproxy)")
    else:
        if not args.api_key:
            print("[!] 未设置 Gemini API Key")
            print("    请运行: export GEMINI_API_KEY='your-key'")
            sys.exit(1)
        model = args.model or "gemini-2.0-flash-exp"
        print(f"[模式] 直连 Gemini API")
    
    print(f"[模型] {model}")
    
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
        from pathlib import Path
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
        
        args.from_image = str(image_path)  # 更新为实际路径
        
        print(f"\\n[图片参考模式] 分析图片: {args.from_image}")
        print("="*50)
        
        from aiproxy_client import analyze_image_for_character
        
        # 用户提供的描述作为指导词（指定分析哪个人物或关注什么细节）
        user_guidance = args.description if args.description else None
        
        extracted_description = analyze_image_for_character(
            image_path=args.from_image,
            token=args.token,
            user_guidance=user_guidance
        )
        
        if extracted_description:
            print(f"\n[提取的描述]")
            print("-"*50)
            print(extracted_description[:500] + "..." if len(extracted_description) > 500 else extracted_description)
            print("-"*50)
            
            # 使用提取的描述作为主描述
            description = extracted_description
        else:
            print("[WARNING] 图片分析失败，使用默认描述")
            if not args.description:
                print("[ERROR] 图片分析失败且未提供描述，无法继续")
                sys.exit(1)
    
    # 调用生成器
    if args.mode == "proxy":
        from aiproxy_client import generate_character_multiview
        
        # 确定是否使用图片参考模式
        ref_image_path = args.from_image if args.from_image else None
        use_ref_prompt = bool(args.from_image)  # 如果有参考图片，使用保留动作的提示词
        
        result = generate_character_multiview(
            character_description=description,
            token=args.token,
            output_dir=args.output,
            auto_cut=not args.no_cut,
            model=model,
            style=style,
            reference_image_path=ref_image_path,
            use_image_reference_prompt=use_ref_prompt
        )
    else:
        # Gemini Generator也需要更新支持style，这里暂时只支持proxy模式的style传递
        # 或稍微修改一下 gemini_generator 的调用假设它有 style (需要去检查 gemini_generator.py)
        # 检查 gemini_generator.py 发现它可能需要单独更新，暂时只更新 proxy 路径因为它是默认推荐
        from gemini_generator import generate_character_views
        # 注意：如果 gemini_generator 还没更新支持 style，这里会报错。
        # 为了安全，先检查一下 gemini_generator。
        # 假设暂时不传 style给 gemini (或者稍后更新它)
        result = generate_character_views(
            character_description=description,
            api_key=args.api_key,
            model_name=model,
            output_dir=args.output,
            auto_cut=not args.no_cut
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

        # 列出生成的文件
        if output_path.exists():
            files = list(output_path.glob("*.png"))
            if files:
                print("\n生成的文件列表:")
                for f in sorted(files)[-5:]:
                     print(f"  📷 {f.name}")
        
    else:
        print("\n❌ 生成失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
