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




def detect_grid_split(image) -> Tuple[int, int]:
    """
    自动检测四宫格的分割点
    返回 (x_split, y_split) 坐标
    """
    _ensure_imports()
    height, width = image.shape[:2]
    
    # 转换为灰度图
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 方法1: 假设中心分割（最简单）
    center_x = width // 2
    center_y = height // 2
    
    # 方法2: 边缘检测找分割线（可选增强）
    # 在中心区域搜索明显的分割线
    search_range = 50  # 在中心 +/- 50 像素范围内搜索
    
    # 检测水平分割线（寻找行亮度跳变最小的位置）
    row_sums = []
    for y in range(center_y - search_range, center_y + search_range):
        if 0 <= y < height:
            row_sums.append((y, np.std(gray[y, :])))
    
    # 检测垂直分割线
    col_sums = []
    for x in range(center_x - search_range, center_x + search_range):
        if 0 <= x < width:
            col_sums.append((x, np.std(gray[:, x])))
    
    # 如果能检测到，使用检测结果；否则使用中心点
    if row_sums:
        # 找到标准差最小的行（可能是分割线）
        best_y = min(row_sums, key=lambda x: x[1])[0]
    else:
        best_y = center_y
        
    if col_sums:
        best_x = min(col_sums, key=lambda x: x[1])[0]
    else:
        best_x = center_x
    
    return best_x, best_y


def split_quadrant_image(image, margin: int = 5) -> List[Tuple[str, tuple]]:
    """
    将四宫格图片分割为四个独立视图
    
    布局假设:
        左上: 正面 (front)
        右上: 背面 (back)
        左下: 左侧 (left)
        右下: 右侧 (right)
    
    Args:
        image: 输入图片 (BGR 格式)
        margin: 切割时从边界收缩的像素数，去除可能的分割线
    
    Returns:
        List of (view_name, image) tuples
    """
    height, width = image.shape[:2]
    x_split, y_split = detect_grid_split(image)
    
    print(f"[INFO] 图片尺寸: {width}x{height}")
    print(f"[INFO] 检测到分割点: ({x_split}, {y_split})")
    
    # 定义四个区域，带有边界收缩
    regions = {
        'front': (margin, margin, x_split - margin, y_split - margin),           # 左上
        'back': (x_split + margin, margin, width - margin, y_split - margin),    # 右上
        'left': (margin, y_split + margin, x_split - margin, height - margin),   # 左下
        'right': (x_split + margin, y_split + margin, width - margin, height - margin)  # 右下
    }
    
    views = []
    for name, (x1, y1, x2, y2) in regions.items():
        cropped = image[y1:y2, x1:x2].copy()
        print(f"[INFO] {name} 视图: 位置 ({x1},{y1})-({x2},{y2}), 尺寸 {x2-x1}x{y2-y1}")
        views.append((name, cropped))
    
    return views


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
