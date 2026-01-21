#!/usr/bin/env python3
"""
图像编辑工具库
为 Gemini API 图像编辑功能提供辅助函数和工具

功能:
    - 图像输入验证和加载
    - 多图像输入处理
    - 编辑提示词构建
    - 思维签名管理 (Gemini 3 Pro)
    - 编辑会话历史管理
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import base64
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy imports
PIL_Image = None


def _ensure_pil():
    """延迟导入 PIL"""
    global PIL_Image
    if PIL_Image is None:
        try:
            from PIL import Image as _Image
            PIL_Image = _Image
        except ImportError:
            raise ImportError(
                "缺少 PIL 依赖: pip install pillow"
            )


# =============================================================================
# 图像输入验证与加载
# =============================================================================

def validate_image_input(image_path: str) -> Tuple[bool, str]:
    """
    验证图像输入
    
    Args:
        image_path: 图像文件路径
    
    Returns:
        (是否有效, 错误消息或空字符串)
    """
    _ensure_pil()
    
    path = Path(image_path)
    
    # 检查文件是否存在
    if not path.exists():
        return False, f"文件不存在: {image_path}"
    
    # 检查文件格式
    supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    if path.suffix.lower() not in supported_formats:
        return False, f"不支持的图像格式: {path.suffix}。支持: {supported_formats}"
    
    # 尝试打开图像
    try:
        img = PIL_Image.open(path)
        img.verify()
        return True, ""
    except Exception as e:
        return False, f"无法打开图像: {str(e)}"


def load_image_as_base64(image_path: str) -> Optional[str]:
    """
    加载图像并转换为 base64
    
    Args:
        image_path: 图像文件路径
    
    Returns:
        base64 编码的字符串，或 None 如果失败
    """
    _ensure_pil()
    
    # 验证
    is_valid, error = validate_image_input(image_path)
    if not is_valid:
        logger.error(f"图像验证失败: {error}")
        return None
    
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_str = base64.b64encode(image_data).decode('utf-8')
            logger.info(f"✅ 已加载图像: {Path(image_path).name} ({len(image_data) / 1024:.1f}KB)")
            return base64_str
    except Exception as e:
        logger.error(f"❌ 加载图像失败: {str(e)}")
        return None


def get_image_mime_type(image_path: str) -> str:
    """
    获取图像的 MIME 类型
    
    Args:
        image_path: 图像文件路径
    
    Returns:
        MIME 类型字符串
    """
    suffix = Path(image_path).suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }
    return mime_types.get(suffix, 'image/png')


# =============================================================================
# 多图像输入处理
# =============================================================================

def process_multi_image_input(
    image_paths: List[str],
    max_images: int = 14,
    validate_only: bool = False
) -> Tuple[bool, List[Dict[str, str]], str]:
    """
    处理多个图像输入
    
    Args:
        image_paths: 图像路径列表
        max_images: 最大允许的图像数
        validate_only: 仅验证，不加载
    
    Returns:
        (是否成功, 图像数据列表, 错误消息)
        
    图像数据格式:
        {
            'path': '原始路径',
            'base64': 'base64数据',
            'mime_type': 'image/png',
            'name': '文件名'
        }
    """
    # 检查数量限制
    if len(image_paths) > max_images:
        return False, [], f"图像数量超过限制: {len(image_paths)} > {max_images}"
    
    # 验证所有图像
    results = []
    errors = []
    
    for i, path in enumerate(image_paths):
        is_valid, error = validate_image_input(path)
        if not is_valid:
            errors.append(f"图像 {i+1}: {error}")
            continue
        
        if not validate_only:
            base64_data = load_image_as_base64(path)
            if base64_data is None:
                errors.append(f"图像 {i+1}: 无法加载")
                continue
            
            results.append({
                'path': path,
                'base64': base64_data,
                'mime_type': get_image_mime_type(path),
                'name': Path(path).name
            })
        else:
            results.append({
                'path': path,
                'name': Path(path).name
            })
    
    if errors:
        error_msg = "; ".join(errors)
        return False, results, error_msg
    
    logger.info(f"✅ 已加载 {len(results)} 个图像")
    return True, results, ""


# =============================================================================
# 编辑提示词构建
# =============================================================================

def compose_edit_prompt(
    edit_type: str,  # "add", "remove", "modify"
    edit_instruction: str,
    character_description: str,
    additional_context: str = ""
) -> str:
    """
    构建添加/移除/修改元素的提示词
    
    Args:
        edit_type: 编辑类型 (add/remove/modify)
        edit_instruction: 编辑指令详情
        character_description: 角色描述
        additional_context: 额外上下文
    
    Returns:
        构建的 Prompt 字符串
    """
    base_template = (
        "Using the provided image of {character}, please {action} {instruction} "
        "to/from the scene. Ensure the change is integrated seamlessly with the "
        "original style, lighting, composition, and the character's pose. "
        "The modification should be professional and natural-looking."
    )
    
    action_map = {
        "add": "add",
        "remove": "remove",
        "modify": "modify"
    }
    
    action = action_map.get(edit_type, "modify")
    
    prompt = base_template.format(
        character=character_description,
        action=action,
        instruction=edit_instruction
    )
    
    if additional_context:
        prompt += f"\n\nAdditional context: {additional_context}"
    
    return prompt


def compose_refine_prompt(
    detail_part: str,  # "face", "hands", "pose", "custom"
    issue_description: str,
    character_description: str,
    preservation_notes: str = ""
) -> str:
    """
    构建语义遮盖/细节修复的提示词
    
    Args:
        detail_part: 要修改的部位
        issue_description: 问题描述
        character_description: 角色描述
        preservation_notes: 保留说明
    
    Returns:
        构建的 Prompt 字符串
    """
    base_template = (
        "Using the provided image of {character}, change only the {part} to "
        "{issue}. Keep everything else in the image exactly the same, "
        "preserving the original style, lighting, composition, and all other elements. "
        "Make ONLY the specified change, nothing else."
    )
    
    prompt = base_template.format(
        character=character_description,
        part=detail_part,
        issue=issue_description
    )
    
    if preservation_notes:
        prompt += f"\n\nPreservation notes: {preservation_notes}"
    
    return prompt


def compose_style_transfer_prompt(
    target_style: str,
    character_description: str
) -> str:
    """
    构建风格迁移的提示词
    
    Args:
        target_style: 目标风格描述
        character_description: 角色描述
    
    Returns:
        构建的 Prompt 字符串
    """
    template = (
        "Transform the provided image of {character} into the artistic style of "
        "{style}. Preserve the original composition, subject matter, and pose, "
        "but render it with the specified stylistic elements. The transformation "
        "should be professional and maintain all key details from the original."
    )
    
    return template.format(
        character=character_description,
        style=target_style
    )


def compose_composite_prompt(
    scene_description: str,
    num_images: int
) -> str:
    """
    构建多图合成的提示词
    
    Args:
        scene_description: 场景描述
        num_images: 输入图像数量
    
    Returns:
        构建的 Prompt 字符串
    """
    template = (
        "Create a new image by combining the elements from the {num} provided images. "
        "Compose them according to this scene description: {scene}. "
        "Ensure all elements are properly integrated with consistent lighting, "
        "perspective, and style. The final image should look like a cohesive scene."
    )
    
    return template.format(
        num=num_images,
        scene=scene_description
    )


# =============================================================================
# 思维签名管理 (Gemini 3 Pro)
# =============================================================================

class ThoughtSignatureManager:
    """
    管理 Gemini 3 Pro 的思维签名
    用于保持多轮对话中的推理上下文
    """
    
    def __init__(self):
        self.signatures: Dict[str, str] = {}
        self.history: List[Dict[str, Any]] = []
    
    def store_signature(self, key: str, signature: str):
        """存储思维签名"""
        self.signatures[key] = signature
        logger.debug(f"Stored thought signature: {key}")
    
    def get_signature(self, key: str) -> Optional[str]:
        """获取思维签名"""
        return self.signatures.get(key)
    
    def extract_from_response(self, response) -> bool:
        """
        从 API 响应中提取思维签名
        
        Args:
            response: Gemini API 响应对象
        
        Returns:
            是否成功提取
        """
        try:
            if hasattr(response, 'thought_signature'):
                self.store_signature('last', response.thought_signature)
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to extract thought signature: {str(e)}")
            return False
    
    def add_to_history(self, message: str, response = None):
        """添加到会话历史"""
        entry = {'message': message}
        if response:
            entry['response'] = response
            self.extract_from_response(response)
        self.history.append(entry)


# =============================================================================
# 编辑会话管理
# =============================================================================

class EditSession:
    """
    管理编辑会话的状态和历史
    支持多步骤编辑操作
    """
    
    def __init__(self, session_id: str, character_description: str):
        self.session_id = session_id
        self.character_description = character_description
        self.edits: List[Dict[str, Any]] = []
        self.signatures = ThoughtSignatureManager()
        self.source_image: Optional[str] = None
    
    def set_source_image(self, image_path: str):
        """设置源图像"""
        is_valid, error = validate_image_input(image_path)
        if not is_valid:
            logger.error(f"Invalid source image: {error}")
            return False
        self.source_image = image_path
        logger.info(f"✅ Source image set: {Path(image_path).name}")
        return True
    
    def add_edit(self, edit_type: str, instruction: str, result_path: Optional[str] = None):
        """记录编辑操作"""
        edit = {
            'type': edit_type,
            'instruction': instruction,
            'result_path': result_path,
            'step': len(self.edits) + 1
        }
        self.edits.append(edit)
        logger.info(f"Added edit {edit['step']}: {edit_type} - {instruction[:50]}...")
    
    def get_edit_history(self) -> List[Dict[str, Any]]:
        """获取编辑历史"""
        return self.edits
    
    def get_status(self) -> Dict[str, Any]:
        """获取会话状态"""
        return {
            'session_id': self.session_id,
            'character': self.character_description,
            'source_image': self.source_image,
            'edits_count': len(self.edits),
            'edits': self.edits
        }


# =============================================================================
# 辅助工具函数
# =============================================================================

def parse_edit_instruction(instruction_str: str) -> Tuple[str, str]:
    """
    解析编辑指令字符串
    格式: "add:xxx" 或 "remove:xxx" 或 "modify:xxx"
    
    Args:
        instruction_str: 编辑指令字符串
    
    Returns:
        (操作类型, 详细指令)
    """
    if ':' not in instruction_str:
        return "modify", instruction_str
    
    parts = instruction_str.split(':', 1)
    action = parts[0].lower().strip()
    detail = parts[1].strip()
    
    if action not in ['add', 'remove', 'modify']:
        logger.warning(f"Unknown action: {action}, treating as modify")
        return "modify", instruction_str
    
    return action, detail


def format_edit_summary(edit_type: str, instruction: str, output_path: str) -> str:
    """
    格式化编辑操作摘要
    
    Args:
        edit_type: 编辑类型
        instruction: 编辑指令
        output_path: 输出路径
    
    Returns:
        格式化的摘要字符串
    """
    action_text = {
        'add': '✨ 添加',
        'remove': '🗑️ 移除',
        'modify': '✏️ 修改',
        'refine': '🎯 优化'
    }.get(edit_type, '⚙️ 编辑')
    
    return f"{action_text}: {instruction}\n  📁 输出: {Path(output_path).name}"


if __name__ == "__main__":
    # 测试工具库
    logger.info("Image Editor Utils Library - v1.0")
    logger.info("This module provides utilities for Gemini image editing features")
