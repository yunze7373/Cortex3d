"""图像处理类节点 (5) — 切割 / 去背景 / 碎片清除 / 增强 / 合并。"""
from __future__ import annotations
import os
from ..utils.errors import node_guard

CAT = "Cortex3d/Process"


class Cortex3d_MultiviewCutter:
    """将多视角拼合图切割成独立视图列表。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":       ("IMAGE",),
                "view_config": ("CORTEX_VIEW_CONFIG",),
            },
            "optional": {
                "margin":   ("INT",     {"default": 4, "min": 0, "max": 32}),
                "no_rembg": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES   = ("IMAGE",)
    RETURN_NAMES   = ("views",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION       = "execute"
    CATEGORY       = CAT

    @node_guard()
    def execute(self, image, view_config, margin=4, no_rembg=False):
        from ..adapters.image_adapter import ImageAdapter
        from ..bridge.file_bridge import FileBridge
        import torch
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        out_dir = str(fb.make_output_dir("comfyui_cut"))
        # 适配器期望 views: int 和 remove_bg: bool（与节点 no_rembg 逻辑反转）
        num_views = getattr(view_config, "num_views", 4)
        view_paths = ImageAdapter.cut_multiview(
            image_path=img_path,
            output_dir=out_dir,
            views=num_views,
            remove_bg=not no_rembg,
            margin=margin,
        )
        tensors = [fb.path_to_tensor(p) for p in view_paths if os.path.isfile(p)]
        if not tensors:
            return ([image],)
        return (tensors,)


class Cortex3d_BackgroundRemover:
    """使用 rembg 去除背景，返回 RGBA → RGB（白底）。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "model": (["u2net", "u2net_human_seg", "isnet-general-use"], {"default": "isnet-general-use"}),
                "bg_color": (["white", "black", "transparent"], {"default": "white"}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, image, model="isnet-general-use", bg_color="white"):
        from ..adapters.image_adapter import ImageAdapter
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        out_dir = fb.make_output_dir("comfyui_rembg")
        output_path = str(out_dir / "rembg_result.png")
        # 适配器签名仅接受 (image_path, output_path)
        result_path = ImageAdapter.remove_background(
            image_path=img_path, output_path=output_path,
        )
        if result_path and os.path.isfile(result_path):
            return (fb.path_to_tensor(result_path),)
        return (image,)


class Cortex3d_FragmentCleaner:
    """碎片清除：删除掩码中的小连通域，保留最大主体。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":         ("IMAGE",),
                "min_area_ratio": ("FLOAT", {"default": 0.05, "min": 0.001, "max": 0.5, "step": 0.005}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, image, min_area_ratio=0.05):
        from ..bridge.file_bridge import FileBridge
        from PIL import Image as PILImage
        import numpy as np
        import torch
        fb = FileBridge()
        pil = fb.tensor_to_pil(image)
        arr = np.array(pil.convert("RGBA"))
        alpha = arr[:, :, 3]
        # 保留面积超过阈值的连通域
        try:
            import cv2
            _, binary = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
            n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
            total = alpha.size
            mask = np.zeros_like(alpha)
            for i in range(1, n_labels):
                if stats[i, cv2.CC_STAT_AREA] / total >= min_area_ratio:
                    mask[labels == i] = 255
            arr[:, :, 3] = mask
        except ImportError:
            pass  # 无 cv2 时跳过清洗
        result = PILImage.fromarray(arr, "RGBA").convert("RGB")
        tensor = torch.from_numpy(np.array(result).astype("float32") / 255.0).unsqueeze(0)
        return (tensor,)


class Cortex3d_ImageEnhancer:
    """Super-Resolution / GFPGAN 人脸增强。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "scale":           ("INT",     {"default": 2, "min": 1, "max": 4}),
                "target_size":     ("INT",     {"default": 0, "min": 0, "max": 4096, "step": 64}),
                "no_realesrgan":   ("BOOLEAN", {"default": False}),
                "no_gfpgan":       ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, image, scale=2, target_size=0, no_realesrgan=False, no_gfpgan=False):
        from ..adapters.image_adapter import ImageAdapter
        from ..bridge.file_bridge import FileBridge
        fb = FileBridge()
        img_path = fb.tensor_to_tmp_png(image)
        out_dir = fb.make_output_dir("comfyui_enhance")
        output_path = str(out_dir / "enhanced_result.png")
        # 适配器期望 use_realesrgan/use_gfpgan (正逻辑) 和 output_path
        result = ImageAdapter.enhance(
            image_path=img_path,
            scale=scale,
            target_size=target_size if target_size > 0 else 1024,
            use_realesrgan=not no_realesrgan,
            use_gfpgan=not no_gfpgan,
            output_path=output_path,
        )
        if result and os.path.isfile(result):
            return (fb.path_to_tensor(result),)
        return (image,)


class Cortex3d_ImageListMerge:
    """将 IMAGE 列表按行/列拼合成单张图（用于预览或调试）。"""
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images":  ("IMAGE",),
                "columns": ("INT", {"default": 2, "min": 1, "max": 8}),
            }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("merged",)
    FUNCTION      = "execute"
    CATEGORY      = CAT

    @node_guard()
    def execute(self, images, columns):
        import math
        import torch
        import torch.nn.functional as F

        columns = columns[0] if isinstance(columns, list) else columns
        if not images:
            return (torch.zeros(1, 64, 64, 3),)

        flat = []
        for img in images:
            if img.dim() == 4:
                for i in range(img.shape[0]):
                    flat.append(img[i])
            else:
                flat.append(img)

        if not flat:
            return (torch.zeros(1, 64, 64, 3),)

        # 统一大小（以第一张为基准）
        h, w = flat[0].shape[:2]
        resized = []
        for t in flat:
            if t.shape[0] != h or t.shape[1] != w:
                t = F.interpolate(t.permute(2, 0, 1).unsqueeze(0), size=(h, w), mode="bilinear", align_corners=False)
                t = t.squeeze(0).permute(1, 2, 0)
            resized.append(t)

        rows = math.ceil(len(resized) / columns)
        grid_rows = []
        for r in range(rows):
            row_imgs = resized[r * columns: (r + 1) * columns]
            while len(row_imgs) < columns:
                row_imgs.append(torch.zeros(h, w, 3))
            grid_rows.append(torch.cat(row_imgs, dim=1))
        merged = torch.cat(grid_rows, dim=0).unsqueeze(0)
        return (merged,)
