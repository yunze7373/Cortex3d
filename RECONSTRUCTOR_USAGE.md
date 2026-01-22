# Reconstructor.py 快速参考

## ✅ 已修复的问题

### 1. 算法名称更正
- ❌ **错误**: `hunyuan3d-2`
- ✅ **正确**: `hunyuan3d-2.1`

### 2. 新增 `--from-id` 参数支持

## 使用方法

### 方式一：直接指定图片路径
```bash
python scripts/reconstructor.py test_images/abc123_front.png --algo hunyuan3d-2.1 --no-texture
```

### 方式二：使用 Asset ID（新增）
```bash
python scripts/reconstructor.py --from-id <asset-id> --algo hunyuan3d-2.1 --no-texture
```

**示例**：
```bash
# 自动查找 test_images/57f1db7d-062f-4275-9325-0141b60c638f_front.png
python scripts/reconstructor.py --from-id 57f1db7d-062f-4275-9325-0141b60c638f --algo hunyuan3d-2.1 --no-texture
```

## `--from-id` 查找规则

脚本会在 `test_images/` 目录下按以下顺序查找：
1. `<id>_front.png`  ← 优先
2. `<id>.png`
3. `<id>.jpg`

找到第一个匹配的文件即停止。

## 完整命令示例

```bash
# 基础用法（Hunyuan3D 2.1，无纹理）
python scripts/reconstructor.py --from-id 57f1db7d-062f-4275-9325-0141b60c638f \
    --algo hunyuan3d-2.1 \
    --no-texture

# 高质量 + 锐化
python scripts/reconstructor.py --from-id abc123 \
    --algo hunyuan3d-2.1 \
    --quality high \
    --sharpen \
    --sharpen-strength 1.5

# UltraShape 精修
python scripts/reconstructor.py --from-id xyz789 \
    --algo trellis \
    --refine \
    --refine-preset balanced
```

## 可用算法

- `trellis` (默认)
- `trellis2`
- `instantmesh`
- `triposr`
- `hunyuan3d`
- `hunyuan3d-2.1` ← 你需要的版本
- `hunyuan3d-omni`
- `auto`
- `multiview`
