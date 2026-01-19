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


def remove_small_fragments(image, min_area_ratio: float = 0.05):
    """
    移除图片中的小碎片（如相邻视图的手片段）
    
    使用连通组件分析，只保留最大的主体，移除面积小于阈值的碎片。
    
    Args:
        image: BGRA 格式图片（必须有透明通道）
        min_area_ratio: 碎片面积相对于最大主体的最小比例，小于此值的将被移除
    
    Returns:
        处理后的图片
    """
    _ensure_imports()
    
    # 检查是否有透明通道
    if len(image.shape) != 3 or image.shape[2] != 4:
        print("[WARNING] remove_small_fragments 需要 BGRA 图片")
        return image
    
    # 获取 alpha 通道作为 mask
    alpha = image[:, :, 3]
    
    # 二值化 alpha 通道
    _, binary = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
    
    # 连通组件分析
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    
    if num_labels <= 1:
        # 只有背景，没有前景
        return image
    
    # 找到最大的组件（排除背景 label=0）
    # stats[:, cv2.CC_STAT_AREA] 包含每个组件的面积
    areas = stats[1:, cv2.CC_STAT_AREA]  # 排除背景
    max_area = np.max(areas)
    max_label = np.argmax(areas) + 1  # +1 因为排除了背景
    
    print(f"[碎片检测] 发现 {num_labels - 1} 个连通区域, 最大面积: {max_area}px²")
    
    # 创建掩码，只保留大于阈值的组件
    min_area = max_area * min_area_ratio
    keep_mask = np.zeros_like(binary)
    
    removed_count = 0
    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area >= min_area:
            keep_mask[labels == label] = 255
        else:
            removed_count += 1
            # 获取碎片位置信息
            x = stats[label, cv2.CC_STAT_LEFT]
            y = stats[label, cv2.CC_STAT_TOP]
            w = stats[label, cv2.CC_STAT_WIDTH]
            h = stats[label, cv2.CC_STAT_HEIGHT]
            print(f"[碎片移除] 移除碎片: 位置({x},{y}), 尺寸{w}x{h}, 面积{area}px² (< {min_area:.0f})")
    
    if removed_count > 0:
        print(f"[碎片移除] 共移除 {removed_count} 个碎片")
    
    # 应用掩码到图片
    result = image.copy()
    result[:, :, 3] = cv2.bitwise_and(result[:, :, 3], keep_mask)
    
    return result


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


def detect_grid_layout(image) -> tuple:
    """
    通用网格布局检测：检测图片中的 rows x cols 布局
    
    通过分析水平和垂直方向的间隙模式来确定网格结构。
    使用严格的间隙检测避免误判主体内部间隙。
    
    Returns:
        (rows, cols, v_gaps, h_gaps): 网格的行数、列数和间隙位置
    """
    _ensure_imports()
    height, width = image.shape[:2]
    
    # 转灰度
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # 边缘检测
    edges = cv2.Canny(gray, 50, 150)
    
    def find_major_gaps(dimension_size, profile, axis_name, expected_counts=[1, 3, 7]):
        """
        找到主要的分割间隙
        
        策略：
        1. 对于常见布局 (1x4, 2x2, 2x4)，尝试预期的间隙数量
        2. 验证间隙是否均匀分布
        3. 选择最可能的配置
        """
        # 计算间隙得分
        profile = np.array(profile, dtype=float)
        edge_density = np.mean(edges, axis=0 if axis_name == 'vertical' else 1)
        
        # 均匀区域高分（低标准差 + 低边缘 = 可能是背景间隙）
        # 使用滑动窗口计算局部标准差
        window_size = max(10, dimension_size // 30)
        gap_scores = []
        
        for i in range(dimension_size):
            start = max(0, i - window_size // 2)
            end = min(dimension_size, i + window_size // 2)
            local_std = np.std(profile[start:end])
            local_edge = np.mean(edge_density[start:end])
            # 低标准差 + 低边缘密度 = 高间隙得分
            score = 1.0 / (1.0 + local_std) * 1.0 / (1.0 + local_edge)
            gap_scores.append(score)
        
        gap_scores = np.array(gap_scores)
        
        # 平滑处理
        kernel_size = max(5, dimension_size // 40)
        if kernel_size % 2 == 0:
            kernel_size += 1
        smoothed = np.convolve(gap_scores, np.ones(kernel_size)/kernel_size, mode='same')
        
        # 尝试不同的间隙数量配置
        best_gaps = []
        best_score = 0
        
        for num_gaps in expected_counts:
            if num_gaps == 0:
                continue
            
            # 计算预期间隙位置（均匀分布）
            segment_size = dimension_size / (num_gaps + 1)
            expected_positions = [int(segment_size * (i + 1)) for i in range(num_gaps)]
            
            # 在预期位置附近搜索实际间隙
            search_range = int(segment_size * 0.25)  # 搜索范围 ±25%
            found_gaps = []
            total_score = 0
            
            for exp_pos in expected_positions:
                search_start = max(0, exp_pos - search_range)
                search_end = min(dimension_size, exp_pos + search_range)
                
                if search_end > search_start:
                    local_scores = smoothed[search_start:search_end]
                    best_local_idx = np.argmax(local_scores)
                    best_local_score = local_scores[best_local_idx]
                    actual_pos = search_start + best_local_idx
                    found_gaps.append(actual_pos)
                    total_score += best_local_score
            
            # 验证间隙是否有效（得分需要高于阈值）
            avg_score = total_score / len(found_gaps) if found_gaps else 0
            threshold = np.mean(smoothed) + np.std(smoothed) * 0.5
            
            if avg_score > threshold and avg_score > best_score:
                best_score = avg_score
                best_gaps = found_gaps
                print(f"[{axis_name}] 接受 {num_gaps} 个间隙配置, 平均得分={avg_score:.4f}, 阈值={threshold:.4f}")
        
        return best_gaps
    
    # =========================================================
    # 检测垂直分割线（确定列数）
    # =========================================================
    col_profile = np.std(gray, axis=0)
    vertical_gaps = find_major_gaps(width, col_profile, 'vertical', expected_counts=[3, 1, 7, 2])
    num_cols = len(vertical_gaps) + 1
    
    # =========================================================
    # 检测水平分割线（确定行数）
    # =========================================================
    row_profile = np.std(gray, axis=1)
    horizontal_gaps = find_major_gaps(height, row_profile, 'horizontal', expected_counts=[1, 3, 0])
    num_rows = len(horizontal_gaps) + 1
    
    # =========================================================
    # 验证和修正
    # =========================================================
    # 限制在合理范围内
    num_cols = min(max(1, num_cols), 8)
    num_rows = min(max(1, num_rows), 4)
    
    # 计算检测到的视图数
    total_views = num_rows * num_cols
    
    print(f"[网格检测] 检测到 {num_cols-1} 个垂直间隙: {vertical_gaps}")
    print(f"[网格检测] 检测到 {num_rows-1} 个水平间隙: {horizontal_gaps}")
    print(f"[网格检测] 布局: {num_rows}x{num_cols} ({total_views} 个视图)")
    
    return (num_rows, num_cols, vertical_gaps, horizontal_gaps)


def split_universal_grid(image, rows: int, cols: int, v_gaps: list, h_gaps: list, margin: int = 5) -> List[Tuple[str, any]]:
    """
    根据检测到的网格布局切割图片
    
    Args:
        image: 输入图片
        rows: 行数
        cols: 列数
        v_gaps: 垂直间隙位置列表
        h_gaps: 水平间隙位置列表
        margin: 边距
    
    Returns:
        [(view_name, cropped_image), ...]
    """
    _ensure_imports()
    height, width = image.shape[:2]
    
    # 确定分割点
    x_splits = [0] + v_gaps + [width]
    y_splits = [0] + h_gaps + [height]
    
    # 视图命名规则
    if rows == 1 and cols == 4:
        view_names = ['front', 'right', 'back', 'left']
    elif rows == 2 and cols == 2:
        view_names = ['front', 'right', 'back', 'left']  # 按田字格顺序
    elif rows == 2 and cols == 4:
        # 2x4: 上排4个 + 下排4个
        view_names = [f'view_{i+1}' for i in range(rows * cols)]
    else:
        view_names = [f'view_{i+1}' for i in range(rows * cols)]
    
    views = []
    view_idx = 0
    
    # 扩展比例
    overlap_ratio = 0.10
    
    for row in range(rows):
        for col in range(cols):
            # 计算基础边界
            base_x1 = x_splits[col]
            base_x2 = x_splits[col + 1]
            base_y1 = y_splits[row]
            base_y2 = y_splits[row + 1]
            
            # 视图尺寸
            view_width = base_x2 - base_x1
            view_height = base_y2 - base_y1
            
            # 向外扩展
            x_overlap = int(view_width * overlap_ratio)
            y_overlap = int(view_height * overlap_ratio)
            
            x1 = max(0, base_x1 - x_overlap)
            x2 = min(width, base_x2 + x_overlap)
            y1 = max(margin, base_y1 - y_overlap)
            y2 = min(height - margin, base_y2 + y_overlap)
            
            if x2 > x1 and y2 > y1:
                cropped = image[y1:y2, x1:x2].copy()
                name = view_names[view_idx] if view_idx < len(view_names) else f'view_{view_idx+1}'
                print(f"[INFO] {name} 视图切割区域: x={x1}-{x2}, y={y1}-{y2}")
                views.append((name, cropped))
            
            view_idx += 1
    
    return views


def detect_layout_smart(image) -> str:
    """
    通过多重检测智能判断布局类型 (Grid vs Linear)
    
    检测方法:
    1. 垂直分割线检测：1x4 有 3 条垂直分割线间隔 W/4，2x2 只有 1 条在 W/2
    2. 水平中心带边缘密度：1x4 中间有内容，2x2 中间是空隙
    3. 宽高比辅助判断
    """
    _ensure_imports()
    height, width = image.shape[:2]
    aspect_ratio = width / height
    
    # 转灰度
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # =====================================================================
    # 方法1: 分析垂直亮度分布，寻找分割线
    # =====================================================================
    # 计算每列的平均亮度
    col_brightness = np.mean(gray, axis=0)
    
    # 在期望的分割位置寻找亮度峰值
    # 1x4 布局的分割线应该在 W/4, W/2, 3W/4
    # 2x2 布局的垂直分割线只在 W/2
    
    def find_peak_near(profile, expected_pos, search_range=0.05):
        """在期望位置附近寻找亮度峰值"""
        length = len(profile)
        range_px = int(length * search_range)
        start = max(0, expected_pos - range_px)
        end = min(length, expected_pos + range_px)
        segment = profile[start:end]
        if len(segment) == 0:
            return 0
        # 返回相对于背景的亮度差异
        peak_val = np.max(segment)
        mean_val = np.mean(profile)
        return peak_val - mean_val
    
    # 检查 1x4 的三个分割线位置
    pos_quarter = width // 4
    pos_half = width // 2
    pos_three_quarter = 3 * width // 4
    
    peak_q1 = find_peak_near(col_brightness, pos_quarter)
    peak_half = find_peak_near(col_brightness, pos_half)
    peak_q3 = find_peak_near(col_brightness, pos_three_quarter)
    
    # 计算分割线强度
    linear_score = (peak_q1 + peak_q3) / 2  # 1x4 特有的两侧分割线
    grid_score = peak_half  # 2x2 的中间分割线
    
    print(f"[DEBUG] 分割线检测: 1/4位置={peak_q1:.1f}, 1/2位置={peak_half:.1f}, 3/4位置={peak_q3:.1f}")
    print(f"[DEBUG] Linear得分={linear_score:.1f}, Grid得分={grid_score:.1f}")
    
    # =====================================================================
    # 方法2: 水平中心带边缘密度
    # =====================================================================
    edges = cv2.Canny(gray, 50, 150)
    center_y = height // 2
    strip_h = max(20, int(height * 0.1))
    start_y = center_y - strip_h // 2
    end_y = center_y + strip_h // 2
    center_strip = edges[start_y:end_y, :]
    
    edge_pixels = np.count_nonzero(center_strip)
    total_pixels = center_strip.size
    edge_density = edge_pixels / total_pixels
    
    print(f"[DEBUG] 中心带边缘密度 = {edge_density:.4f}")
    
    # =====================================================================
    # 方法3: 检测主体排列方式（核心算法）
    # 通过检测水平/垂直方向的分割线来判断布局
    # =====================================================================
    
    # 检测垂直分割线（用于 1x4 横排）
    # 在 1/4, 1/2, 3/4 位置检查是否有垂直间隙
    h_gaps = []
    for ratio in [0.25, 0.5, 0.75]:
        col = int(width * ratio)
        col_start = max(0, col - 10)
        col_end = min(width, col + 10)
        gap_region = gray[:, col_start:col_end]
        # 计算该列区域的标准差（低标准差 = 均匀背景 = 间隙）
        gap_std = np.std(gap_region)
        h_gaps.append(gap_std)
    
    # 检测水平分割线（用于 2x2 田字格）
    # 在 1/2 位置检查是否有水平间隙
    row = height // 2
    row_start = max(0, row - 10)
    row_end = min(height, row + 10)
    gap_region = gray[row_start:row_end, :]
    v_gap_std = np.std(gap_region)
    
    # 计算分割线特征
    avg_h_gap_std = np.mean(h_gaps)  # 垂直分割线的平均标准差
    print(f"[DEBUG] 垂直分割线标准差: {h_gaps}, 平均={avg_h_gap_std:.1f}")
    print(f"[DEBUG] 水平分割线标准差: {v_gap_std:.1f}")
    
    # =====================================================================
    # 综合判断
    # =====================================================================
    votes_linear = 0
    votes_grid = 0
    
    # 投票1: 分割线检测 (原有)
    if linear_score > grid_score * 0.5 and peak_q1 > 5 and peak_q3 > 5:
        votes_linear += 1
        print("[DEBUG] 分割线检测投票: Linear (检测到 1/4 和 3/4 分割线)")
    else:
        votes_grid += 1
        print("[DEBUG] 分割线检测投票: Grid")
    
    # 投票2: 边缘密度 (原有)
    if edge_density > 0.025:
        votes_linear += 1
        print("[DEBUG] 边缘密度投票: Linear (中心有内容)")
    else:
        votes_grid += 1
        print("[DEBUG] 边缘密度投票: Grid (中心较空)")
    
    # 投票3: 主体排列检测 (新增 - 最重要)
    # 比较垂直分割线和水平分割线的质量
    # 标准差越低说明分割线越清晰
    if avg_h_gap_std < v_gap_std and avg_h_gap_std < 40:
        # 垂直分割线更清晰 → 1x4 横排
        votes_linear += 3  # 给予更高权重
        print(f"[DEBUG] 主体排列投票: Linear x3 (垂直分割线更清晰)")
    elif v_gap_std < avg_h_gap_std and v_gap_std < 40:
        # 水平分割线更清晰 → 2x2 田字格
        votes_grid += 3
        print(f"[DEBUG] 主体排列投票: Grid x3 (水平分割线更清晰)")
    else:
        # 无法确定，使用宽高比作为备选
        if aspect_ratio >= 1.4:
            votes_linear += 1
            print(f"[DEBUG] 主体排列投票: Linear (无法确定，AR={aspect_ratio:.2f}>=1.4)")
        elif aspect_ratio <= 0.7:
            # 极端竖屏才投 Grid
            votes_grid += 1
            print(f"[DEBUG] 主体排列投票: Grid (无法确定，AR={aspect_ratio:.2f}<=0.7)")
        else:
            print(f"[DEBUG] 主体排列投票: 弃权 (无法确定)")
    
    print(f"[DEBUG] 最终投票: Linear={votes_linear}, Grid={votes_grid}")
    
    if votes_linear > votes_grid:
        return "linear"
    elif votes_grid > votes_linear:
        return "grid"
    else:
        # 平票时，优先 linear（因为这是生成脚本的默认输出格式）
        return "linear"


def detect_layout_and_split(image, margin: int = 5) -> List[Tuple[str, any]]:
    """
    智能检测图片布局类型并切割
    
    支持布局:
    1. 1x4 横排 (Linear)
    2. 2x2 田字格 (Grid)
    3. 2x4 等非标准布局 (Universal Grid)
    """
    _ensure_imports()
    height, width = image.shape[:2]
    aspect_ratio = width / height
    
    print(f"[INFO] 图片尺寸: {width}x{height}, 宽高比: {aspect_ratio:.2f}")
    
    # =========================================================
    # 首先使用通用网格检测来识别布局
    # =========================================================
    rows, cols, v_gaps, h_gaps = detect_grid_layout(image)
    
    # 根据检测结果决定使用哪种切割方式
    if rows == 1 and cols == 4:
        # 标准 1x4 横排
        print("[INFO] 识别为: 1x4 横排布局 (Linear)")
        return split_horizontal_layout(image, margin)
    elif rows == 2 and cols == 2:
        # 标准 2x2 田字格
        print("[INFO] 识别为: 2x2 田字格布局 (Grid)")
        return split_grid_layout(image, margin)
    elif rows == 1 and cols >= 2:
        # 其他横排布局（如 1x3, 1x5 等）
        print(f"[INFO] 识别为: 1x{cols} 横排布局")
        return split_universal_grid(image, rows, cols, v_gaps, h_gaps, margin)
    elif rows >= 2 and cols >= 2:
        # 非标准网格（如 2x4, 3x3 等）
        print(f"[INFO] 识别为: {rows}x{cols} 网格布局 ({rows * cols} 个视图)")
        return split_universal_grid(image, rows, cols, v_gaps, h_gaps, margin)
    else:
        # 回退到传统检测
        print("[INFO] 无法确定布局，使用传统检测...")
        layout_type = detect_layout_smart(image)
        if layout_type == "linear":
            print("[INFO] 回退识别为: 1x4 横排布局 (Linear)")
            return split_horizontal_layout(image, margin)
        else:
            print("[INFO] 回退识别为: 2x2 田字格布局 (Grid)")
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
    切割 1x4 横排布局 - 智能检测主体边界
    
    1. 使用边缘检测找到垂直分割线（主体之间的间隙）
    2. 基于检测到的分割线切割，而不是固定 1/4
    3. 如果检测失败，回退到固定 1/4 切割
    """
    _ensure_imports()
    height, width = image.shape[:2]
    
    # 转换为灰度图进行分析
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # =========================================================
    # 方法1: 使用列像素密度找到分割点
    # 在主体之间的间隙区域，像素变化较小（背景色）
    # =========================================================
    
    # 计算每列的标准差（变化程度）
    col_std = np.std(gray, axis=0)
    
    # 计算每列的边缘密度
    edges = cv2.Canny(gray, 50, 150)
    col_edge_density = np.mean(edges, axis=0)
    
    # 综合得分：低标准差 + 低边缘密度 = 可能是分割线
    # 归一化
    col_std_norm = (col_std - col_std.min()) / (col_std.max() - col_std.min() + 1e-6)
    col_edge_norm = (col_edge_density - col_edge_density.min()) / (col_edge_density.max() - col_edge_density.min() + 1e-6)
    
    # 分割线得分：越低越可能是分割线
    gap_score = col_std_norm + col_edge_norm
    
    # 寻找3个分割点（将图片分成4份）
    cell_width = width // 4
    split_points = []
    
    for i in range(1, 4):
        # 在预期位置附近搜索最佳分割点（±20%范围）
        expected_pos = i * cell_width
        search_start = max(0, expected_pos - cell_width // 5)
        search_end = min(width, expected_pos + cell_width // 5)
        
        # 在搜索范围内找到最低分（最可能是间隙）
        search_range = gap_score[search_start:search_end]
        if len(search_range) > 0:
            local_min_idx = np.argmin(search_range)
            best_split = search_start + local_min_idx
            split_points.append(best_split)
            print(f"[智能检测] 第{i}个分割点: 预期{expected_pos}, 实际{best_split} (偏移{best_split - expected_pos}px)")
        else:
            split_points.append(expected_pos)
            print(f"[智能检测] 第{i}个分割点: 使用预期位置{expected_pos}")
    
    # 添加边界
    split_points = [0] + split_points + [width]
    
    # =========================================================
    # 切割视图 (每个视图向两侧扩展以捕获延伸的肢体)
    # =========================================================
    views = []
    view_names = ['front', 'right', 'back', 'left']
    
    # 扩展比例：向每侧扩展视图宽度的 10%
    overlap_ratio = 0.10
    
    for i, name in enumerate(view_names):
        base_x1 = split_points[i]
        base_x2 = split_points[i + 1]
        view_width = base_x2 - base_x1
        overlap = int(view_width * overlap_ratio)
        
        # 向两侧扩展
        x1 = max(0, base_x1 - overlap)
        x2 = min(width, base_x2 + overlap)
        y1 = margin
        y2 = height - margin
        
        # 边界检查
        y1 = max(0, y1)
        y2 = min(height, y2)
        
        if x2 > x1 and y2 > y1:
            cropped = image[y1:y2, x1:x2].copy()
            print(f"[INFO] {name} 视图切割区域: x={x1}-{x2} (基础宽度{view_width}px, 扩展{overlap}px)")
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


def remove_background(image, model_name: str = "birefnet-general"):
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
                
                # 移除小碎片（如相邻视图的手片段）
                print(f"[处理中] 清理 {view_name} 视图碎片...")
                processed = remove_small_fragments(processed, min_area_ratio=0.03)
                
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
