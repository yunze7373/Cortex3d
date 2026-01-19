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


def find_subject_bbox(image, padding: int = 10):
    """
    使用边缘检测或 alpha 通道找到主体的边界框
    
    Args:
        image: BGR 或 BGRA 格式的图片
        padding: 边界外扩像素数
    
    Returns:
        (x1, y1, x2, y2) 边界框坐标
    """
    _ensure_imports()
    height, width = image.shape[:2]
    
    # 如果有 alpha 通道，使用 alpha 找边界
    if len(image.shape) == 3 and image.shape[2] == 4:
        alpha = image[:, :, 3]
        mask = alpha > 10  # 阈值
    else:
        # 否则使用灰度图和边缘检测
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 使用 Otsu 阈值分割前景背景
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 如果大部分是白色（背景），反转
        if np.mean(mask) > 127:
            mask = 255 - mask
        
        mask = mask > 127
    
    # 找到非零像素的边界
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        # 没有检测到主体，返回整个图像
        return 0, 0, width, height
    
    y1, y2 = np.where(rows)[0][[0, -1]]
    x1, x2 = np.where(cols)[0][[0, -1]]
    
    # 添加 padding
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(width, x2 + padding)
    y2 = min(height, y2 + padding)
    
    return x1, y1, x2, y2


def crop_to_subject(image, target_size: int = 1024, padding: int = 20):
    """
    裁切图片到主体区域，并调整到正方形输出
    
    Args:
        image: BGR 或 BGRA 格式的图片
        target_size: 输出图片尺寸 (正方形)
        padding: 主体周围的边距
    
    Returns:
        裁切后的图片 (正方形)
    """
    _ensure_imports()
    
    # 找到主体边界
    x1, y1, x2, y2 = find_subject_bbox(image, padding=padding)
    
    # 计算主体尺寸
    subject_w = x2 - x1
    subject_h = y2 - y1
    
    # 扩展为正方形（取较大边）
    max_dim = max(subject_w, subject_h)
    
    # 计算正方形中心
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    
    # 计算正方形边界
    half = max_dim // 2
    sq_x1 = cx - half
    sq_y1 = cy - half
    sq_x2 = cx + half
    sq_y2 = cy + half
    
    # 边界检查和调整
    height, width = image.shape[:2]
    
    # 如果超出边界，移动正方形
    if sq_x1 < 0:
        sq_x2 -= sq_x1
        sq_x1 = 0
    if sq_y1 < 0:
        sq_y2 -= sq_y1
        sq_y1 = 0
    if sq_x2 > width:
        sq_x1 -= (sq_x2 - width)
        sq_x2 = width
    if sq_y2 > height:
        sq_y1 -= (sq_y2 - height)
        sq_y2 = height
    
    # 确保边界有效
    sq_x1 = max(0, sq_x1)
    sq_y1 = max(0, sq_y1)
    sq_x2 = min(width, sq_x2)
    sq_y2 = min(height, sq_y2)
    
    # 裁切
    cropped = image[sq_y1:sq_y2, sq_x1:sq_x2]
    
    # 如果需要，调整大小
    if cropped.shape[0] != target_size or cropped.shape[1] != target_size:
        # 保持纵横比，放到正方形画布上
        h, w = cropped.shape[:2]
        scale = target_size / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        
        # 创建正方形画布（透明或白色）
        if len(image.shape) == 3 and image.shape[2] == 4:
            canvas = np.zeros((target_size, target_size, 4), dtype=np.uint8)
        else:
            canvas = np.ones((target_size, target_size, 3), dtype=np.uint8) * 255
        
        # 居中放置
        x_offset = (target_size - new_w) // 2
        y_offset = (target_size - new_h) // 2
        
        if len(resized.shape) == 2:
            resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
        
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        return canvas
    
    return cropped



def detect_layout_smart(image) -> str:
    """
    通过边缘检测智能判断布局类型 (Grid vs Linear)
    
    原理:
    - 提取图片水平中心带 (H/2 附近 10% 高度区域)
    - 1x4 (Linear): 中心带有大量边缘 (因为角色占据整个高度) -> Edge Density High
    - 2x2 (Grid): 中心带通常是上下两排的空隙 -> Edge Density Low
    """
    _ensure_imports()
    height, width = image.shape[:2]
    
    # 转灰度
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    # Canny 边缘检测
    edges = cv2.Canny(gray, 50, 150)
    
    # 提取中心水平带 (高度的 45% - 55%)
    center_y = height // 2
    strip_h = max(20, int(height * 0.1))
    start_y = center_y - strip_h // 2
    end_y = center_y + strip_h // 2
    
    center_strip = edges[start_y:end_y, :]
    
    # 计算边缘密度 (非零像素占比)
    edge_pixels = np.count_nonzero(center_strip)
    total_pixels = center_strip.size
    density = edge_pixels / total_pixels
    
    print(f"[DEBUG] 布局检测: 中心带边缘密度 = {density:.4f}")
    
    # 阈值判断
    # 典型值: 1x4 约 0.05-0.10, 2x2 约 0.00-0.02
    if density > 0.03: 
        return "linear"  # 1x4 (中间有内容)
    else:
        return "grid"    # 2x2 (中间是空隙)


def detect_layout_and_split(image, margin: int = 5) -> List[Tuple[str, any]]:
    """
    智能检测图片布局类型并切割
    
    支持两种布局:
    1. 2x2 田字格 (宽高比接近1:1 或 4:3)
    2. 1x4 横排 (宽高比约 4:1 或更宽)
    """
    _ensure_imports()
    height, width = image.shape[:2]
    aspect_ratio = width / height
    
    print(f"[INFO] 图片尺寸: {width}x{height}, 宽高比: {aspect_ratio:.2f}")
    
    layout_type = "unknown"
    
    # 对于极宽的图片 (>= 3.0)，直接判定为横排
    if aspect_ratio >= 3.0:
        layout_type = "linear"
        print("[INFO] 宽高比 >= 3.0，直接判定为横排")
    # 对于极窄的图片 (< 0.8)，直接判定为竖排/田字格
    elif aspect_ratio < 0.8:
        layout_type = "grid"
        print("[INFO] 宽高比 < 0.8，直接判定为田字格")
    else:
        # 其他所有情况 (0.8 - 3.0) -> 使用智能内容检测
        # 这包括正方形 1:1 (可能是 1x4 紧凑排列) 和常规宽高比
        print(f"[INFO] 启用智能内容检测...")
        layout_type = detect_layout_smart(image)
    
    if layout_type == "linear":
        print("[INFO] 识别为: 1x4 横排布局 (Linear)")
        return split_horizontal_layout(image, margin)
    else:
        print("[INFO] 识别为: 2x2 田字格布局 (Grid)")
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
    切割 1x4 横排布局 - 使用重叠区域避免切到手
    
    每个区域向两边扩展 15%，确保捕获超出格子边界的手臂等部位。
    后续的 crop_to_subject 会根据实际主体边界裁切。
    """
    height, width = image.shape[:2]
    cell_width = width // 4
    
    # 重叠比例：向每侧扩展 15%
    overlap = int(cell_width * 0.15)
    
    views = []
    # AI 通常按顺时针生成: Front(0°) → Right(90°) → Back(180°) → Left(270°)
    view_names = ['front', 'right', 'back', 'left']
    
    for i, name in enumerate(view_names):
        # 计算基础位置
        base_x1 = i * cell_width
        base_x2 = (i + 1) * cell_width
        
        # 向两侧扩展（允许重叠）
        x1 = max(0, base_x1 - overlap)
        x2 = min(width, base_x2 + overlap)
        y1 = margin
        y2 = height - margin
        
        # 边界检查
        y1 = max(0, y1)
        y2 = min(height, y2)
        
        if x2 > x1 and y2 > y1:
            cropped = image[y1:y2, x1:x2].copy()
            print(f"[INFO] {name} 视图切割区域: x={x1}-{x2} (扩展{overlap}px)")
            views.append((name, cropped))
    
    return views


def split_grid_layout(image, margin: int = 5) -> List[Tuple[str, any]]:
    """
    切割 2x2 田字格布局 - 使用固定几何分割
    
    AI 生成的 2x2 布局通常是:
    Front | Right
    Back  | Left
    """
    height, width = image.shape[:2]
    
    # 强制中心分割
    x_split = width // 2
    y_split = height // 2
    
    # 定义四个区域 (顺时针: Front → Right → Back → Left)
    # 布局:
    # [0,0] Front | [1,0] Right
    # [0,1] Back  | [1,1] Left
    regions = {
        'front': (margin, margin, x_split - margin, y_split - margin),
        'right': (x_split + margin, margin, width - margin, y_split - margin),
        'back': (margin, y_split + margin, x_split - margin, height - margin),
        'left': (x_split + margin, y_split + margin, width - margin, height - margin)
    }
    
    views = []
    # 按顺时针顺序: front, right, back, left
    for name in ['front', 'right', 'back', 'left']:
        x1, y1, x2, y2 = regions[name]
        
        x1 = max(0, x1)
        x2 = min(width, x2)
        y1 = max(0, y1)
        y2 = min(height, y2)

        if x2 > x1 and y2 > y1:
            cropped = image[y1:y2, x1:x2].copy()
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


def remove_background(image, model_name: str = "isnet-general-use"):
    """
    使用 rembg 去除图片背景
    
    Args:
        image: BGR 格式的 numpy 数组
        model_name: rembg 模型名称，可选:
            - "isnet-general-use" (默认，对复杂前景更好)
            - "birefnet-general" (最新模型，质量最高但较慢)
            - "u2net" (经典模型)
    
    Returns:
        BGRA 格式的 numpy 数组（带 alpha 通道）
    """
    _ensure_imports()
    if not REMBG_AVAILABLE:
        raise ImportError(
            "rembg 未安装。请运行: pip install rembg onnxruntime"
        )
    
    # 导入 session 管理
    from rembg import new_session
    
    # 创建指定模型的 session
    session = new_session(model_name)
    print(f"[INFO] 使用背景移除模型: {model_name}")
    
    # OpenCV BGR -> PIL RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)
    
    # 去除背景 (使用指定 session)
    result = remove_bg(pil_image, session=session)
    
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
                
                # 智能裁切：使用 alpha 通道找到主体边界
                print(f"[处理中] 智能裁切 {view_name} 视图到主体区域...")
                processed = crop_to_subject(processed, target_size=1024, padding=30)
                
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
        default="test_images",
        help="输出目录 (默认: test_images)"
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
