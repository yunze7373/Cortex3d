#!/usr/bin/env python3
"""
UltraShape 通用细化模块
支持细化任何 3D 重建模型的输出：InstantMesh、TripoSR、TRELLIS.2、Hunyuan3D 等

用法:
    # 细化单个网格文件
    python run_ultrashape.py --image image.png --mesh mesh.glb --output outputs/refined
    
    # 细化 InstantMesh 输出
    python run_ultrashape.py --image image.png --mesh outputs/instantmesh/latest.obj
    
    # 快速预览模式（低显存）
    python run_ultrashape.py --image image.png --mesh mesh.glb --preset fast
    
    # 高质量模式
    python run_ultrashape.py --image image.png --mesh mesh.glb --preset high
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import gc

import torch
import numpy as np
from PIL import Image

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 路径配置
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
ULTRASHAPE_ROOT = Path("/opt/ultrashape")  # Docker 容器内路径

# 添加 UltraShape 到 Python 路径
if ULTRASHAPE_ROOT.exists():
    sys.path.insert(0, str(ULTRASHAPE_ROOT))
    logging.info(f"✓ UltraShape 模块路径: {ULTRASHAPE_ROOT}")
else:
    logging.warning(f"⚠ UltraShape 未安装在 {ULTRASHAPE_ROOT}")
    logging.warning("  提示: 请使用 'make build-ultrashape' 构建 Docker 容器")

# 质量预设配置
QUALITY_PRESETS = {
    "lowmem": {
        "steps": 20,
        "num_latents": 4096,
        "octree_res": 384,
        "chunk_size": 1024,
        "num_surface_points": 102400,
        "description": "低内存模式（~1分钟，6GB VRAM）",
        "low_vram": True,
        "max_memory_gb": 6
    },
    "fast": {
        "steps": 12,
        "num_latents": 8192,
        "octree_res": 512,
        "chunk_size": 2048,
        "num_surface_points": 204800,
        "description": "快速预览（~30秒，8GB VRAM）",
        "low_vram": True,
        "max_memory_gb": 8
    },
    "balanced": {
        "steps": 30,
        "num_latents": 12288,
        "octree_res": 640,
        "chunk_size": 2048,
        "num_surface_points": 204800,
        "description": "标准质量（~2分钟，峰值14GB VRAM，适合16GB显卡）",
        "low_vram": True,
        "max_memory_gb": 14  # 严格峰值控制
    },
    "high": {
        "steps": 50,
        "num_latents": 32768,
        "octree_res": 1024,
        "chunk_size": 8000,
        "num_surface_points": 409600,
        "description": "高质量（~5分钟，24GB VRAM）",
        "max_memory_gb": 24
    },
    "ultra": {
        "steps": 100,
        "num_latents": 32768,
        "octree_res": 2048,
        "chunk_size": 10000,
        "num_surface_points": 409600,
        "description": "超高质量（~10分钟，32GB VRAM）",
        "max_memory_gb": 32
    }
}


def check_dependencies():
    """检查必要依赖"""
    try:
        from omegaconf import OmegaConf
        from ultrashape.pipelines import UltraShapePipeline
        from ultrashape.surface_loaders import SharpEdgeSurfaceLoader
        from ultrashape.utils.misc import instantiate_from_config
        from ultrashape.utils import voxelize_from_point
        logging.info("✓ UltraShape 依赖加载成功")
        
        # 应用 dtype 修复补丁
        apply_dtype_fix()
        
        return True
    except ImportError as e:
        logging.error(f"✗ 缺少依赖: {e}")
        logging.error("  请确保在正确的 Docker 容器中运行")
        return False


def apply_dtype_fix():
    """
    修复 UltraShape 混合精度问题
    RuntimeError: expected scalar type Float but found Half
    """
    try:
        import torch.nn as nn
        import torch.nn.functional as F
        from ultrashape.models.denoisers import dit_mask
        
        # 1. 修复 scaled_dot_product_attention
        original_sdpa = F.scaled_dot_product_attention
        
        def patched_sdpa(query, key, value, attn_mask=None, dropout_p=0.0, is_causal=False, scale=None):
            """确保 q, k, v 类型一致为 float32"""
            query = query.float()
            key = key.float()
            value = value.float()
            if attn_mask is not None:
                attn_mask = attn_mask.float()
            return original_sdpa(
                query, key, value,
                attn_mask=attn_mask,
                dropout_p=dropout_p,
                is_causal=is_causal,
                scale=scale
            )
        
        F.scaled_dot_product_attention = patched_sdpa
        
        # 2. 修复 F.linear 函数（MoE 层使用）
        original_f_linear = F.linear
        
        def patched_f_linear(input, weight, bias=None):
            """强制 F.linear 输入权重都为 float32"""
            input = input.float()
            weight = weight.float()
            if bias is not None:
                bias = bias.float()
            return original_f_linear(input, weight, bias)
        
        F.linear = patched_f_linear
        
        # 3. 修复所有 nn.Linear 模块
        original_linear_forward = nn.Linear.forward
        
        def patched_linear_forward(self, input):
            """强制线性层输入输出为 float32"""
            if self.weight.dtype != torch.float32:
                self.weight.data = self.weight.data.float()
            if self.bias is not None and self.bias.dtype != torch.float32:
                self.bias.data = self.bias.data.float()
            input = input.float()
            return original_linear_forward(self, input)
        
        nn.Linear.forward = patched_linear_forward
        
        # 4. 修复 LayerNorm 层
        original_layernorm_forward = nn.LayerNorm.forward
        
        def patched_layernorm_forward(self, input):
            """强制 LayerNorm 输入输出为 float32"""
            if self.weight is not None and self.weight.dtype != torch.float32:
                self.weight.data = self.weight.data.float()
            if self.bias is not None and self.bias.dtype != torch.float32:
                self.bias.data = self.bias.data.float()
            input = input.float()
            return original_layernorm_forward(self, input)
        
        nn.LayerNorm.forward = patched_layernorm_forward
        
        logging.info("✓ UltraShape dtype 修复补丁已应用 (SDPA + F.linear + nn.Linear + LayerNorm)")
        
    except Exception as e:
        logging.warning(f"⚠ dtype 补丁应用失败: {e}")
        logging.warning("  将尝试继续运行，但可能会遇到 dtype 错误")


def check_dependencies():
    """检查必要依赖"""
    try:
        from omegaconf import OmegaConf
        from ultrashape.pipelines import UltraShapePipeline
        from ultrashape.surface_loaders import SharpEdgeSurfaceLoader
        from ultrashape.utils.misc import instantiate_from_config
        from ultrashape.utils import voxelize_from_point
        logging.info("✓ UltraShape 依赖加载成功")
        
        # 应用 dtype 修复补丁
        apply_dtype_fix()
        
        return True
    except ImportError as e:
        logging.error(f"✗ 缺少依赖: {e}")
        logging.error("  请确保在正确的 Docker 容器中运行")
        return False


def load_ultrashape_pipeline(config_path, ckpt_path, device='cuda', low_vram=False):
    """加载 UltraShape 流水线"""
    from omegaconf import OmegaConf
    from ultrashape.utils.misc import instantiate_from_config
    from ultrashape.pipelines import UltraShapePipeline
    
    logging.info("正在加载 UltraShape 模型...")
    
    # 加载配置
    config = OmegaConf.load(config_path)
    
    # 实例化模型组件
    logging.info("  - 加载 VAE...")
    vae = instantiate_from_config(config.model.params.vae_config)
    
    logging.info("  - 加载 DiT...")
    dit = instantiate_from_config(config.model.params.dit_cfg)
    
    logging.info("  - 加载调度器...")
    scheduler = instantiate_from_config(config.model.params.scheduler_cfg)
    
    logging.info("  - 加载条件编码器...")
    conditioner = instantiate_from_config(config.model.params.conditioner_config)
    
    logging.info("  - 加载图像处理器...")
    image_processor = instantiate_from_config(config.model.params.image_processor_cfg)
    
    # 加载权重
    logging.info(f"  - 加载权重: {ckpt_path}")
    if not Path(ckpt_path).exists():
        raise FileNotFoundError(f"权重文件不存在: {ckpt_path}")
    
    weights = torch.load(ckpt_path, map_location='cpu')
    
    # 强制转换权重为 float32（权重文件可能保存为 float16）
    logging.info("  - 转换权重为 float32...")
    for key in ['vae', 'dit', 'conditioner']:
        if key in weights:
            for param_key in weights[key]:
                if torch.is_tensor(weights[key][param_key]):
                    weights[key][param_key] = weights[key][param_key].float()
    
    vae.load_state_dict(weights['vae'], strict=True)
    dit.load_state_dict(weights['dit'], strict=True)
    conditioner.load_state_dict(weights['conditioner'], strict=True)
    
    # 移动到设备并强制 float32
    vae.to(device).float()
    dit.to(device).float()
    conditioner.to(device).float()
    
    # 递归强制所有子模块、参数和缓冲区都是 float32
    def force_float32(module):
        """递归强制模块所有组件转换为 float32"""
        module.float()
        for child in module.children():
            force_float32(child)
        for param in module.parameters(recurse=False):
            param.data = param.data.float()
        for buffer in module.buffers(recurse=False):
            buffer.data = buffer.data.float()
    
    logging.info("  - 强制转换所有模型组件为 float32...")
    force_float32(vae)
    force_float32(dit)
    force_float32(conditioner)
    
    # 设置为评估模式
    vae.eval()
    dit.eval()
    conditioner.eval()
    
    # 启用 FlashVDM 加速（如果可用）
    if hasattr(vae, 'enable_flashvdm_decoder'):
        # vae.enable_flashvdm_decoder()
        logging.info("  ✓ FlashVDM 加速已跳过 (强制 Float32)")
    
    # 创建流水线
    logging.info("  - 创建推理流水线...")
    pipeline = UltraShapePipeline(
        vae=vae,
        model=dit,
        scheduler=scheduler,
        conditioner=conditioner,
        image_processor=image_processor
    )
    
    # 低显存优化
    if low_vram:
        pipeline.enable_model_cpu_offload()
        logging.info("  ✓ 低显存模式已启用（CPU offloading）")
        
        # 尝试启用梯度检查点（如果可用）
        try:
            if hasattr(dit, 'enable_gradient_checkpointing'):
                dit.enable_gradient_checkpointing()
                logging.info("  ✓ 梯度检查点已启用")
        except Exception as e:
            logging.debug(f"  - 梯度检查点不可用: {e}")
    
    logging.info("✓ UltraShape 流水线加载完成")
    return pipeline, config


def load_surface_from_mesh(mesh_path, normalize_scale=0.99, num_points=409600):
    """从网格文件加载表面点云"""
    from ultrashape.surface_loaders import SharpEdgeSurfaceLoader
    
    logging.info(f"正在加载网格: {mesh_path}")
    
    # 初始化表面加载器 - 可配置采样点数
    # 分配：50% 均匀采样 + 50% 尖锐边缘采样
    num_sharp = num_points // 2
    num_uniform = num_points - num_sharp
    
    logging.info(f"  - 采样点数: {num_points} (均匀: {num_uniform}, 边缘: {num_sharp})")
    
    loader = SharpEdgeSurfaceLoader(
        num_sharp_points=num_sharp,
        num_uniform_points=num_uniform
    )
    
    # 加载并采样网格
    surface_pcd = loader(str(mesh_path))
    
    # 归一化
    if normalize_scale != 1.0:
        surface_pcd = surface_pcd * normalize_scale
    
    logging.info(f"  ✓ 表面点云加载完成: {surface_pcd.shape}")
    return surface_pcd


def refine_mesh(
    image_path,
    mesh_path,
    output_dir,
    ckpt_path="checkpoints/ultrashape_v1.pt",
    config_path="configs/infer_dit_refine.yaml",
    preset="balanced",
    steps=None,
    num_latents=None,
    octree_res=None,
    chunk_size=None,
    guidance_scale=5.0,
    scale=0.99,
    seed=42,
    low_vram=False,
    remove_bg=False
):
    """
    UltraShape 细化主函数
    
    Args:
        image_path: 参考图像路径
        mesh_path: 粗糙网格路径（.glb/.obj）
        output_dir: 输出目录
        preset: 质量预设 (fast/balanced/high/ultra)
        steps: 推理步数（覆盖预设）
        num_latents: 潜在 token 数量（覆盖预设）
        octree_res: Marching Cubes 分辨率（覆盖预设）
        chunk_size: 批处理块大小（覆盖预设）
        low_vram: 低显存模式
    """
    
    # 检查依赖
    if not check_dependencies():
        return None
    
    from ultrashape.utils import voxelize_from_point
    from ultrashape.rembg import BackgroundRemover
    import trimesh
    
    # 设置随机种子
    torch.manual_seed(seed)
    np.random.seed(seed)
    
    # 应用质量预设
    if preset in QUALITY_PRESETS:
        preset_config = QUALITY_PRESETS[preset]
        logging.info(f"📊 使用质量预设: {preset} - {preset_config['description']}")
        
        steps = steps or preset_config["steps"]
        num_latents = num_latents or preset_config["num_latents"]
        octree_res = octree_res or preset_config["octree_res"]
        chunk_size = chunk_size or preset_config["chunk_size"]
        num_surface_points = preset_config.get("num_surface_points", 409600)
        max_memory_gb = preset_config.get("max_memory_gb", None)
        
        # 如果预设启用低显存模式，强制开启
        if preset_config.get("low_vram", False):
            low_vram = True
            logging.info("  ⚙️  自动启用 CPU offloading (低显存优化)")
    else:
        logging.warning(f"未知预设 '{preset}'，使用默认值")
        steps = steps or 30
        num_latents = num_latents or 16384
        octree_res = octree_res or 768
        chunk_size = chunk_size or 4000
        num_surface_points = 409600
        max_memory_gb = None
    
    # 设备配置
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logging.info(f"🖥️  设备: {device}")
    
    # 设置严格的显存限制
    if max_memory_gb and torch.cuda.is_available():
        max_memory_bytes = int(max_memory_gb * 1024 * 1024 * 1024)
        torch.cuda.set_per_process_memory_fraction(max_memory_gb / 16.0)  # 假设16GB显卡
        logging.info(f"  🔒 严格限制显存: {max_memory_gb}GB (峰值保护)")
        
        # 设置 PyTorch 缓存分配器为保守模式
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    
    # 确保路径存在
    mesh_path = Path(mesh_path)
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not mesh_path.exists():
        raise FileNotFoundError(f"网格文件不存在: {mesh_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    # 加载配置路径
    config_path = ULTRASHAPE_ROOT / config_path
    ckpt_path = Path(ckpt_path)
    if not ckpt_path.is_absolute():
        # 尝试多个可能的路径
        possible_paths = [
            Path("/workspace/checkpoints") / ckpt_path.name,
            Path("/workspace/models/ultrashape") / ckpt_path.name,
            ULTRASHAPE_ROOT / ckpt_path,
            Path("models/ultrashape") / ckpt_path.name  # 相对路径 fallback
        ]
        
        found = False
        for p in possible_paths:
            if p.exists():
                ckpt_path = p
                found = True
                logging.info(f"  ✓ 找到权重文件: {ckpt_path}")
                break
        
        if not found:
            # 默认回退到 ULTRASHAPE_ROOT，让后续报错
            ckpt_path = ULTRASHAPE_ROOT / ckpt_path
    
    if not config_path.exists():
        logging.error(f"配置文件不存在: {config_path}")
        return None
    
    # 加载流水线
    pipeline, config = load_ultrashape_pipeline(
        config_path=str(config_path),
        ckpt_path=str(ckpt_path),
        device=device,
        low_vram=low_vram
    )
    
    # 获取体素分辨率
    voxel_res = config.model.params.vae_config.params.voxel_query_res
    logging.info(f"📐 体素分辨率: {voxel_res}")
    
    # 加载表面点云
    surface_pcd = load_surface_from_mesh(mesh_path, normalize_scale=scale, num_points=num_surface_points)
    
    # 体素化条件
    logging.info(f"🧊 生成体素条件 (Token 数: {num_latents})...")
    voxel_cond, _ = voxelize_from_point(
        surface_pcd[:, :, :3],
        resolution=voxel_res,
        num_latents=num_latents
    )
    
    # 低显存模式：先不移到 GPU
    if not low_vram:
        voxel_cond = voxel_cond.to(device)
    logging.info(f"  ✓ 体素条件: {voxel_cond.shape}")
    
    # 加载图像
    logging.info(f"🖼️  加载图像: {image_path}")
    image = Image.open(image_path)
    
    # 移除背景（如果需要）
    if remove_bg or image.mode != 'RGBA':
        logging.info("  - 移除背景...")
        rembg = BackgroundRemover()
        image = rembg(image)
    
    # 运行细化
    logging.info("\n" + "="*60)
    logging.info("🚀 开始 UltraShape 细化...")
    logging.info(f"  - 推理步数: {steps}")
    logging.info(f"  - 引导强度: {guidance_scale}")
    logging.info(f"  - 八叉树分辨率: {octree_res}")
    logging.info(f"  - 块大小: {chunk_size}")
    logging.info("="*60 + "\n")
    
    try:
        # 低显存模式：激进的内存清理
        if low_vram:
            gc.collect()
            torch.cuda.empty_cache()
            logging.info("  🧹 清理显存完成")
            
            # 强制同步，确保清理完成
            if torch.cuda.is_available():
                torch.cuda.synchronize()
        
        # 强制禁用 AMP 和梯度，确保全程 float32 + 无梯度
        with torch.cuda.amp.autocast(enabled=False), torch.no_grad():
            # 确保输入张量也是 float32
            if voxel_cond.dtype != torch.float32:
                voxel_cond = voxel_cond.float()
            
            # 低显存模式：分批移到 GPU
            if low_vram and voxel_cond.device.type != 'cuda':
                logging.info("  📦 分批加载到 GPU...")
                voxel_cond = voxel_cond.to(device)
                
                # 立即清理并同步
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                
                # 打印当前显存使用
                if torch.cuda.is_available():
                    allocated = torch.cuda.memory_allocated() / 1024**3
                    reserved = torch.cuda.memory_reserved() / 1024**3
                    logging.info(f"  💾 显存: {allocated:.2f}GB 已用, {reserved:.2f}GB 已保留")
            
            outputs = pipeline(
                image=image,
                voxel_cond=voxel_cond,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                octree_resolution=octree_res,
                num_chunks=chunk_size,
                output_type="trimesh",
                enable_pbar=True
            )
        
        # 保存结果
        output_name = mesh_path.stem + "_refined"
        output_path = output_dir / f"{output_name}.glb"
        
        logging.info(f"\n💾 保存细化网格: {output_path}")
        outputs[0].export(str(output_path))
        
        # 也保存为 OBJ 格式（兼容性）
        obj_path = output_dir / f"{output_name}.obj"
        outputs[0].export(str(obj_path))
        logging.info(f"  - OBJ 格式: {obj_path}")
        
        # 输出统计信息
        mesh = outputs[0]
        logging.info("\n" + "="*60)
        logging.info("✅ 细化完成！")
        logging.info(f"  - 顶点数: {len(mesh.vertices):,}")
        logging.info(f"  - 面数: {len(mesh.faces):,}")
        logging.info(f"  - 输出路径: {output_path}")
        logging.info("="*60 + "\n")
        
        # 清理显存
        gc.collect()
        torch.cuda.empty_cache()
        
        return str(output_path)
        
    except Exception as e:
        logging.error(f"✗ 细化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="UltraShape 通用细化模块 - 支持所有 3D 重建模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 细化 InstantMesh 输出
  python run_ultrashape.py --image test.png --mesh outputs/instantmesh/latest.obj
  
  # 细化 TRELLIS.2 输出（高质量）
  python run_ultrashape.py --image test.png --mesh outputs/trellis2/mesh.glb --preset high
  
  # 细化 Hunyuan3D 输出（快速预览）
  python run_ultrashape.py --image test.png --mesh outputs/hunyuan3d/mesh.glb --preset fast --low-vram
  
  # 自定义参数
  python run_ultrashape.py --image test.png --mesh mesh.glb --steps 100 --octree-res 2048
        """
    )
    
    # 必需参数
    parser.add_argument("--image", required=True, help="参考图像路径")
    parser.add_argument("--mesh", required=True, help="输入网格路径（.glb/.obj）")
    
    # 输出配置
    parser.add_argument("--output", default="outputs/ultrashape", help="输出目录")
    parser.add_argument("--ckpt", default="checkpoints/ultrashape_v1.pt", help="模型权重路径")
    parser.add_argument("--config", default="configs/infer_dit_refine.yaml", help="配置文件路径")
    
    # 质量预设
    parser.add_argument(
        "--preset",
        choices=["lowmem", "fast", "balanced", "high", "ultra"],
        default="balanced",
        help="质量预设 (lowmem: 6GB峰值, fast: 8GB峰值, balanced: 14GB峰值, high: 20GB, ultra: 32GB)"
    )
    
    # 高级参数（覆盖预设）
    parser.add_argument("--steps", type=int, help="推理步数（覆盖预设）")
    parser.add_argument("--num-latents", type=int, help="潜在 token 数量（覆盖预设）")
    parser.add_argument("--octree-res", type=int, help="Marching Cubes 分辨率（覆盖预设）")
    parser.add_argument("--chunk-size", type=int, help="批处理块大小（覆盖预设）")
    parser.add_argument("--guidance-scale", type=float, default=5.0, help="CFG 引导强度")
    parser.add_argument("--scale", type=float, default=0.99, help="网格归一化比例")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    
    # 优化选项
    parser.add_argument("--low-vram", action="store_true", help="启用低显存模式（CPU offloading）")
    parser.add_argument("--remove-bg", action="store_true", help="自动移除图像背景")
    
    args = parser.parse_args()
    
    # 显示预设信息
    if args.preset:
        preset_info = QUALITY_PRESETS.get(args.preset, {})
        print(f"\n{'='*60}")
        print(f"🎯 质量预设: {args.preset.upper()}")
        print(f"   {preset_info.get('description', 'N/A')}")
        print(f"{'='*60}\n")
    
    # 执行细化
    result = refine_mesh(
        image_path=args.image,
        mesh_path=args.mesh,
        output_dir=args.output,
        ckpt_path=args.ckpt,
        config_path=args.config,
        preset=args.preset,
        steps=args.steps,
        num_latents=args.num_latents,
        octree_res=args.octree_res,
        chunk_size=args.chunk_size,
        guidance_scale=args.guidance_scale,
        scale=args.scale,
        seed=args.seed,
        low_vram=args.low_vram,
        remove_bg=args.remove_bg
    )
    
    if result:
        print(f"\n🎉 细化成功！输出: {result}")
        return 0
    else:
        print("\n❌ 细化失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
