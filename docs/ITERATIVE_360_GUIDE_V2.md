# 迭代 360° 生成模式指南 v2

## 📌 概述

新增 `--iterative-360 {4,6,8}` 模式实现 **Gemini API 360° 角色一致性生成**，严格遵循官方文档建议：

> **Character Consistency: 360 view** - Generate 360-degree views by iteratively prompting for different angles. For best results, include previously generated images in subsequent prompts to maintain consistency.

### 支持的视角数量

| 模式 | 视角序列 | 布局 | 描述 |
|------|---------|------|------|
| **4-view** | FRONT (0°) → RIGHT (90°) → BACK (180°) → LEFT (270°) | 1×4 水平 | 标准四视角 |
| **6-view** | FRONT → FRONT_RIGHT (45°) → RIGHT → BACK → BACK_LEFT (225°) → LEFT | 2×3 | 包含 45° 角度 |
| **8-view** | 上述 6 个 + TOP + BOTTOM | 2×4 右侧为 TOP/BOTTOM | 完整 360° 覆盖 |

---

## 🎯 工作原理

### 迭代 360° 模式

每个视角都基于**前一个视角的生成结果作为参考图**，通过迭代参考来最大化一致性：

```
初始参考图
    ↓
[Step 1: 生成 FRONT] → Image_1
    ↓ (Image_1 作为下一步参考)
[Step 2: 生成 RIGHT] → Image_2
    ↓ (Image_2 作为下一步参考)
[Step 3: 生成 BACK] → Image_3
    ↓
... (持续迭代) ...
    ↓
[最后: 合成多视角] → 最终输出
```

### 关键机制

1. **初始参考**：使用 `--from-image` 提供的图像
2. **迭代参考**：每步完成后，将生成的图像作为下一步的参考
3. **一致性指令**：每步提示词自动注入 "Keep pose/expression IDENTICAL, only camera angle changes"
4. **动态合成**：根据视角数自动拼接成合适的布局

---

## 📝 使用方法

### 命令格式

```bash
python scripts/generate_character.py \
  --from-image <reference_image> \
  --iterative-360 {4|6|8} \
  --mode direct \
  [其他选项]
```

### 使用示例

#### 4-view 迭代生成
```bash
python scripts/generate_character.py \
  --from-image reference_images/character.png \
  --iterative-360 4 \
  --mode direct \
  --photorealistic
```

#### 6-view 迭代生成（更细致的 360°）
```bash
python scripts/generate_character.py \
  --from-image reference_images/character.png \
  --iterative-360 6 \
  --mode direct \
  --photorealistic \
  --resolution 2K
```

#### 8-view 完整 360°（包括上下视角）
```bash
python scripts/generate_character.py \
  --from-image reference_images/character.png \
  --iterative-360 8 \
  --mode direct \
  --strict \
  --resolution 2K \
  --preview
```

### 参数对应表

| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `--from-image <path>` | ✅ | - | 参考图像路径 |
| `--iterative-360 {4,6,8}` | ✅ | - | 迭代模式 + 视角数 |
| `--mode direct` | ✅ | proxy | Gemini 直连模式（需要 GEMINI_API_KEY） |
| `--photorealistic` | ✗ | - | 写实风格生成（推荐） |
| `--strict` | ✗ | - | 严格复制模式（100% 基于参考） |
| `--resolution` | ✗ | 2K | 分辨率: 1K/2K/4K |
| `--preview` | ✗ | - | 完成后自动打开预览 |
| `--output` | ✗ | test_images | 输出目录 |

---

## 📊 执行流程详解

### 4-view 迭代示例

```
【初始化】
 参考图: character.png
 模式: --iterative-360 4

【第 1/4 步】FRONT 视图 (0°)
 输入: character.png + "Generate front view"
 输出: FRONT_0.png ✅

【第 2/4 步】RIGHT 视图 (90°)
 输入: FRONT_0.png (作为参考) + "Keep pose identical, only rotate camera to 90°"
 输出: RIGHT_90.png ✅

【第 3/4 步】BACK 视图 (180°)
 输入: RIGHT_90.png (作为参考) + "Keep pose identical, only rotate camera to 180°"
 输出: BACK_180.png ✅

【第 4/4 步】LEFT 视图 (270°)
 输入: BACK_180.png (作为参考) + "Keep pose identical, only rotate camera to 270°"
 输出: LEFT_270.png ✅

【合成】
 合并 4 张图: [FRONT | RIGHT | BACK | LEFT]
 输出: iterative_360_composite_4view.png 🎉
```

### 输出文件结构

```
test_images/
├── iterative_360_composite_4view.png      # 最终 4-view 合成
│   ├── FRONT_0.png
│   ├── RIGHT_90.png
│   ├── BACK_180.png
│   └── LEFT_270.png
├── iterative_360_composite_6view.png      # 最终 6-view 合成 (如果选择 --iterative-360 6)
└── iterative_360_composite_8view.png      # 最终 8-view 合成 (如果选择 --iterative-360 8)
```

---

## 🛠️ 与 Gemini API 最佳实践对应

| 文档建议 | 本实现 | 状态 |
|---------|--------|------|
| "Include previously generated images in subsequent prompts" | 每步都用前一张作参考 | ✅ |
| "Iteratively prompt for different angles" | 4/6/8 步迭代 | ✅ |
| "Maintain consistency" | 动态提示词注入 + 参考传递 | ✅ |
| "Use semantic negative prompts" | QUALITY REQUIREMENTS | ✅ |
| "Control the camera" | 每步明确相机角度 | ✅ |
| "Iterate and refine" | 多步骤本质上是细化过程 | ✅ |

---

## 📈 性能对比

### 4-view 一次生成 vs 迭代 4-view

| 方面 | 一次性生成 | 迭代 360°4 |
|------|----------|-----------|
| 生成时间 | ~1-2 分钟 | ~4-8 分钟 |
| 角色头方向一致 | 中等 | 优秀 ⭐⭐ |
| 身体姿势锁定 | 中等 | 优秀 ⭐⭐ |
| 肢体位置一致 | 中等 | 优秀 ⭐⭐ |
| API 调用次数 | 1 | 4 |
| 官方推荐度 | 否 | 是 ✅ |

### 视角数量对比

| 模式 | 步数 | 生成时间 | 细节覆盖 | 文件数 | 推荐场景 |
|------|------|---------|---------|--------|---------|
| 4-view | 4 | ~4 min | 基础 | 4 张 | 快速原型 |
| 6-view | 6 | ~6 min | 中等 | 6 张 | 标准品质 |
| 8-view | 8 | ~8 min | 完整 | 8 张 | 专业/商业 |

---

## ⚠️ 重要注意事项

### 1. 必须使用 `--from-image`
```bash
# ❌ 错误
python scripts/generate_character.py "描述" --iterative-360 4

# ✅ 正确
python scripts/generate_character.py --from-image ref.png --iterative-360 4
```

### 2. 必须使用 `--mode direct`（Gemini 直连）
```bash
# ❌ 代理模式不支持
python scripts/generate_character.py --from-image ref.png --iterative-360 4 --mode proxy

# ✅ 必须用直连
python scripts/generate_character.py --from-image ref.png --iterative-360 4 --mode direct
```

### 3. 需要设置 `GEMINI_API_KEY`
```bash
# Linux/Mac
export GEMINI_API_KEY="your-key-here"

# Windows PowerShell
$env:GEMINI_API_KEY="your-key-here"

# 或在命令中指定
python scripts/generate_character.py --from-image ref.png --iterative-360 4 --token your-key
```

### 4. 生成时间比一次性多 4 倍
- 4-view：~4-8 分钟
- 6-view：~6-12 分钟
- 8-view：~8-16 分钟

### 5. API 配额消耗
每次迭代 360° 相当于多次 API 调用（4 次、6 次或 8 次）

---

## 🔧 故障排除

### Q: 提示 "iterative-360 requires --from-image"
**A**: 检查是否提供了 `--from-image`
```bash
# ❌ 缺少参考图
python scripts/generate_character.py --iterative-360 4

# ✅ 提供参考图
python scripts/generate_character.py --from-image character.png --iterative-360 4
```

### Q: 提示 "mode must be 'direct'"
**A**: 迭代 360° 仅支持 Gemini 直连，不支持代理模式
```bash
python scripts/generate_character.py \
  --from-image ref.png \
  --iterative-360 4 \
  --mode direct  # ← 必须指定 direct
```

### Q: 某个中间步骤失败
**A**: 可能是 API 限流或网络问题，稍后重试

### Q: 生成的 4 个视角看起来不一样
**A**: 这是正常现象（不同角度确实有区别），但如果发现：
- **头部方向明显改变**
- **身体姿势改变**
- **肢体位置交换**

这说明 Gemini 未能保持一致性，可尝试：
1. 使用更清晰/高质量的参考图
2. 添加 `--strict` 模式
3. 提供更详细的文字描述

---

## 💡 高级用法

### 结合 --strict 模式（最严格）
```bash
python scripts/generate_character.py \
  --from-image ref.png \
  --iterative-360 6 \
  --mode direct \
  --strict
```

### 自动转 3D（完整流水线）
```bash
python scripts/generate_character.py \
  --from-image ref.png \
  --iterative-360 6 \
  --mode direct \
  --to-3d \
  --algo hunyuan3d
```

### 导出提示词（不实际生成）
```bash
python scripts/generate_character.py \
  --from-image ref.png \
  --iterative-360 4 \
  --mode direct \
  --export-prompt
```

---

## 📚 相关资源

- [Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/image-generation)
- [Cortex3d README](README.md)
- [多视角生成详细指南](MULTIVIEW_GUIDE.md) (如果存在)

---

**最后更新**: 2026-01-22  
**版本**: 2.0 (Multi-view Support)  
**状态**: ✅ 生产就绪
