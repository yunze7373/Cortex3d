#!/usr/bin/env python3
"""
Z-Image-Turbo 本地客户端
调用本地 Docker 部署的 Z-Image 模型

使用方式:
    from zimage_client import ZImageClient, generate_character_local
    
    # 方式1: 类接口
    client = ZImageClient()
    path = client.generate("一只可爱的橘猫")
    
    # 方式2: 函数接口 (兼容现有代码)
    path = generate_character_local("赛博朋克女战士", multi_view=True)
"""

import os
import sys
import requests
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
from PIL import Image
from io import BytesIO

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 默认本地服务地址
DEFAULT_ZIMAGE_URL = os.environ.get("ZIMAGE_URL", "http://localhost:8199")


class ZImageClient:
    """Z-Image-Turbo 本地客户端"""
    
    def __init__(self, base_url: str = None):
        """
        初始化客户端
        
        Args:
            base_url: 服务地址，默认 http://localhost:8199
        """
        self.base_url = base_url or DEFAULT_ZIMAGE_URL
        self.timeout = 300  # 5分钟超时 (首次加载模型可能较慢)
    
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
    
    def wait_for_service(self, timeout: int = 180, interval: int = 5) -> bool:
        """
        等待服务启动
        
        Args:
            timeout: 最大等待时间(秒)
            interval: 检查间隔(秒)
        
        Returns:
            True 如果服务启动成功
        """
        import time
        
        print(f"⏳ 等待 Z-Image 服务启动...")
        start = time.time()
        
        while time.time() - start < timeout:
            if self.health_check():
                print(f"✅ 服务已就绪!")
                return True
            print(f"   服务未就绪，{interval}秒后重试...")
            time.sleep(interval)
        
        print(f"❌ 服务启动超时 ({timeout}秒)")
        return False
    
    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 9,
        seed: int = None,
        output_path: str = None,
    ) -> Optional[str]:
        """
        生成单张图像
        
        Args:
            prompt: 提示词 (支持中英文)
            width: 图像宽度 (256-2048)
            height: 图像高度 (256-2048)
            steps: 推理步数 (默认9, 实际8次DiT前向)
            seed: 随机种子 (可选)
            output_path: 输出路径 (可选)
        
        Returns:
            保存的图像路径，失败返回 None
        """
        try:
            payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "steps": steps,
            }
            if seed is not None:
                payload["seed"] = seed
            
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error = response.json().get("error", "未知错误")
                print(f"[ERROR] Z-Image 生成失败: {error}")
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
                output_path = f"outputs/zimage_{timestamp}.png"
            
            # 确保目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存图像
            img.save(output_path)
            
            return output_path
            
        except requests.exceptions.ConnectionError:
            print("[ERROR] 无法连接到 Z-Image 服务")
            print("       请确保 Docker 容器已启动:")
            print("       docker compose up -d zimage")
            return None
            
        except requests.exceptions.Timeout:
            print("[ERROR] Z-Image 服务响应超时")
            return None
            
        except Exception as e:
            print(f"[ERROR] Z-Image 生成失败: {e}")
            return None
    
    def generate_multiview(
        self,
        character_description: str,
        style: str = "photorealistic",
        output_dir: str = "test_images",
        view_mode: str = "4-view",
        seed: int = None,
    ) -> Optional[str]:
        """
        生成多视角图像
        
        Args:
            character_description: 角色描述
            style: 风格
            output_dir: 输出目录
            view_mode: 视角模式 (4-view, 6-view, 8-view)
            seed: 随机种子
        
        Returns:
            保存的图像路径
        """
        # 尝试导入 Cortex3d 的提示词模板
        try:
            from config import build_multiview_prompt
            prompt = build_multiview_prompt(
                character_description,
                style=style,
                view_mode=view_mode
            )
        except ImportError:
            # 回退到简单模板
            prompt = self._build_simple_multiview_prompt(
                character_description, style, view_mode
            )
        
        # 多视角需要更宽的画布
        if view_mode == "4-view":
            width, height = 2048, 512
        elif view_mode == "6-view":
            width, height = 3072, 512
        else:  # 8-view
            width, height = 4096, 512
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{output_dir}/zimage_multiview_{timestamp}.png"
        
        return self.generate(
            prompt=prompt,
            width=width,
            height=height,
            seed=seed,
            output_path=output_path
        )
    
    def _build_simple_multiview_prompt(
        self,
        description: str,
        style: str,
        view_mode: str
    ) -> str:
        """构建简单的多视角提示词"""
        if view_mode == "4-view":
            views = "front view, left side view, back view, right side view"
        elif view_mode == "6-view":
            views = "front view, front-left view, left side view, back view, right side view, front-right view"
        else:
            views = "front view, front-left view, left side view, back-left view, back view, back-right view, right side view, front-right view"
        
        return f"""Character turnaround sheet showing {views} of the same character.
Character: {description}
Style: {style}, consistent design across all views, white background, professional character design reference sheet.
Each view clearly shows the character from different angles with identical outfit, proportions, and details."""


# =============================================================================
# 便捷函数 (兼容现有接口)
# =============================================================================

def generate_with_zimage(
    prompt: str,
    output_dir: str = "outputs",
    width: int = 1024,
    height: int = 1024,
    **kwargs
) -> Optional[str]:
    """
    使用本地 Z-Image 生成图像
    
    Args:
        prompt: 提示词
        output_dir: 输出目录
        width: 宽度
        height: 高度
        **kwargs: 其他参数 (steps, seed)
    
    Returns:
        图像路径
    """
    client = ZImageClient()
    
    if not client.health_check():
        print("[ERROR] Z-Image 服务不可用")
        print("       启动服务: docker compose up -d zimage")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_dir}/zimage_{timestamp}.png"
    
    return client.generate(
        prompt=prompt,
        width=width,
        height=height,
        output_path=output_path,
        **kwargs
    )


def generate_character_local(
    character_description: str,
    style: str = "photorealistic",
    output_dir: str = "test_images",
    multi_view: bool = False,
    view_mode: str = "4-view",
    seed: int = None,
    auto_cut: bool = True,
) -> Optional[str]:
    """
    使用本地 Z-Image 生成角色图像
    
    这个函数的接口设计与现有的 generate_character_views() 兼容
    
    Args:
        character_description: 角色描述
        style: 风格
        output_dir: 输出目录
        multi_view: 是否生成多视角
        view_mode: 视角模式
        seed: 随机种子
        auto_cut: 是否自动切割 (TODO)
    
    Returns:
        图像路径
    """
    client = ZImageClient()
    
    # 检查服务
    if not client.health_check():
        print("\n" + "=" * 50)
        print("❌ Z-Image 服务不可用")
        print("=" * 50)
        print("\n请启动服务:")
        print("  docker compose up -d zimage")
        print("\n或等待服务启动:")
        print("  make logs-zimage")
        print("=" * 50 + "\n")
        return None
    
    print(f"\n🖥️  使用本地 Z-Image-Turbo 生成")
    print(f"   角色: {character_description[:50]}{'...' if len(character_description) > 50 else ''}")
    print(f"   风格: {style}")
    print(f"   多视角: {'是 (' + view_mode + ')' if multi_view else '否'}")
    
    if multi_view:
        result = client.generate_multiview(
            character_description=character_description,
            style=style,
            output_dir=output_dir,
            view_mode=view_mode,
            seed=seed
        )
    else:
        # 单图生成
        prompt = f"{character_description}, {style} style, high quality, detailed, professional"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{output_dir}/zimage_character_{timestamp}.png"
        
        result = client.generate(
            prompt=prompt,
            width=1024,
            height=1024,
            seed=seed,
            output_path=output_path
        )
    
    if result:
        print(f"\n✅ 生成成功: {result}")
    else:
        print("\n❌ 生成失败")
    
    return result


# =============================================================================
# 命令行测试
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Z-Image-Turbo 客户端测试")
    parser.add_argument("prompt", nargs="?", default="一只可爱的橘猫，高清照片", help="提示词")
    parser.add_argument("--width", type=int, default=1024, help="宽度")
    parser.add_argument("--height", type=int, default=1024, help="高度")
    parser.add_argument("--steps", type=int, default=9, help="步数")
    parser.add_argument("--seed", type=int, default=None, help="种子")
    parser.add_argument("--output", "-o", default="outputs", help="输出目录")
    parser.add_argument("--multi-view", action="store_true", help="多视角模式")
    parser.add_argument("--url", default=None, help="服务地址")
    
    args = parser.parse_args()
    
    # 创建客户端
    client = ZImageClient(base_url=args.url)
    
    # 检查服务
    print("🔍 检查 Z-Image 服务...")
    if not client.health_check():
        print("❌ 服务不可用，尝试等待启动...")
        if not client.wait_for_service(timeout=60):
            sys.exit(1)
    
    # 生成
    if args.multi_view:
        result = client.generate_multiview(
            character_description=args.prompt,
            output_dir=args.output,
            seed=args.seed
        )
    else:
        result = client.generate(
            prompt=args.prompt,
            width=args.width,
            height=args.height,
            steps=args.steps,
            seed=args.seed,
            output_path=f"{args.output}/zimage_test.png"
        )
    
    if result:
        print(f"\n✅ 图像已保存: {result}")
    else:
        print("\n❌ 生成失败")
        sys.exit(1)
