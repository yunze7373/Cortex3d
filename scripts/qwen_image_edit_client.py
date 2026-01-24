#!/usr/bin/env python3
"""
Qwen-Image-Edit 客户端
与本地 Qwen-Image-Edit 服务通信

用法:
    from qwen_image_edit_client import QwenImageEditClient
    
    client = QwenImageEditClient()
    result = client.edit(
        image_path="input.png",
        prompt="给这个人换上红色连衣裙",
        output_path="output.png"
    )
"""

import os
import sys
import base64
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    print("[WARNING] PIL 未安装，某些功能可能受限")
    Image = None

# 默认服务地址
DEFAULT_QWEN_EDIT_URL = os.environ.get("QWEN_IMAGE_EDIT_URL", "http://localhost:8200")


class QwenImageEditClient:
    """Qwen-Image-Edit 本地客户端"""
    
    def __init__(self, base_url: str = None):
        """
        初始化客户端
        
        Args:
            base_url: 服务地址，默认 http://localhost:8200
        """
        self.base_url = base_url or DEFAULT_QWEN_EDIT_URL
        self.timeout = 600  # 10分钟超时 (首次加载模型较慢，编辑也需要时间)
    
    def health_check(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            True 如果服务正常
        """
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status") == "ok"
            return False
        except:
            return False
    
    def wait_for_service(self, timeout: int = 600, interval: int = 10) -> bool:
        """
        等待服务启动
        
        Args:
            timeout: 最大等待时间(秒)
            interval: 检查间隔(秒)
        
        Returns:
            True 如果服务启动成功
        """
        import time
        
        print(f"⏳ 等待 Qwen-Image-Edit 服务启动...")
        print(f"   (首次启动需要下载模型，可能需要较长时间)")
        start = time.time()
        
        while time.time() - start < timeout:
            if self.health_check():
                print(f"✅ 服务已就绪!")
                return True
            print(f"   服务未就绪，{interval}秒后重试...")
            time.sleep(interval)
        
        print(f"❌ 服务启动超时 ({timeout}秒)")
        return False
    
    def edit(
        self,
        image_path: str,
        prompt: str,
        cfg_scale: float = 4.0,
        steps: int = 50,
        seed: int = None,
        output_path: str = None,
    ) -> Optional[str]:
        """
        编辑图像
        
        Args:
            image_path: 输入图像路径
            prompt: 编辑指令 (支持中英文)
            cfg_scale: CFG 缩放 (默认4.0)
            steps: 推理步数 (默认50)
            seed: 随机种子 (可选)
            output_path: 输出路径 (可选)
        
        Returns:
            保存的图像路径，失败返回 None
        """
        try:
            # 读取输入图像
            image_path = Path(image_path)
            if not image_path.exists():
                print(f"[ERROR] 输入图像不存在: {image_path}")
                return None
            
            # 读取并编码图像
            if Image:
                img = Image.open(image_path)
                # 确保是 RGB
                if img.mode != "RGB":
                    img = img.convert("RGB")
                # 转为 base64
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                image_b64 = base64.b64encode(buffer.getvalue()).decode()
                orig_size = img.size
            else:
                with open(image_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode()
                orig_size = None
            
            # 构建请求
            payload = {
                "prompt": prompt,
                "image": image_b64,
                "cfg_scale": cfg_scale,
                "steps": steps,
            }
            if seed is not None:
                payload["seed"] = seed
            
            print(f"[Qwen-Image-Edit] 图像编辑请求")
            print(f"   输入: {image_path.name}")
            print(f"   指令: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
            print(f"   参数: cfg={cfg_scale}, steps={steps}")
            
            response = requests.post(
                f"{self.base_url}/edit",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                try:
                    error = response.json().get("error", "未知错误")
                except:
                    error = response.text[:200]
                print(f"[ERROR] Qwen-Image-Edit 编辑失败: {error}")
                return None
            
            data = response.json()
            img_b64 = data.get("image")
            
            if not img_b64:
                print("[ERROR] 服务未返回图像")
                return None
            
            # 解码图像
            img_data = base64.b64decode(img_b64)
            img = Image.open(BytesIO(img_data))
            
            # 生成输出路径
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"outputs/qwen_edit_{timestamp}.png"
            
            # 确保目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存图像
            img.save(output_path)
            
            gen_time = data.get("time", 0)
            print(f"[Qwen-Image-Edit] ✅ 编辑完成: {output_path} (耗时: {gen_time}s)")
            return output_path
            
        except requests.exceptions.ConnectionError:
            print("[ERROR] 无法连接到 Qwen-Image-Edit 服务")
            print("       请确保 Docker 容器已启动:")
            print("       docker compose up -d qwen-image-edit")
            return None
            
        except requests.exceptions.Timeout:
            print("[ERROR] Qwen-Image-Edit 服务响应超时")
            return None
            
        except Exception as e:
            print(f"[ERROR] Qwen-Image-Edit 编辑失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def edit_image_local(
    image_path: str,
    prompt: str,
    output_dir: str = "test_images",
    cfg_scale: float = 4.0,
    steps: int = 50,
    seed: int = None,
) -> Optional[str]:
    """
    便捷函数：使用本地 Qwen-Image-Edit 服务编辑图像
    
    Args:
        image_path: 输入图像路径
        prompt: 编辑指令
        output_dir: 输出目录
        cfg_scale: CFG 缩放
        steps: 推理步数
        seed: 随机种子
    
    Returns:
        编辑后图像的路径
    """
    client = QwenImageEditClient()
    
    # 检查服务
    if not client.health_check():
        print("[ERROR] Qwen-Image-Edit 服务不可用")
        print("       请确保服务已启动: docker compose up -d qwen-image-edit")
        return None
    
    # 生成输出路径
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_dir}/qwen_edit_{timestamp}.png"
    
    return client.edit(
        image_path=image_path,
        prompt=prompt,
        cfg_scale=cfg_scale,
        steps=steps,
        seed=seed,
        output_path=output_path
    )


# 测试入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Qwen-Image-Edit 客户端测试")
    parser.add_argument("image", help="输入图像路径")
    parser.add_argument("prompt", help="编辑指令")
    parser.add_argument("--output", "-o", help="输出路径")
    parser.add_argument("--cfg", type=float, default=4.0, help="CFG 缩放")
    parser.add_argument("--steps", type=int, default=50, help="推理步数")
    parser.add_argument("--seed", type=int, help="随机种子")
    
    args = parser.parse_args()
    
    client = QwenImageEditClient()
    
    # 等待服务
    if not client.health_check():
        print("服务未就绪，等待启动...")
        if not client.wait_for_service():
            sys.exit(1)
    
    # 编辑图像
    result = client.edit(
        image_path=args.image,
        prompt=args.prompt,
        cfg_scale=args.cfg,
        steps=args.steps,
        seed=args.seed,
        output_path=args.output
    )
    
    if result:
        print(f"\n✅ 成功保存到: {result}")
    else:
        print("\n❌ 编辑失败")
        sys.exit(1)
