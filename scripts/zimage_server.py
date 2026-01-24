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
- GET  /health  - 健康检查
- POST /generate - 生成图像
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
        pipe.to("cuda")
        
        # 尝试启用 Flash Attention
        try:
            pipe.transformer.set_attention_backend("flash")
            print("   ✅ Flash Attention 2 已启用")
        except Exception as e:
            print(f"   ⚠️  Flash Attention 不可用，使用 SDPA: {e}")
        
        # 可选: 编译模型 (首次推理会慢，之后更快)
        # pipe.transformer.compile()
        
        load_time = time.time() - start_time
        print(f"\n✅ 模型加载完成! 耗时: {load_time:.1f}秒")
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
        ],
        "gpu": {
            "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1) if torch.cuda.is_available() else None,
        }
    })


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
