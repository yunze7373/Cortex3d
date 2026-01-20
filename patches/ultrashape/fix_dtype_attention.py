"""
UltraShape dtype 修复补丁
修复 scaled_dot_product_attention 的混合精度问题

应用方式：
    在 Dockerfile.ultrashape 中添加：
    COPY patches/ultrashape/fix_dtype_attention.py /opt/ultrashape/ultrashape/models/denoisers/
    RUN cd /opt/ultrashape && python3 -c "from ultrashape.models.denoisers.fix_dtype_attention import apply_patch; apply_patch()"
"""

import torch
import torch.nn.functional as F


def patched_attention_forward(self, x, rotary_cos=None, rotary_sin=None):
    """修复后的注意力前向传播 - 确保所有张量都是 float32"""
    B, L, C = x.shape
    
    # 确保输入是 float32
    x = x.float()
    
    q, k, v = self.qkv(x).reshape(B, L, 3, self.num_heads, self.head_dim).unbind(2)
    
    # 强制转换为 float32
    q = q.float()
    k = k.float()
    v = v.float()
    
    # 应用旋转位置编码（如果提供）
    if rotary_cos is not None and rotary_sin is not None:
        rotary_cos = rotary_cos.float()
        rotary_sin = rotary_sin.float()
        q, k = apply_rotary_emb(q, k, rotary_cos, rotary_sin)
    
    # Scaled dot-product attention
    q = q.transpose(1, 2)
    k = k.transpose(1, 2)
    v = v.transpose(1, 2)
    
    # 所有张量现在都应该是 float32
    x = F.scaled_dot_product_attention(q, k, v)
    x = x.transpose(1, 2).reshape(B, L, C)
    
    # 输出投影
    x = self.proj(x)
    return x


def apply_rotary_emb(q, k, cos, sin):
    """应用旋转位置编码"""
    # 确保所有张量类型一致
    q = q.float()
    k = k.float()
    cos = cos.float()
    sin = sin.float()
    
    # 分割实部和虚部
    q_r, q_i = q[..., ::2], q[..., 1::2]
    k_r, k_i = k[..., ::2], k[..., 1::2]
    
    # 旋转
    q_out_r = q_r * cos - q_i * sin
    q_out_i = q_r * sin + q_i * cos
    k_out_r = k_r * cos - k_i * sin
    k_out_i = k_r * sin + k_i * cos
    
    # 重新组合
    q_out = torch.stack([q_out_r, q_out_i], dim=-1).flatten(-2)
    k_out = torch.stack([k_out_r, k_out_i], dim=-1).flatten(-2)
    
    return q_out, k_out


def apply_patch():
    """应用补丁到 UltraShape DiT 模型"""
    import sys
    from pathlib import Path
    
    # 导入 DiT 模型
    try:
        from ultrashape.models.denoisers import dit_mask
        
        # 替换注意力层的 forward 方法
        if hasattr(dit_mask, 'Attention'):
            dit_mask.Attention.forward = patched_attention_forward
            print("✓ UltraShape Attention dtype patch applied successfully")
        else:
            print("⚠ Could not find Attention class in dit_mask")
            
    except ImportError as e:
        print(f"✗ Failed to apply patch: {e}")
        sys.exit(1)


if __name__ == "__main__":
    apply_patch()
