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
    
    策略：
    1. 根据图像宽高比估算合理的列数
    2. 验证预期位置是否有明显的间隙
    3. 对于行数，检测是否有水平分割线
    
    Returns:
        (rows, cols, v_gaps, h_gaps): 网格的行数、列数和间隙位置
    """
    _ensure_imports()
    height, width = image.shape[:2]
    aspect_ratio = width / height
    
    # 转灰度
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # 边缘检测
    edges = cv2.Canny(gray, 50, 150)
    
    # =========================================================
    # 快速检测: 2x2 田字格（十字分割线）
    # =========================================================
    # 如果宽高比接近 1:1 且中心有明显的十字交叉线，直接判定为 2x2
    if 0.8 <= aspect_ratio <= 1.25:
        mid_x = width // 2
        mid_y = height // 2
        
        # 检测垂直中心线
        v_strip = gray[:, mid_x-15:mid_x+15]  # 中心垂直条带
        v_std = np.std(v_strip)  # 条带内标准差
        v_edge_count = np.sum(edges[:, mid_x-15:mid_x+15] > 0)
        
        # 检测水平中心线
        h_strip = gray[mid_y-15:mid_y+15, :]  # 中心水平条带
        h_std = np.std(h_strip)  # 条带内标准差
        h_edge_count = np.sum(edges[mid_y-15:mid_y+15, :] > 0)
        
        # 比较中心线与整体
        overall_std = np.std(gray)
        
        # 十字线特征: 中心条带标准差低于整体（较均匀）
        v_is_divider = v_std < overall_std * 0.7
        h_is_divider = h_std < overall_std * 0.7
        
        print(f"[2x2检测] AR={aspect_ratio:.2f}, 垂直中心std={v_std:.1f}, 水平中心std={h_std:.1f}, 整体std={overall_std:.1f}")
        
        if v_is_divider and h_is_divider:
            print("[2x2检测] 检测到明显的十字分割线，判定为 2x2 田字格")
            num_rows = 2
            num_cols = 2
            vertical_gaps = [mid_x]
            horizontal_gaps = [mid_y]
            total_views = num_rows * num_cols
            
            print(f"[网格检测] 检测到 {len(vertical_gaps)} 个垂直间隙: {vertical_gaps}")
            print(f"[网格检测] 检测到 {len(horizontal_gaps)} 个水平间隙: {horizontal_gaps}")
            print(f"[网格检测] 布局: {num_rows}x{num_cols} ({total_views} 个视图)")
            
            return (num_rows, num_cols, vertical_gaps, horizontal_gaps)
    
    def calculate_gap_score_at_position(pos, profile, edges_profile, window=20):
        """计算指定位置的间隙得分"""
        start = max(0, pos - window // 2)
        end = min(len(profile), pos + window // 2)
        
        if end <= start:
            return 0
        
        # 低标准差 + 低边缘密度 = 可能是间隙
        local_std = np.std(profile[start:end])
        local_edge = np.mean(edges_profile[start:end])
        
        # 间隙得分（越高越可能是间隙）
        score = 1.0 / (1.0 + local_std / 50.0) * 1.0 / (1.0 + local_edge / 20.0)
        return score
    
    def find_gaps_for_n_columns(n_cols, img_width, col_profile, col_edges):
        """尝试将图像分成 n 列，返回间隙位置和总得分"""
        if n_cols <= 1:
            return [], 0
        
        cell_width = img_width / n_cols
        gaps = []
        total_score = 0
        
        for i in range(1, n_cols):
            expected_pos = int(i * cell_width)
            # 在预期位置附近搜索最佳间隙
            search_range = int(cell_width * 0.2)  # ±20%
            best_pos = expected_pos
            best_score = 0
            
            for offset in range(-search_range, search_range + 1, 5):
                test_pos = expected_pos + offset
                if 0 < test_pos < img_width:
                    score = calculate_gap_score_at_position(test_pos, col_profile, col_edges)
                    if score > best_score:
                        best_score = score
                        best_pos = test_pos
            
            gaps.append(best_pos)
            total_score += best_score
        
        avg_score = total_score / len(gaps) if gaps else 0
        return gaps, avg_score
    
    # =========================================================
    # 根据宽高比估算列数
    # =========================================================
    # 假设每个视图大约是正方形或略竖长（全身人物）
    # 典型情况：
    # - 1x4 横排：AR ≈ 4:3 到 5:3 (1.33 - 1.67)
    # - 2x2 田字格：AR ≈ 1:1
    # - 2x4 网格：AR ≈ 4:3 (1.33)
    
    col_profile = np.std(gray, axis=0)
    col_edges = np.mean(edges, axis=0)
    
    # 尝试不同列数配置
    candidates = []
    for n_cols in [4, 2, 3, 5, 6, 8]:
        gaps, score = find_gaps_for_n_columns(n_cols, width, col_profile, col_edges)
        # 计算每个单元格的宽高比
        cell_width = width / n_cols
        # 对于多行情况，单元格高度会减半
        cell_height_1row = height
        cell_height_2row = height / 2
        
        cell_ar_1row = cell_width / cell_height_1row
        cell_ar_2row = cell_width / cell_height_2row
        
        candidates.append({
            'cols': n_cols,
            'gaps': gaps,
            'score': score,
            'cell_ar_1row': cell_ar_1row,
            'cell_ar_2row': cell_ar_2row
        })
        print(f"[列检测] {n_cols}列: 得分={score:.4f}, 单元AR(1行)={cell_ar_1row:.2f}, 单元AR(2行)={cell_ar_2row:.2f}")
    
    # 选择最佳配置
    # 优先选择单元格接近正方形或竖长的配置
    best_candidate = None
    best_combined_score = 0
    
    for c in candidates:
        # 计算综合得分：间隙得分 + 单元格形状奖励
        # 理想单元格AR在 0.5-1.2 之间（略竖长到略横长）
        ar_score_1row = 1.0 if 0.5 <= c['cell_ar_1row'] <= 1.2 else 0.5
        ar_score_2row = 1.0 if 0.5 <= c['cell_ar_2row'] <= 1.2 else 0.5
        
        # 4列通常是首选（标准多视图）
        preference_bonus = 1.2 if c['cols'] == 4 else 1.0
        
        combined_1row = c['score'] * ar_score_1row * preference_bonus
        combined_2row = c['score'] * ar_score_2row * preference_bonus
        combined = max(combined_1row, combined_2row)
        
        if combined > best_combined_score:
            best_combined_score = combined
            best_candidate = c
    
    num_cols = best_candidate['cols'] if best_candidate else 4
    vertical_gaps = best_candidate['gaps'] if best_candidate else []
    
    print(f"[列检测] 选择 {num_cols} 列配置")
    
    # =========================================================
    # 检测水平分割线（确定行数）
    # =========================================================
    row_profile = np.std(gray, axis=1)
    row_edges = np.mean(edges, axis=1)
    
    # 检测中间是否有水平间隙（2行）
    mid_pos = height // 2
    mid_score = calculate_gap_score_at_position(mid_pos, row_profile, row_edges, window=30)
    
    # 阈值判断
    avg_row_score = np.mean([calculate_gap_score_at_position(i, row_profile, row_edges) 
                             for i in range(0, height, height // 10)])
    
    # 计算当前选择的列配置在1行和2行时的单元格AR
    cell_ar_1row = best_candidate['cell_ar_1row'] if best_candidate else 0.5
    cell_ar_2row = best_candidate['cell_ar_2row'] if best_candidate else 1.0
    
    print(f"[行检测] 中间位置得分={mid_score:.4f}, 平均得分={avg_row_score:.4f}")
    print(f"[行检测] 单元AR(1行)={cell_ar_1row:.2f}, 单元AR(2行)={cell_ar_2row:.2f}")
    
    # 判断条件：
    # 必须满足：中间位置得分高于平均值（说明中间有间隙）
    # 辅助条件：AR 不合理可以降低阈值
    
    has_mid_gap = mid_score > avg_row_score  # 基本条件：中间得分高于平均
    ar_suggests_2rows = cell_ar_1row < 0.45  # AR 暗示可能需要2行
    
    needs_2rows = False
    reason = ""
    
    if mid_score > avg_row_score * 1.3:
        # 中间有明显间隙
        needs_2rows = True
        reason = f"中间有明显间隙(得分比={mid_score/avg_row_score:.2f})"
    elif has_mid_gap and ar_suggests_2rows:
        # 中间有轻微间隙 + AR 确认需要2行
        needs_2rows = True
        reason = f"中间有间隙(得分比={mid_score/avg_row_score:.2f}) + AR暗示({cell_ar_1row:.2f}<0.45)"
    
    if needs_2rows:
        num_rows = 2
        horizontal_gaps = [mid_pos]
        print(f"[行检测] 检测到需要2行布局: {reason}")
    else:
        num_rows = 1
        horizontal_gaps = []
        if ar_suggests_2rows:
            print(f"[行检测] AR暗示2行(AR={cell_ar_1row:.2f})，但中间无间隙，保持1行")
        else:
            print("[行检测] 布局为 1 行")
    
    # 计算检测到的视图数
    total_views = num_rows * num_cols
    
    print(f"[网格检测] 检测到 {len(vertical_gaps)} 个垂直间隙: {vertical_gaps[:5]}...")
    print(f"[网格检测] 检测到 {len(horizontal_gaps)} 个水平间隙: {horizontal_gaps}")
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
    elif rows == 2 and cols == 3:
        # 2x3 (6视角): 
        # Row 1: front, front_right, right
        # Row 2: back, left, front_left
        view_names = ['front', 'front_right', 'right', 'back', 'left', 'front_left']
    elif rows == 2 and cols == 4:
        # 2x4 (8视角):
        # Row 1: front, front_right, right, back
        # Row 2: left, front_left, top, bottom
        view_names = ['front', 'front_right', 'right', 'back', 'left', 'front_left', 'top', 'bottom']
    elif rows == 1 and cols == 6:
        # 1x6 (6视角横排)
        view_names = ['front', 'front_right', 'right', 'back', 'left', 'front_left']
    elif rows == 1 and cols == 8:
        # 1x8 (8视角横排)
        view_names = ['front', 'front_right', 'right', 'back', 'left', 'front_left', 'top', 'bottom']
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


def split_quadrant_image(image, margin: int = 5, expected_views: list = None) -> List[Tuple[str, any]]:
    """
    分割四宫格图片
    
    Args:
        image: 输入图片
        margin: 边距
        expected_views: 期望的视角名称列表 (用于指导分割)
    
    Returns:
        [(view_name, image), ...]
    """
    _ensure_imports()
    
    # 如果指定了期望视角，计算期望的行列数
    expected_layout = None
    if expected_views:
        count = len(expected_views)
        if count == 1:
            print(f"[布局指导] 单视角模式 (1x1)")
            # 不需要分割，直接裁剪边距即可
            h, w = image.shape[:2]
            if margin > 0:
                cropped = image[margin:h-margin, margin:w-margin]
            else:
                cropped = image
            return [(expected_views[0], cropped)]
        
        # 尝试从 prompts.views 导入辅助函数
        try:
            from prompts.views import get_layout_for_views
            rows, cols, _ = get_layout_for_views(count)
            expected_layout = (rows, cols)
            print(f"[布局指导] 期望布局: {rows}x{cols} ({count} 视图)")
        except ImportError:
            # 简单的回退逻辑
            if count <= 4: expected_layout = (1, 4)
            elif count <= 6: expected_layout = (2, 3)
            elif count <= 8: expected_layout = (2, 4)
    
    # 检测布局 (传入期望的列数作为提示)
    # 注意: detect_grid_layout 目前签名不支持 expected_cols，这里暂时只使用其返回值进行校验
    # 如果需要支持 expected_cols，需要修改 detect_grid_layout
    layout_type, rows, cols, v_gaps, h_gaps = detect_grid_layout(image)
    
    # 如果检测结果与期望严重不符，优先使用期望
    if expected_layout:
        exp_rows, exp_cols = expected_layout
        if rows != exp_rows or cols != exp_cols:
            print(f"[警告] 检测到的布局 ({rows}x{cols}) 与期望 ({exp_rows}x{exp_cols}) 不符")
            if exp_rows == 1 and exp_cols == count:
                print(f"[修正] 强制使用 {exp_cols} 列分割")
                rows, cols = exp_rows, exp_cols
            elif exp_rows == 2 and exp_cols * 2 == count:
                print(f"[修正] 强制使用 {exp_rows}x{exp_cols} 布局")
                rows, cols = exp_rows, exp_cols

    # 调用通用分割
    views = split_universal_grid(image, rows, cols, v_gaps, h_gaps, margin=margin)
    
    # 如果产生了正确数量的视图，应用期望的名称
    if expected_views and len(views) == len(expected_views):
        print(f"[命名] 应用期望的视图名称: {expected_views}")
        new_views = []
        for i, (old_name, img) in enumerate(views):
            new_views.append((expected_views[i], img))
        return new_views
        
    return views


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
    margin: int = 5,
    expected_views: List[str] = None
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
    views = split_quadrant_image(image, margin=margin, expected_views=expected_views)
    
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
