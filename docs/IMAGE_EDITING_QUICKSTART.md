# Cortex3d 图像编辑模式使用指南

> 使用 Gemini 的语义图像编辑能力快速修改角色图像的元素、修复细节问题

## 🎯 概述

Cortex3d 现在支持两种新的工作模式：

1. **编辑模式** (`--mode-edit`) - 添加、移除或修改角色图像中的元素
2. **细节修复模式** (`--mode-refine`) - 修复角色图像中特定部位的缺陷或问题

这些模式使用 Gemini 的图像编辑能力，不需要重新生成整个角色。

## 🔧 编辑模式 (`--mode-edit`)

### 使用场景

- 为角色添加新元素（装备、配件、装饰品等）
- 移除不需要的元素
- 修改现有元素的外观

### 参数说明

| 参数 | 类型 | 必需 | 说明 | 示例 |
|-----|------|------|------|------|
| `--mode-edit` | flag | ✅ | 激活编辑模式 | - |
| `--edit-elements` | string | ✅ | 编辑指令 | `"add:肩部炮台"` |
| `--from-edited` | path | ✅ | 源图像路径 | `"outputs/char_front.png"` |
| `--character` | string | ⏩ | 角色描述（可选，用于更好的编辑效果） | `"赛博女战士"` |
| `--token` | string | ⏩ | API Token（可选，使用环境变量则不需要） | - |
| `--output` | path | ⏩ | 输出目录（默认：test_images） | `"outputs"` |
| `--model` | string | ⏩ | 模型名称（默认：gemini-2.5-flash） | `"gemini-3-pro-image"` |

### 编辑指令格式

编辑指令使用 `[操作]:[目标]` 的格式：

```
add:xxx       # 添加元素
remove:xxx    # 移除元素
modify:xxx    # 修改元素
```

### 使用示例

**例1：为赛博女战士添加肩部炮台**

```bash
export GEMINI_API_KEY="your-api-key"

python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:肩部双联装加特林炮" \
  --from-edited "test_images/character_front.png" \
  --character "赛博女战士，穿着黑色皮衣" \
  --output "outputs"
```

**例2：移除角色头顶的装饰品**

```bash
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "remove:头顶的蝴蝶结" \
  --from-edited "test_images/character_front.png" \
  --character "甜美女孩"
```

**例3：修改角色手中的武器**

```bash
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "modify:左手的剑为光剑" \
  --from-edited "test_images/character_front.png" \
  --character "未来战士"
```

### 输出

编辑完成后，系统会在输出目录生成编辑后的图像：

```
outputs/
├── add_edited_20250101_120000.png      # 添加元素的结果
├── remove_edited_20250101_120100.png   # 移除元素的结果
└── modify_edited_20250101_120200.png   # 修改元素的结果
```

## 🎨 细节修复模式 (`--mode-refine`)

### 使用场景

- 修复脸部缺陷或不自然的地方
- 改正手部的错误（多出来的手指、变形等）
- 调整身体姿态或比例
- 修复眼睛、嘴部等细节
- 自定义其他部位的问题

### 参数说明

| 参数 | 类型 | 必需 | 说明 | 示例 |
|-----|------|------|------|------|
| `--mode-refine` | flag | ✅ | 激活细节修复模式 | - |
| `--refine-details` | choice | ✅ | 修复部位 | `"face"` \| `"hands"` \| `"pose"` \| `"eyes"` \| `"custom"` |
| `--detail-issue` | string | ✅ | 问题描述 | `"左手有6根手指需要改为5根"` |
| `--from-refine` | path | ✅ | 源图像路径 | `"outputs/char_front.png"` |
| `--character` | string | ⏩ | 角色描述（可选） | `"动漫女孩"` |
| `--token` | string | ⏩ | API Token（可选） | - |
| `--output` | path | ⏩ | 输出目录（默认：test_images） | `"outputs"` |
| `--model` | string | ⏩ | 模型名称（默认：gemini-2.5-flash） | `"gemini-3-pro-image"` |

### 修复部位选项

- `face` - 修复脸部的任何问题
- `hands` - 修复手部的任何问题
- `pose` - 修复身体姿态或比例
- `eyes` - 专门修复眼睛
- `custom` - 自定义修复（配合 `--detail-issue` 参数）

### 使用示例

**例1：修复脸部不自然的地方**

```bash
export GEMINI_API_KEY="your-api-key"

python scripts/generate_character.py \
  --mode-refine \
  --refine-details "face" \
  --detail-issue "脸部看起来很不自然，嘴型有点扭曲" \
  --from-refine "test_images/character_front.png" \
  --character "动漫女孩"
```

**例2：修复手部错误（多指）**

```bash
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "hands" \
  --detail-issue "左手有6根手指，需要改为正常的5根" \
  --from-refine "test_images/character_front.png" \
  --character "战士"
```

**例3：调整身体比例**

```bash
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "pose" \
  --detail-issue "身体比例看起来不对，头部太大，身体太小" \
  --from-refine "test_images/character_front.png"
```

**例4：专门修复眼睛**

```bash
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "eyes" \
  --detail-issue "眼睛看起来呆滞，需要更有神采的表情" \
  --from-refine "test_images/character_front.png"
```

**例5：自定义修复（例如修复耳朵）**

```bash
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "custom" \
  --detail-issue "右耳朵看起来像变形了，需要修复成正常的耳朵形状" \
  --from-refine "test_images/character_front.png"
```

### 输出

细节修复完成后，系统会在输出目录生成修复后的图像：

```
outputs/
├── refined_face_20250101_120000.png      # 脸部修复结果
├── refined_hands_20250101_120100.png     # 手部修复结果
├── refined_pose_20250101_120200.png      # 姿态修复结果
└── refined_eyes_20250101_120300.png      # 眼睛修复结果
```

## 💡 最佳实践

### 1. 清晰的指令

编写清晰、具体的指令会获得更好的结果：

```bash
# ❌ 不清晰
--edit-elements "add:东西"

# ✅ 清晰
--edit-elements "add:右肩膀上的黄色发光球体，像能量球"
```

### 2. 提供角色描述

提供 `--character` 参数可以帮助 AI 更好地理解上下文：

```bash
# 更好
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:戏法師的魔法杖" \
  --from-edited "image.png" \
  --character "奇幻世界的女性戏法師，穿着紫色魔法长袍"

# 不如上面
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:魔法杖" \
  --from-edited "image.png"
```

### 3. 使用高质量源图像

- 使用 Cortex3d 生成的图像作为源（效果更好）
- 确保人物完整清晰可见
- 避免过度失真或模糊的图像

### 4. 多步骤编辑工作流

对于复杂的编辑，可以分步进行：

```bash
# 步骤1：添加第一个元素
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:左肩装备" \
  --from-edited "original.png" \
  --output "step1"

# 步骤2：基于第一步的结果添加第二个元素
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:右肩装备" \
  --from-edited "step1/add_edited_*.png" \
  --output "step2"

# 步骤3：最后进行细节修复
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "face" \
  --from-refine "step2/add_edited_*.png" \
  --output "final"
```

## 🛠️ 故障排除

### 问题1：找不到 API Key

**症状**：
```
[ERROR] No valid API key found
```

**解决方案**：
```bash
# 使用 --token 参数明确指定
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:xxx" \
  --from-edited "image.png" \
  --token "your-gemini-api-key"

# 或设置环境变量
export GEMINI_API_KEY="your-gemini-api-key"
```

### 问题2：源图像不存在

**症状**：
```
[ERROR] Source image not found: ...
```

**解决方案**：
- 检查图像路径是否正确
- 使用绝对路径而不是相对路径
- 确保文件实际存在

### 问题3：编辑效果不理想

**症状**：编辑结果看起来不像预期

**解决方案**：
- 提供更详细的指令：`"add:蓝色发光的肩部护甲，有科技感"` 而不是 `"add:盔甲"`
- 提供完整的角色描述：`--character "赛博朋克女战士，高科技未来风格，紫蓝色配色"`
- 尝试不同的模型：`--model "gemini-3-pro-image"` 可能效果更好

## 📊 工作流对比

| 任务 | 方案1: 重新生成 | 方案2: 使用编辑模式 | 优势 |
|-----|-------------|----------------|------|
| 为角色添加武器 | 🕐🕐🕐 (3+ 分钟) | ⚡ (~30秒) | 快速 |
| 修复手指错误 | 🕐🕐🕐 (3+ 分钟) | ⚡ (~30秒) | 快速 |
| 微调配色 | 🕐🕐🕐 (3+ 分钟) | ⚡ (~30秒) | 快速 |
| 完整重新设计 | ⚡ (正确做法) | ❌ (不适用) | 效果更好 |

## 🚀 下一步

- **串联工作流**：结合编辑和修复模式处理复杂的角色改进
- **脚本化处理**：编写脚本对多个图像进行批量编辑
- **3D 集成**：编辑完成后直接用于 3D 建模流水线

## 参考资源

- [Gemini 图像编辑官方文档](https://ai.google.dev/docs/gemini-2-5-flash-planning-guide#image_editing)
- [Cortex3d 主 README](../README.md)
- [Gemini 图像编辑集成文档](GEMINI_IMAGE_EDITING_INTEGRATION.md)
- [Gemini 图像编辑快速参考](GEMINI_IMAGE_EDITING_CHEATSHEET.md)
