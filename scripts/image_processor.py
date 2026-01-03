#!/usr/bin/env python3
"""
四视图图片处理器
将 Gemini 生成的四宫格图片切割为独立视图，并去除背景

使用方法:
    python image_processor.py input_image.png --output outputs/

依赖:
    pip install opencv-python pillow rembg onnxruntime
"""

import argparse
import os
from pathlib import Path
from typing import Tuple, List, Optional

# Lazy imports - only load when needed
cv2 = None
np = None
Image = None
remove_bg = None
REMBG_AVAILABLE = False


def _ensure_imports():
    """延迟导入依赖库"""
    global cv2, np, Image, remove_bg, REMBG_AVAILABLE
    
    if cv2 is None:
        try:
            import cv2 as _cv2
            import numpy as _np
            from PIL import Image as _Image
            cv2 = _cv2
            np = _np
            Image = _Image
        except ImportError as e:
            raise ImportError(
                f"缺少必要依赖: {e}\n"
                "请运行: pip install opencv-python pillow numpy"
            )
    
    if remove_bg is None:
        try:
            from rembg import remove as _remove_bg
            remove_bg = _remove_bg
            REMBG_AVAILABLE = True
        except ImportError:
            REMBG_AVAILABLE = False




def detect_layout_and_split(image, margin: int = 5) -> List[Tuple[str, any]]:
    """
    智能检测图片布局类型并切割
    
    支持两种布局:
    1. 2x2 田字格 (宽高比接近1:1 或 4:3)
    2. 1x4 横排 (宽高比约 4:1 或更宽)
    
    Args:
        image: 输入图片 (BGR 格式)
        margin: 切割边界收缩像素
    
    Returns:
        List of (view_name, image) tuples: [front, back, left, right]
    """
    _ensure_imports()
    height, width = image.shape[:2]
    aspect_ratio = width / height
    
    print(f"[INFO] 图片尺寸: {width}x{height}, 宽高比: {aspect_ratio:.2f}")
    
    # 判断布局类型
    # 1x4 横排: 宽高比 > 1.5 (如 1408x768 = 1.83)
    # 2x2 田字格: 宽高比 <= 1.5 (如 1024x1024 = 1.0 或 1024x768 = 1.33)
    if aspect_ratio > 1.5:
        # 1x4 横排布局
        print("[INFO] 检测到 1x4 横排布局")
        return split_horizontal_layout(image, margin)
    else:
        # 2x2 田字格布局
        print("[INFO] 检测到 2x2 田字格布局")
        return split_grid_layout(image, margin)


def find_dividing_lines(gray_image, axis: str, num_divisions: int) -> List[int]:
    """
    检测分割线位置
    
    Args:
        gray_image: 灰度图
        axis: 'horizontal' 或 'vertical'
        num_divisions: 期望的分割线数量
    
    Returns:
        分割线位置列表
    """
    _ensure_imports()
    
    if axis == 'vertical':
        # 检测垂直分割线 (沿x轴)
        profile = np.mean(gray_image, axis=0)  # 每列的平均亮度
    else:
        # 检测水平分割线 (沿y轴)
        profile = np.mean(gray_image, axis=1)  # 每行的平均亮度
    
    length = len(profile)
    
    # 寻找亮度峰值 (分割线通常是亮的)
    # 将图像分成 num_divisions+1 段，在每段边界附近寻找峰值
    dividers = []
    for i in range(1, num_divisions + 1):
        expected_pos = int(length * i / (num_divisions + 1))
        search_start = max(0, expected_pos - length // 10)
        search_end = min(length, expected_pos + length // 10)
        
        # 在搜索范围内找最亮的位置
        segment = profile[search_start:search_end]
        if len(segment) > 0:
            local_max_idx = np.argmax(segment)
            dividers.append(search_start + local_max_idx)
    
    return dividers


def split_horizontal_layout(image, margin: int = 5) -> List[Tuple[str, any]]:
    """
    切割 1x4 横排布局 - 使用固定几何分割
    """
    # _ensure_imports() # (already called by caller or globally)
    height, width = image.shape[:2]
    
    # 使用固定网格分割，比依靠亮度检测（find_dividing_lines）更可靠，
    # 尤其是在背景复杂或黑暗的情况下。AI生成图通常严格遵守栅格。
    dividers = [width // 4, width // 2, 3 * width // 4]
    
    # print(f"[INFO] 垂直分割线位置: {dividers}")
    
    x_positions = [0] + dividers + [width]
    
    views = []
    view_names = ['front', 'back', 'left', 'right']
    
    for i, name in enumerate(view_names):
        x1 = x_positions[i] + margin
        x2 = x_positions[i + 1] - margin
        y1 = margin
        y2 = height - margin
        
        # 边界检查
        x1 = max(0, x1)
        x2 = min(width, x2)
        y1 = max(0, y1)
        y2 = min(height, y2)
        
        if x2 > x1 and y2 > y1:
            cropped = image[y1:y2, x1:x2].copy()
            # print(f"[INFO] {name} 视图: {x2-x1}x{y2-y1}")
            views.append((name, cropped))
    
    return views


def split_grid_layout(image, margin: int = 5) -> List[Tuple[str, any]]:
    """
    切割 2x2 田字格布局 - 使用固定几何分割
    """
    height, width = image.shape[:2]
    
    # 强制中心分割
    x_split = width // 2
    y_split = height // 2
    
    # print(f"[INFO] 分割中心点: ({x_split}, {y_split})")
    
    # 定义四个区域
    regions = {
        'front': (margin, margin, x_split - margin, y_split - margin),
        'back': (x_split + margin, margin, width - margin, y_split - margin),
        'left': (margin, y_split + margin, x_split - margin, height - margin),
        'right': (x_split + margin, y_split + margin, width - margin, height - margin)
    }
    
    views = []
    # 顺序：前、后、左、右 (注意：田字格通常是 前后/左右 排列，但也取决于具体模型)
    # 假设标准 layout:
    # Front | Back
    # Left  | Right
    for name in ['front', 'back', 'left', 'right']:
        x1, y1, x2, y2 = regions[name]
        
        x1 = max(0, x1)
        x2 = min(width, x2)
        y1 = max(0, y1)
        y2 = min(height, y2)

        if x2 > x1 and y2 > y1:
            cropped = image[y1:y2, x1:x2].copy()
            # print(f"[INFO] {name} 视图: {x2-x1}x{y2-y1}")
            views.append((name, cropped))
    
    return views


# 保留旧函数名以保持兼容性
def detect_grid_split(image) -> Tuple[int, int]:
    """向后兼容的分割点检测函数"""
    _ensure_imports()
    height, width = image.shape[:2]
    
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    h_dividers = find_dividing_lines(gray, 'horizontal', 1)
    v_dividers = find_dividing_lines(gray, 'vertical', 1)
    
    y_split = h_dividers[0] if h_dividers else height // 2
    x_split = v_dividers[0] if v_dividers else width // 2
    
    return x_split, y_split


def split_quadrant_image(image, margin: int = 5) -> List[Tuple[str, tuple]]:
    """向后兼容的四宫格切割函数 - 现在会自动检测布局类型"""
    return detect_layout_and_split(image, margin)


def remove_background(image):
    """
    使用 rembg 去除图片背景
    
    Args:
        image: BGR 格式的 numpy 数组
    
    Returns:
        BGRA 格式的 numpy 数组（带 alpha 通道）
    """
    _ensure_imports()
    if not REMBG_AVAILABLE:
        raise ImportError(
            "rembg 未安装。请运行: pip install rembg onnxruntime"
        )
    
    # OpenCV BGR -> PIL RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)
    
    # 去除背景
    result = remove_bg(pil_image)
    
    # PIL RGBA -> OpenCV BGRA
    result_np = np.array(result)
    if result_np.shape[2] == 4:
        result_bgra = cv2.cvtColor(result_np, cv2.COLOR_RGBA2BGRA)
    else:
        result_bgra = cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)
    
    return result_bgra


def process_quadrant_image(
    input_path: str,
    output_dir: str,
    remove_bg_flag: bool = True,
    margin: int = 5
) -> List[str]:
    """
    处理四宫格图片的主函数
    
    Args:
        input_path: 输入图片路径
        output_dir: 输出目录
        remove_bg_flag: 是否去除背景
        margin: 切割边界收缩像素
    
    Returns:
        生成的文件路径列表
    """
    _ensure_imports()
    # 读取图片
    image = cv2.imread(input_path)
    if image is None:
        raise ValueError(f"无法读取图片: {input_path}")
    
    print(f"\n{'='*50}")
    print(f"[开始处理] {input_path}")
    print(f"{'='*50}")
    
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 获取输入文件名（不含扩展名）
    input_stem = Path(input_path).stem
    
    # 分割图片
    views = split_quadrant_image(image, margin=margin)
    
    output_files = []
    
    for view_name, view_image in views:
        # 生成输出文件名
        output_filename = f"{input_stem}_{view_name}.png"
        output_filepath = output_path / output_filename
        
        if remove_bg_flag:
            print(f"[处理中] 去除 {view_name} 视图背景...")
            try:
                processed = remove_background(view_image)
            except ImportError as e:
                print(f"[警告] {e}")
                print(f"[警告] 跳过去背景，保存原图")
                processed = view_image
        else:
            processed = view_image
        
        # 保存
        cv2.imwrite(str(output_filepath), processed)
        print(f"[保存] {output_filepath}")
        output_files.append(str(output_filepath))
    
    print(f"\n[完成] 共生成 {len(output_files)} 个视图文件")
    return output_files


def main():
    parser = argparse.ArgumentParser(
        description="将 Gemini 生成的四宫格图片切割为独立视图"
    )
    parser.add_argument(
        "input",
        help="输入的四宫格图片路径"
    )
    parser.add_argument(
        "--output", "-o",
        default="outputs",
        help="输出目录 (默认: outputs)"
    )
    parser.add_argument(
        "--no-rembg",
        action="store_true",
        help="跳过去背景处理"
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=5,
        help="切割边界收缩像素 (默认: 5)"
    )
    
    args = parser.parse_args()
    
    process_quadrant_image(
        input_path=args.input,
        output_dir=args.output,
        remove_bg_flag=not args.no_rembg,
        margin=args.margin
    )


if __name__ == "__main__":
    main()
