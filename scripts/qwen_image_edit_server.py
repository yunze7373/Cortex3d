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
USE_QUANTIZATION = os.environ.get("USE_QUANTIZATION", "true").lower() == "true"


def load_model():
    """加载 Qwen-Image-Edit 模型"""
    global pipe, model_loaded
    
    print("\n" + "=" * 60)
    print("🚀 Qwen-Image-Edit 本地推理服务")
    print("=" * 60)
    print(f"📅 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 PyTorch: {torch.__version__}")
    print(f"🎮 CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    print(f"\n📦 正在加载 Qwen-Image-Edit 模型...")
    print(f"   来源: Qwen/Qwen-Image-Edit (HuggingFace)")
    print(f"   参数: 20B")
    print(f"   量化: {'8-bit (bitsandbytes)' if USE_QUANTIZATION else '原始精度'}")
    
    start_time = time.time()
    
    try:
        from diffusers import QwenImageEditPipeline
        
        # 模型加载配置
        model_id = "Qwen/Qwen-Image-Edit"
        
        if USE_QUANTIZATION:
            # 使用 8-bit 量化减少显存
            try:
                # 尝试从 diffusers 不同路径导入量化配置
                quantization_config_cls = None
                try:
                    from diffusers import BitsAndBytesConfig
                    quantization_config_cls = BitsAndBytesConfig
                except ImportError:
                    try:
                        from diffusers.utils import BitsAndBytesConfig
                        quantization_config_cls = BitsAndBytesConfig
                    except ImportError:
                        try:
                            from diffusers.quantizers import BitsAndBytesConfig
                            quantization_config_cls = BitsAndBytesConfig
                        except ImportError:
                            pass
                
                if quantization_config_cls:
                    print(f"   📦 使用量化配置类: {quantization_config_cls.__module__}.{quantization_config_cls.__name__}")
                    quantization_config = quantization_config_cls(
                        load_in_8bit=True,
                        bnb_8bit_compute_dtype=torch.bfloat16,
                    )
                    
                    pipe = QwenImageEditPipeline.from_pretrained(
                        model_id,
                        torch_dtype=torch.bfloat16,
                        quantization_config=quantization_config,
                        low_cpu_mem_usage=True,
                    )
                    print("   ✅ 8-bit 量化模式已启用")
                else:
                    raise ImportError("无法找到 diffusers.BitsAndBytesConfig")
                
            except Exception as e:
                print(f"   ⚠️ 量化加载失败: {e}")
                print("   🔄 尝试 transformers 量化配置回退...")
                
                # 回退方案：分别加载组件
                # Qwen-Image-Edit = Tokenizer + Text Encoder (Qwen2-VL) + VAE + Transformer + Scheduler
                try:
                    from transformers import BitsAndBytesConfig as TrBitsAndBytesConfig
                    from transformers import Qwen2_5_VLForConditionalGeneration, AutoTokenizer
                    from diffusers import AutoencoderKL, QwenImageEditPipeline
                    
                    print("   📦 手动加载并量化组件...")
                    
                    # 1. 量化 Text Encoder (这是显存大户)
                    bnb_config = TrBitsAndBytesConfig(
                        load_in_8bit=True,
                        bnb_8bit_compute_dtype=torch.bfloat16
                    )
                    
                    # 注意: Qwen-Image-Edit 可能使用特定的子文件夹
                    # 我们尝试从 pipeline 配置中推断或者直接加载
                    # 这里为了保险，还是尝试直接回退到标准模式但开启更激进的 offload
                    # 因为手动拼装 pipeline 风险很大，且容易出错
                    print("   ⚠️ 组件分离加载过于复杂，转为标准模式 + CPU Offload")
                    raise e
                    
                except Exception as e2:
                    print(f"   ⚠️ 最终量化失败: {e2}")
                    print("   🔄 回退到标准模式 (Sequential CPU Offload)...")
                    
                    # 尝试加载 pipeline (不带量化)，但开启 low_cpu_mem_usage
                    # 如果只有 16GB VRAM，全量加载可能会在 to("cuda") 时失败
                    # 所以我们先加载到 CPU，然后 enable_sequential_cpu_offload
                    pipe = QwenImageEditPipeline.from_pretrained(
                        model_id,
                        torch_dtype=torch.bfloat16,
                        low_cpu_mem_usage=True,
                        device_map="balance" # 尝试让 accelerate 自动分配
                    )
                    # 不要调用 pipe.to("cuda")，而是使用 offload
                    pass
        else:
            # 标准加载
            pipe = QwenImageEditPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
            )
            pipe.to("cuda")
        
        # 检查是否需要 CPU offload
        if torch.cuda.is_available():
            total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if total_vram < 20: # 20GB 以下都建议开启 offload，除非已经量化且很小
                # 检查是否已量化
                is_quantized = hasattr(pipe, "quantization_config") and pipe.quantization_config is not None
                
                if not is_quantized:
                    print(f"   ⚠️ GPU 显存 ({total_vram:.1f}GB) 可能不足以运行 20B 模型(非量化)")
                    print("   🔄 启用 Sequential CPU Offload (速度较慢但省显存)...")
                    pipe.enable_sequential_cpu_offload()
                elif total_vram < 10: # 即便是 8-bit，如果显存小于 10GB 也要小心
                    print(f"   ⚠️ 显存紧张，启用 Model CPU Offload...")
                    pipe.enable_model_cpu_offload()
        
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
        "quantized": USE_QUANTIZATION,
    })


@app.route("/info", methods=["GET"])
def info():
    """模型信息"""
    return jsonify({
        "model": "Qwen-Image-Edit",
        "developer": "Alibaba Qwen (阿里巴巴通义)",
        "parameters": "20B",
        "quantization": "8-bit" if USE_QUANTIZATION else "bfloat16",
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
        "steps": 50,             // 可选，默认 50
        "seed": 42               // 可选，随机种子
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
        steps = int(data.get("steps", 50))
        seed = data.get("seed", None)
        negative_prompt = data.get("negative_prompt", " ")
        
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
        
        # 生成器 (种子)
        if seed is None:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
        generator = torch.manual_seed(seed)
        
        width, height = input_image.size
        
        print(f"\n🎨 [{datetime.now().strftime('%H:%M:%S')}] 图像编辑请求")
        print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        print(f"   尺寸: {width}x{height}, CFG: {cfg_scale}, 步数: {steps}, 种子: {seed}")
        
        start_time = time.time()
        
        # 执行编辑
        with torch.inference_mode():
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
        
        # 转 base64
        buffer = BytesIO()
        output_image.save(buffer, format="PNG")
        img_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        print(f"   ✅ 完成! 耗时: {gen_time:.2f}秒")
        
        return jsonify({
            "image": img_b64,
            "width": output_image.width,
            "height": output_image.height,
            "seed": seed,
            "time": round(gen_time, 2),
        })
        
    except torch.cuda.OutOfMemoryError:
        print("   ❌ CUDA 内存不足!")
        torch.cuda.empty_cache()
        return jsonify({"error": "GPU 内存不足，请尝试较小的图像"}), 507
        
    except Exception as e:
        print(f"   ❌ 编辑失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 加载模型
    load_model()
    
    # 启动 Flask 服务
    app.run(host="0.0.0.0", port=8200, threaded=False)
