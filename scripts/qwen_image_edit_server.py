#!/usr/bin/env python3
"""
Qwen-Image-Edit 本地推理服务
提供 REST API 用于图像编辑

模型: Qwen/Qwen-Image-Edit (20B参数)
- 支持语义编辑和外观编辑
- 精确的文字编辑能力
- 中英文双语支持

API 端点:
- GET  /health - 健康检查
- POST /edit   - 图像编辑
- GET  /info   - 模型信息

量化说明:
- diffusers 的 BitsAndBytesConfig 只能用于单个模型组件(如 transformer)
- 不能直接对整个 Pipeline 使用量化配置
- 正确做法：分别加载并量化 transformer 和 text_encoder，再组装 Pipeline
"""

import os
import sys
import time
import base64
from io import BytesIO
from datetime import datetime

import torch
from flask import Flask, request, jsonify

app = Flask(__name__)

# 全局变量
pipe = None
model_loaded = False
quantization_mode = "none"  # "8bit", "4bit", "none"
USE_QUANTIZATION = os.environ.get("USE_QUANTIZATION", "true").lower() == "true"
QUANTIZATION_BITS = os.environ.get("QUANTIZATION_BITS", "8")  # "8" 或 "4"


def load_model():
    """加载 Qwen-Image-Edit 模型"""
    global pipe, model_loaded, quantization_mode
    
    print("\n" + "=" * 60)
    print("🚀 Qwen-Image-Edit 本地推理服务")
    print("=" * 60)
    print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 PyTorch: {torch.__version__}")
    print(f"🎮 CUDA: {torch.cuda.is_available()}")
    
    total_vram = 0
    if torch.cuda.is_available():
        total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {total_vram:.1f} GB")
    
    print(f"\n📦 正在加载 Qwen-Image-Edit 模型...")
    print(f"   来源: Qwen/Qwen-Image-Edit (HuggingFace)")
    print(f"   参数: 20B")
    print(f"   量化: {'启用 (' + QUANTIZATION_BITS + '-bit)' if USE_QUANTIZATION else '禁用'}")
    
    start_time = time.time()
    
    try:
        from diffusers import QwenImageEditPipeline
        
        model_id = "Qwen/Qwen-Image-Edit"
        
        # ====================================================================
        # 加载策略说明:
        # - 量化模式: 4-bit/8-bit 量化，直接放 GPU，不使用 CPU offload
        #   (量化模型与 CPU offload 不兼容，会报 meta tensor 错误)
        # - 非量化模式: 使用 CPU offload 节省显存，但推理较慢
        # ====================================================================
        
        if USE_QUANTIZATION:
            # ============================================================
            # 混合量化模式：Transformer 量化放 GPU，Text_Encoder 放 CPU
            # 这是 16GB 显卡的唯一可行方案！
            # 20B 模型即使全部 4-bit 量化也需要 ~12GB，加上推理激活值会 OOM
            # ============================================================
            print("\n   📦 使用混合量化模式...")
            print("      (Transformer-GPU量化 + TextEncoder-CPU)")
            
            try:
                from diffusers import BitsAndBytesConfig as DiffusersBitsAndBytesConfig
                from diffusers import AutoModel
                # 使用正确的 text_encoder 类型
                from transformers import Qwen2_5_VLForConditionalGeneration
                
                use_4bit = QUANTIZATION_BITS == "4"
                
                if use_4bit:
                    print("   🔧 Transformer: 4-bit NF4 量化")
                    diffusers_quant_config = DiffusersBitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16,
                        bnb_4bit_use_double_quant=True,
                    )
                    quantization_mode = "4bit-hybrid"
                else:
                    print("   🔧 Transformer: 8-bit 量化")
                    diffusers_quant_config = DiffusersBitsAndBytesConfig(
                        load_in_8bit=True,
                    )
                    quantization_mode = "8bit-hybrid"
                
                # 1. 量化加载 transformer → GPU
                print("   📦 [1/3] 加载 transformer (量化 → GPU)...")
                transformer_quantized = AutoModel.from_pretrained(
                    model_id,
                    subfolder="transformer",
                    quantization_config=diffusers_quant_config,
                    torch_dtype=torch.bfloat16,
                )
                print(f"      ✅ Transformer 已加载 (GPU, {quantization_mode})")
                
                # 清理显存
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    import gc
                    gc.collect()
                
                # 2. text_encoder 放 CPU (不量化)
                # 16GB 显卡无法同时在 GPU 放 transformer + text_encoder
                print("   📦 [2/3] 加载 text_encoder (CPU, bfloat16)...")
                text_encoder_cpu = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    model_id,
                    subfolder="text_encoder",
                    torch_dtype=torch.bfloat16,
                    device_map="cpu",
                    low_cpu_mem_usage=True,
                )
                print(f"      ✅ Text Encoder 已加载 (CPU)")
                
                # 3. 组装 Pipeline
                print("   📦 [3/3] 组装 Pipeline...")
                pipe = QwenImageEditPipeline.from_pretrained(
                    model_id,
                    transformer=transformer_quantized,
                    text_encoder=text_encoder_cpu,
                    torch_dtype=torch.bfloat16,
                    low_cpu_mem_usage=True,
                )
                
                # VAE 移到 GPU (较小，约 300MB)
                if hasattr(pipe, 'vae') and pipe.vae is not None:
                    pipe.vae = pipe.vae.to(dtype=torch.float16, device="cuda")
                
                # 启用显存优化
                try:
                    pipe.enable_xformers_memory_efficient_attention()
                    print("   ✅ xFormers 已启用")
                except Exception:
                    pass
                
                try:
                    if hasattr(pipe, 'enable_vae_slicing'):
                        pipe.enable_vae_slicing()
                    if hasattr(pipe, 'enable_vae_tiling'):
                        pipe.enable_vae_tiling()
                except Exception:
                    pass
                
                print(f"\n   ✅ 混合模式就绪!")
                print(f"      Transformer: GPU (量化)")
                print(f"      TextEncoder: CPU (推理时会较慢)")
                print(f"      VAE: GPU (fp16)")
                
            except Exception as e:
                print(f"   ⚠️ 量化加载失败: {e}")
                import traceback
                traceback.print_exc()
                
                # 回退到非量化 + CPU Offload 模式
                print("   🔄 回退到非量化 + CPU Offload 模式...")
                quantization_mode = "none"
                
                pipe = QwenImageEditPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.bfloat16,
                    low_cpu_mem_usage=True,
                )
                print("   🔄 启用 Sequential CPU Offload (慢但稳定)...")
                pipe.enable_sequential_cpu_offload()
        else:
            # ============================================================
            # 非量化模式: 使用 CPU Offload 节省显存
            # ============================================================
            print("   📦 非量化模式加载...")
            pipe = QwenImageEditPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
            )
            
            if total_vram < 40:
                print(f"   ⚠️ GPU 显存 ({total_vram:.1f}GB) 不足完全加载 20B 模型")
                print("   🔄 启用 Sequential CPU Offload...")
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.to("cuda")
        
        pipe.set_progress_bar_config(disable=True)

        
        load_time = time.time() - start_time
        model_loaded = True
        
        print(f"\n✅ 模型加载完成! 耗时: {load_time:.1f}秒")
        print("🌐 服务地址: http://0.0.0.0:8200")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@app.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "status": "ok" if model_loaded else "loading",
        "model": "Qwen-Image-Edit",
        "cuda": torch.cuda.is_available(),
        "quantization": quantization_mode,
    })


@app.route("/info", methods=["GET"])
def info():
    """模型信息"""
    quant_desc = {
        "8bit-hybrid": "8-bit 混合 (Transformer-GPU + TextEncoder-CPU)",
        "4bit-hybrid": "4-bit 混合 (Transformer-GPU + TextEncoder-CPU)",
        "8bit": "8-bit 全量化 (需24GB+显存)",
        "4bit": "4-bit 全量化 (需20GB+显存)",
        "none": "bfloat16 + CPU Offload"
    }.get(quantization_mode, quantization_mode)
    
    return jsonify({
        "model": "Qwen-Image-Edit",
        "developer": "Alibaba Qwen (阿里巴巴通义)",
        "parameters": "20B",
        "quantization": quant_desc,
        "quantization_mode": quantization_mode,
        "features": [
            "语义编辑 (对象旋转、风格转换)",
            "外观编辑 (添加/删除/修改元素)",
            "精确文字编辑",
            "中英文双语支持",
        ],
        "endpoints": [
            {"method": "GET", "path": "/health", "description": "健康检查"},
            {"method": "POST", "path": "/edit", "description": "图像编辑"},
            {"method": "GET", "path": "/info", "description": "模型信息"},
        ],
        "gpu": {
            "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1) if torch.cuda.is_available() else None,
        },
        "limits": {
            "default_max_size": 768,
            "default_steps": 28,
            "recommended": {
                "16GB_hybrid": {"max_size": 768, "steps": 28, "note": "Transformer-GPU + TextEncoder-CPU"},
                "24GB_4bit": {"max_size": 1024, "steps": 50},
                "48GB": {"max_size": 1536, "steps": 50},
            },
            "memory_breakdown": {
                "transformer_4bit": "~8GB",
                "text_encoder_cpu": "~10GB RAM",
                "vae_fp16": "~0.3GB",
                "inference_activation": "~4-6GB (视分辨率)"
            }
        }
    })


@app.route("/edit", methods=["POST"])
def edit():
    """
    图像编辑
    
    POST JSON:
    {
        "prompt": "编辑指令 (支持中英文)",
        "image": "base64编码的输入图像",
        "cfg_scale": 4.0,        // 可选，默认 4.0
        "steps": 28,             // 可选，默认 28 (官方推荐 28-50)
        "seed": 42,              // 可选，随机种子
        "max_size": 1024         // 可选，最大图像尺寸 (默认1024，16GB+4bit可用)
    }
    
    返回:
    {
        "image": "base64编码的PNG图像",
        "width": 1024,
        "height": 1024,
        "seed": 42,
        "time": 5.23
    }
    """
    if not model_loaded:
        return jsonify({"error": "模型正在加载中，请稍后重试"}), 503
    
    try:
        from PIL import Image
        
        data = request.json or {}
        
        prompt = data.get("prompt", "")
        image_b64 = data.get("image", "")
        cfg_scale = float(data.get("cfg_scale", 4.0))
        # 默认 28 步，Qwen-Image-Edit 官方推荐 28-50 步
        steps = int(data.get("steps", 28))
        seed = data.get("seed", None)
        negative_prompt = data.get("negative_prompt", " ")
        # 最大图像尺寸 - 16GB显存+4bit建议768，24GB可用1024
        max_size = int(data.get("max_size", 768))
        
        if not prompt:
            return jsonify({"error": "prompt 参数是必需的"}), 400
        
        if not image_b64:
            return jsonify({"error": "image 参数是必需的 (base64编码)"}), 400
        
        # 解码输入图像
        try:
            if "base64," in image_b64:
                image_b64 = image_b64.split("base64,")[1]
            image_data = base64.b64decode(image_b64)
            input_image = Image.open(BytesIO(image_data)).convert("RGB")
        except Exception as e:
            return jsonify({"error": f"图像解码失败: {e}"}), 400
        
        # 记录原始尺寸
        original_width, original_height = input_image.size
        
        # ============================================================
        # 图像尺寸限制 - 防止显存溢出
        # 16GB 显存 + 4-bit 量化：建议最大 1024x1024
        # ============================================================
        if max(original_width, original_height) > max_size:
            # 按比例缩放，保持长边不超过 max_size
            if original_width > original_height:
                new_width = max_size
                new_height = int(original_height * max_size / original_width)
            else:
                new_height = max_size
                new_width = int(original_width * max_size / original_height)
            
            # 确保尺寸是 8 的倍数 (某些模型要求)
            new_width = (new_width // 8) * 8
            new_height = (new_height // 8) * 8
            
            input_image = input_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"   📐 图像缩放: {original_width}x{original_height} → {new_width}x{new_height}")
        
        # 生成器 (种子)
        if seed is None:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
        generator = torch.manual_seed(seed)
        
        width, height = input_image.size
        
        print(f"\n🎨 [{datetime.now().strftime('%H:%M:%S')}] 图像编辑请求")
        print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        print(f"   原始尺寸: {original_width}x{original_height}, 处理尺寸: {width}x{height}")
        print(f"   CFG: {cfg_scale}, 步数: {steps}, 种子: {seed}")
        
        # 清理显存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            import gc
            gc.collect()
        
        start_time = time.time()
        
        # 执行编辑
        # 使用 torch.cuda.amp.autocast 进一步节省显存
        with torch.inference_mode():
            with torch.cuda.amp.autocast(dtype=torch.bfloat16):
                output = pipe(
                    image=input_image,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    generator=generator,
                    true_cfg_scale=cfg_scale,
                    num_inference_steps=steps,
                )
        
        output_image = output.images[0]
        gen_time = time.time() - start_time
        
        # 清理显存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # 转 base64
        buffer = BytesIO()
        output_image.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        print(f"   ✅ 完成! 耗时: {gen_time:.2f}秒")
        
        return jsonify({
            "image": img_b64,
            "width": output_image.width,
            "height": output_image.height,
            "original_width": original_width,
            "original_height": original_height,
            "seed": seed,
            "time": round(gen_time, 2),
        })
        
    except torch.cuda.OutOfMemoryError:
        print("   ❌ CUDA 内存不足!")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return jsonify({
            "error": "GPU 内存不足，请尝试较小的图像或降低 max_size 参数 (默认 1024)",
            "hint": "可以在请求中添加 'max_size': 768 或更小的值"
        }), 507
        
    except RuntimeError as e:
        error_msg = str(e)
        print(f"   ❌ 运行时错误: {error_msg}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if "out of memory" in error_msg.lower():
            return jsonify({
                "error": "GPU 内存不足",
                "hint": "请在请求中添加 'max_size': 768 或更小的值来限制图像尺寸"
            }), 507
        import traceback
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500
        
    except Exception as e:
        print(f"   ❌ 编辑失败: {e}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 加载模型
    load_model()
    
    # 启动 Flask 服务
    app.run(host="0.0.0.0", port=8200, threaded=False)
