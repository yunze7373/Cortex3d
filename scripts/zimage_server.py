#!/usr/bin/env python3
"""
Z-Image-Turbo 本地推理服务
提供 REST API 用于图像生成

模型: Tongyi-MAI/Z-Image-Turbo (6B参数)
- 8步推理，亚秒级延迟
- 支持中英文双语
- 优秀的文字渲染能力
- 16GB VRAM 即可运行

API 端点:
- GET  /health   - 健康检查
- POST /generate - 文生图 (Text-to-Image)
- POST /img2img  - 图生图 (Image-to-Image)
- GET  /info     - 模型信息
"""

import os
import sys
import base64
import time
import torch
from io import BytesIO
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# 全局 Pipeline
pipe = None
model_loaded = False


def load_model():
    """加载 Z-Image-Turbo 模型"""
    global pipe, model_loaded
    
    print("=" * 60)
    print("🚀 Z-Image-Turbo 本地推理服务")
    print("=" * 60)
    print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 PyTorch: {torch.__version__}")
    print(f"🎮 CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    print("")
    
    print("📦 正在加载 Z-Image-Turbo 模型...")
    print("   来源: Tongyi-MAI/Z-Image-Turbo (HuggingFace)")
    print("   参数: 6B")
    print("   精度: bfloat16")
    
    start_time = time.time()
    
    try:
        from diffusers import ZImagePipeline
        
        pipe = ZImagePipeline.from_pretrained(
            "Tongyi-MAI/Z-Image-Turbo",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
        )
        
        # 尝试直接加载到 GPU
        use_cpu_offload = False
        try:
            # 先清理显存
            torch.cuda.empty_cache()
            pipe.to("cuda")
            print("   ✅ 模型已加载到 GPU")
        except (RuntimeError, torch.cuda.OutOfMemoryError) as oom_e:
            print(f"   ⚠️  GPU 显存不足: {oom_e}")
            print("   🔄 启用 Sequential CPU Offload 模式...")
            torch.cuda.empty_cache()
            # 重新加载并使用 CPU offload
            del pipe
            torch.cuda.empty_cache()
            pipe = ZImagePipeline.from_pretrained(
                "Tongyi-MAI/Z-Image-Turbo",
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
            )
            pipe.enable_sequential_cpu_offload()
            use_cpu_offload = True
            print("   ✅ CPU Offload 模式已启用 (推理速度会略慢)")
        
        # 尝试启用 Flash Attention
        if not use_cpu_offload:
            try:
                pipe.transformer.set_attention_backend("flash")
                print("   ✅ Flash Attention 2 已启用")
            except Exception as e:
                print(f"   ⚠️  Flash Attention 不可用，使用 SDPA: {e}")
        
        # 可选: 编译模型 (首次推理会慢，之后更快)
        # pipe.transformer.compile()
        
        load_time = time.time() - start_time
        print(f"\n✅ 模型加载完成! 耗时: {load_time:.1f}秒")
        if use_cpu_offload:
            print("   📌 运行模式: CPU Offload (节省显存)")
        print(f"🌐 服务地址: http://0.0.0.0:8199")
        print("=" * 60)
        
        model_loaded = True
        
    except Exception as e:
        print(f"\n❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok" if model_loaded else "loading",
        "model": "Z-Image-Turbo",
        "cuda": torch.cuda.is_available(),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    })


@app.route("/generate", methods=["POST"])
def generate():
    """
    生成图像
    
    POST JSON:
    {
        "prompt": "描述文本 (支持中英文)",
        "width": 1024,      // 默认 1024
        "height": 1024,     // 默认 1024
        "steps": 9,         // 默认 9 (实际 8 次 DiT 前向)
        "seed": 42,         // 可选，随机种子
        "negative_prompt": "..."  // 可选，负面提示词 (Turbo模型效果有限)
    }
    
    返回:
    {
        "image": "base64编码的PNG图像",
        "width": 1024,
        "height": 1024,
        "seed": 42,
        "time": 1.23
    }
    """
    if not model_loaded:
        return jsonify({"error": "模型正在加载中，请稍后重试"}), 503
    
    try:
        data = request.json or {}
        
        prompt = data.get("prompt", "")
        width = data.get("width", 1024)
        height = data.get("height", 1024)
        steps = data.get("steps", 9)  # Z-Image-Turbo 推荐 9 步
        seed = data.get("seed", None)
        
        if not prompt:
            return jsonify({"error": "prompt 参数是必需的"}), 400
        
        # 验证尺寸
        if width < 256 or width > 2048 or height < 256 or height > 2048:
            return jsonify({"error": "尺寸范围: 256-2048"}), 400
        
        # 生成器 (种子)
        if seed is None:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
        generator = torch.Generator("cuda").manual_seed(seed)
        
        print(f"\n🎨 [{datetime.now().strftime('%H:%M:%S')}] 生成请求")
        print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        print(f"   尺寸: {width}x{height}, 步数: {steps}, 种子: {seed}")
        
        start_time = time.time()
        
        # 生成图像
        image = pipe(
            prompt=prompt,
            height=height,
            width=width,
            num_inference_steps=steps,
            guidance_scale=0.0,  # Turbo 模型不需要 guidance
            generator=generator,
        ).images[0]
        
        gen_time = time.time() - start_time
        
        # 转 base64
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        print(f"   ✅ 完成! 耗时: {gen_time:.2f}秒")
        
        return jsonify({
            "image": img_b64,
            "width": width,
            "height": height,
            "seed": seed,
            "time": round(gen_time, 2),
        })
        
    except torch.cuda.OutOfMemoryError:
        print("   ❌ CUDA 内存不足!")
        torch.cuda.empty_cache()
        return jsonify({"error": "GPU 内存不足，请尝试较小的尺寸"}), 507
        
    except Exception as e:
        print(f"   ❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/info", methods=["GET"])
def info():
    """模型信息"""
    return jsonify({
        "model": "Z-Image-Turbo",
        "developer": "Tongyi-MAI (阿里巴巴通义)",
        "parameters": "6B",
        "recommended_steps": 9,
        "supported_resolutions": [512, 768, 1024, 1280, 1536, 2048],
        "features": [
            "中英文双语支持",
            "优秀的文字渲染",
            "照片级真实感",
            "8步快速推理",
            "图生图 (img2img)",
        ],
        "endpoints": [
            {"method": "GET", "path": "/health", "description": "健康检查"},
            {"method": "POST", "path": "/generate", "description": "文生图"},
            {"method": "POST", "path": "/img2img", "description": "图生图"},
        ],
        "gpu": {
            "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1) if torch.cuda.is_available() else None,
        }
    })


@app.route("/img2img", methods=["POST"])
def img2img():
    """
    图生图 (Image-to-Image)
    
    使用 SDEdit 方式：对输入图像添加噪声然后去噪，实现风格变换或内容修改。
    
    POST JSON:
    {
        "prompt": "描述文本 (支持中英文)",
        "image": "base64编码的输入图像",
        "strength": 0.75,   // 0.0-1.0, 越高变化越大
        "width": 1024,      // 可选，默认使用原图尺寸
        "height": 1024,     // 可选，默认使用原图尺寸
        "steps": 9,         // 默认 9
        "seed": 42          // 可选，随机种子
    }
    
    返回:
    {
        "image": "base64编码的PNG图像",
        "width": 1024,
        "height": 1024,
        "seed": 42,
        "strength": 0.75,
        "time": 1.23
    }
    """
    if not model_loaded:
        return jsonify({"error": "模型正在加载中，请稍后重试"}), 503
    
    try:
        from PIL import Image
        import numpy as np
        
        data = request.json or {}
        
        prompt = data.get("prompt", "")
        image_b64 = data.get("image", "")
        strength = float(data.get("strength", 0.75))
        steps = data.get("steps", 9)
        seed = data.get("seed", None)
        
        if not prompt:
            return jsonify({"error": "prompt 参数是必需的"}), 400
        
        if not image_b64:
            return jsonify({"error": "image 参数是必需的 (base64编码)"}), 400
        
        # 验证 strength
        if strength < 0.0 or strength > 1.0:
            return jsonify({"error": "strength 范围: 0.0-1.0"}), 400
        
        # 解码输入图像
        try:
            # 处理可能的 data:image/png;base64, 前缀
            if "base64," in image_b64:
                image_b64 = image_b64.split("base64,")[1]
            image_data = base64.b64decode(image_b64)
            init_image = Image.open(BytesIO(image_data)).convert("RGB")
        except Exception as e:
            return jsonify({"error": f"图像解码失败: {e}"}), 400
        
        # 获取/设置尺寸
        width = data.get("width", init_image.width)
        height = data.get("height", init_image.height)
        
        # 验证尺寸
        if width < 256 or width > 2048 or height < 256 or height > 2048:
            return jsonify({"error": "尺寸范围: 256-2048"}), 400
        
        # 调整输入图像尺寸
        if init_image.width != width or init_image.height != height:
            init_image = init_image.resize((width, height), Image.Resampling.LANCZOS)
        
        # 生成器 (种子)
        if seed is None:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
        generator = torch.Generator("cuda").manual_seed(seed)
        
        print(f"\n🖼️ [{datetime.now().strftime('%H:%M:%S')}] 图生图请求")
        print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        print(f"   尺寸: {width}x{height}, 强度: {strength}, 步数: {steps}, 种子: {seed}")
        
        start_time = time.time()
        
        # SDEdit: 计算实际步数
        # strength=0.75 意味着跳过 25% 的去噪步骤
        actual_steps = int(steps * strength)
        if actual_steps < 1:
            actual_steps = 1
        
        # 使用 VAE 编码输入图像到潜空间
        init_image_tensor = pipe.image_processor.preprocess(init_image)
        init_image_tensor = init_image_tensor.to(device=pipe.device, dtype=pipe.dtype)
        
        # 编码到潜空间
        latents = pipe.vae.encode(init_image_tensor).latent_dist.sample(generator)
        latents = latents * pipe.vae.config.scaling_factor
        
        # 设置调度器
        pipe.scheduler.set_timesteps(steps)
        
        # 计算开始的时间步
        start_step = int(steps * (1 - strength))
        timesteps = pipe.scheduler.timesteps[start_step:]
        
        # 添加噪声
        noise = torch.randn(latents.shape, generator=generator, device=pipe.device, dtype=pipe.dtype)
        latents = pipe.scheduler.add_noise(latents, noise, timesteps[:1])
        
        # 编码提示词
        prompt_embeds, pooled_prompt_embeds = pipe.encode_prompt(
            prompt=prompt,
            device=pipe.device,
            num_images_per_prompt=1,
            do_classifier_free_guidance=False,
        )
        
        # 去噪循环
        for i, t in enumerate(timesteps):
            # 预测噪声
            noise_pred = pipe.transformer(
                hidden_states=latents,
                timestep=t.unsqueeze(0),
                encoder_hidden_states=prompt_embeds,
                pooled_projections=pooled_prompt_embeds,
                return_dict=False,
            )[0]
            
            # 更新潜变量
            latents = pipe.scheduler.step(noise_pred, t, latents, return_dict=False)[0]
        
        # 解码图像
        latents = latents / pipe.vae.config.scaling_factor
        image = pipe.vae.decode(latents, return_dict=False)[0]
        image = pipe.image_processor.postprocess(image, output_type="pil")[0]
        
        gen_time = time.time() - start_time
        
        # 转 base64
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        print(f"   ✅ 完成! 耗时: {gen_time:.2f}秒")
        
        return jsonify({
            "image": img_b64,
            "width": width,
            "height": height,
            "seed": seed,
            "strength": strength,
            "time": round(gen_time, 2),
        })
        
    except torch.cuda.OutOfMemoryError:
        print("   ❌ CUDA 内存不足!")
        torch.cuda.empty_cache()
        return jsonify({"error": "GPU 内存不足，请尝试较小的尺寸"}), 507
        
    except Exception as e:
        print(f"   ❌ 图生图失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 加载模型
    load_model()
    
    # 启动服务
    # 注意: 使用 threaded=False 避免多线程访问 CUDA
    app.run(
        host="0.0.0.0",
        port=8199,
        threaded=False,
        debug=False
    )
