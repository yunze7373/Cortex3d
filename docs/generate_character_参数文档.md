# Cortex3d General Character 命令参数完整文档

## 概述

`generate_character.py` 是 Cortex3d 项目的核心角色生成脚本，支持多种生成模式、风格预设和高级功能。本文档详细介绍了所有可用的命令参数。

## 基本命令格式

```bash
python scripts/generate_character.py [DESCRIPTION] [OPTIONS]
```

## 基础参数

### 必需参数

| 参数 | 描述 | 示例 |
|------|------|------|
| `description` | 角色描述（可选，某些模式下可省略） | `"赛博朋克女战士"` |

### 生成模式

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--mode` | `proxy`, `direct`, `local` | `proxy` | 生成模式：proxy=AiProxy服务, direct=直连Gemini API, local=本地Z-Image |
| `--token` | 字符串 | 自动选择 | 认证Token（proxy模式使用AIPROXY_TOKEN，direct模式使用GEMINI_API_KEY） |

### 输入源

| 参数 | 描述 | 示例 |
|------|------|------|
| `--from-image` | 从参考图像提取角色特征 | `--from-image photo.jpg` |
| `--from-id` | 跳过2D生成，使用已存在的图像ID进行3D转换 | `--from-id a7af1af9-xxx` |

## 输出设置

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--output`, `-o` | `test_images` | 输出目录 |
| `--no-cut` | 否 | 禁用自动切割 |
| `--preview` | 否 | 生成后自动预览 |

## 多视角设置

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--views` | `4`, `6`, `8` | `4` | 视角数量：4=标准，6=包含45度角，8=包含顶部/底部 |
| `--custom-views` | 视角名称列表 | 无 | 自定义视角列表，覆盖`--views` |
| `--iterative-360` | `4`, `6`, `8` | 无 | 迭代360度模式，按顺序生成视图以提高一致性 |

### 可用视角选项
- `front` - 正面
- `front_right` - 右前方
- `right` - 右侧
- `back` - 背面
- `back_left` - 左后方
- `left` - 左侧
- `front_left` - 左前方
- `top` - 顶部
- `bottom` - 底部

## 图像质量设置

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--resolution` | `1K`, `2K`, `4K` | `2K` | 图像分辨率：1K=快速，2K=默认，4K=高质量但慢 |
| `--aspect-ratio` | `1:1`, `3:2`, `2:3`, `16:9`, `9:16`, `4:3`, `3:4` | 自动 | 图像宽高比 |
| `--pro` | 开关 | 否 | 使用高级Gemini Pro模型获得更高质量 |

## 风格预设

### 基础风格开关

| 参数 | 描述 |
|------|------|
| `--photorealistic`, `--real` | 写实风格（8k原始照片，真实纹理） |
| `--anime` | 动漫风格（赛璐璐着色，鲜艳色彩） |

### 扩展风格预设

| 参数 | 别名 | 描述 |
|------|------|------|
| `--ghibli` | - | 宫崎骏/吉卜力风格（水彩，奇幻） |
| `--pixel` | - | 像素艺术/复古游戏风格（16位，清晰像素） |
| `--minecraft` | `--voxel` | Minecraft/体素块风格（立方几何） |
| `--clay` | `--claymation` | 粘土动画风格（定格动画美学） |
| `--plush` | `--felt` | 毛绒玩具/毛毡面料风格（柔软，可爱） |
| `--paper` | `--papercraft` | 纸质剪贴/纸质马里奥风格（平面2.5D） |
| `--cyberpunk` | `--neon` | 赛博朋克/霓虹科幻风格 |
| `--fantasy` | `--medieval` | 高度幻想/中世纪RPG风格 |
| `--watercolor` | - | 传统水彩画风格 |
| `--oil` | `--oil-painting` | 古典油画风格 |
| `--3d-toon` | `--pixar` | 3D卡通/皮克斯-迪士尼风格 |
| `--comic` | `--marvel` | 美式漫画/超级英雄风格 |
| `--minimal` | `--flat` | 极简主义/扁平设计风格 |
| `--lowpoly` | - | 低多边形/几何3D风格 |

### 风格管理

| 参数 | 描述 |
|------|------|
| `--style` | 自定义风格描述或预设名称 |
| `--list-styles` | 列出所有可用风格预设并退出 |

## 本地模式设置

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--local-url` | `http://localhost:8199` | 本地Z-Image服务地址 |
| `--local-steps` | `9` | 本地模型推理步数 |

## 图像分析设置

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--analysis-api` | `auto`, `proxy`, `direct`, `local` | `auto` | 图像分析API选择 |
| `--strict` | 开关 | 否 | 严格复制模式：100%基于参考图像生成，配合`--from-image`使用 |

## 图像预处理

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--preprocess` | 开关 | 否 | 预处理输入图像：去除背景提高AI质量 |
| `--preprocess-model` | `birefnet-general`, `isnet-general-use`, `u2net` | `birefnet-general` | 背景去除模型 |

## 换装功能

| 参数 | 描述 | 示例 |
|------|------|------|
| `--wear`, `--outfit`, `--clothing` | 换装模式：让主体穿上指定衣服 | `--wear dress.png` |
| `--accessory`, `--add-item` | 配饰模式：给主体添加配饰 | `--accessory hat.png bag.png` |
| `--wear-strict` | 换装严格模式（默认开启） | - |
| `--wear-instruction` | 自定义换装指令 | `--wear-instruction "穿上红色连衣裙"` |
| `--wear-model`, `--hifi` | 换装模型选择 | `--wear-model pro` |
| `--wear-no-rembg` | 跳过衣服/配饰图片的智能切割预处理 | - |

## 3D转换设置

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--to-3d` | 开关 | 否 | 生成后自动转换为3D模型 |
| `--algo` | `hunyuan3d`, `hunyuan3d-2.1`, `hunyuan3d-omni`, `trellis`, `trellis2` | `hunyuan3d` | 3D算法选择 |
| `--quality` | `balanced`, `high`, `ultra` | `high` | 3D质量：balanced=快速，high=默认，ultra=最佳但慢 |
| `--geometry-only`, `--fast` | 开关 | 否 | 仅生成几何体，无纹理（更快） |
| `--pose` | 文件路径 | 无 | 姿势控制文件（仅hunyuan3d-omni支持） |

## 主体隔离参数

| 参数 | 描述 |
|------|------|
| `--subject-only`, `--isolate` | 仅处理主体（人物/角色），移除所有背景对象 |
| `--with-props` | 指定要保留的道具/对象 |

## 负面提示词控制

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--no-negative` | 开关 | 否 | 禁用负面提示词 |
| `--negative-categories` | `anatomy`, `quality`, `layout` | `anatomy quality layout` | 负面提示词类别 |

## 智能验证与自动补全

| 参数 | 描述 |
|------|------|
| `--auto-complete` | 自动验证生成的多视角图并补全缺失视角 |
| `--validate-only` | 仅验证生成的图片视角，不进行补全 |
| `--max-completion-retries` | 自动补全的最大重试次数（默认：3） |

## P0高优先级编辑功能

### 添加/移除元素

| 参数 | 描述 |
|------|------|
| `--mode-edit` | 激活编辑模式：添加/移除/修改角色元素 |
| `--edit-elements` | 编辑指令，格式：'add:xxx'或'remove:xxx'或'modify:xxx' |
| `--from-edited` | 要编辑的源图像路径 |

### 语义遮盖/细节修复

| 参数 | 选项 | 描述 |
|------|------|------|
| `--mode-refine` | 开关 | 激活优化模式：修复特定细节 |
| `--refine-details` | `face`, `hands`, `pose`, `eyes`, `custom` | 要优化的细节部位 |
| `--detail-issue` | 字符串 | 具体问题描述 |
| `--from-refine` | 文件路径 | 要优化的源图像路径 |

### 风格转换模式

| 参数 | 选项 | 描述 |
|------|------|------|
| `--mode-style` | 开关 | 激活风格转换模式 |
| `--style-preset` | `anime`, `cinematic`, `oil-painting`, `watercolor`, `comic`, `3d` | 风格预设 |
| `--custom-style` | 字符串 | 自定义风格描述 |
| `--from-style` | 文件路径 | 要进行风格转换的源图像路径 |
| `--preserve-details` | 开关 | 风格转换时是否保留原始细节（默认：是） |

### 高级合成功能

| 参数 | 选项 | 默认值 | 描述 |
|------|------|--------|------|
| `--mode-composite` | 开关 | - | 激活合成模式：组合多张图片创建新场景 |
| `--composite-images` | 图片路径列表 | - | 要合成的多张图片路径 |
| `--composite-instruction` | 字符串 | - | 合成指令 |
| `--composite-type` | `auto`, `clothing`, `accessory`, `general` | `auto` | 合成类型 |
| `--composite-output-name` | 字符串 | 自动生成 | 合成输出文件名 |
| `--composite-prompt-template` | 字符串 | - | 自定义合成提示词模板 |
| `--composite-no-smart-extract` | 开关 | - | 禁用智能提取 |

### 高保真细节保留

| 参数 | 描述 |
|------|------|
| `--mode-preserve` | 激活高保真编辑模式：在修改图像时保留关键细节 |
| `--preserve-image` | 主图片路径（包含要保留细节的图片） |
| `--preserve-element` | 元素图片路径（要添加到主图的元素） |
| `--preserve-detail-desc` | 要保留的关键细节描述 |
| `--preserve-instruction` | 修改指令 |
| `--preserve-output-name` | 输出文件名 |

## 其他功能

| 参数 | 描述 |
|------|------|
| `--export-prompt` | 导出提示词和参数而非调用API |
| `--model` | 模型名称（默认：models/nano-banana-pro-preview） |

## 使用示例

### 基础用法
```bash
# 基本角色生成
python scripts/generate_character.py "赛博朋克女战士"

# 从图片生成多视角
python scripts/generate_character.py --from-image photo.jpg --views 8

# 使用特定风格
python scripts/generate_character.py "机器人" --pixel --views 6

# 直接转3D
python scripts/generate_character.py "魔法师" --to-3d --algo hunyuan3d-2.1
```

### 高级用法
```bash
# 换装功能
python scripts/generate_character.py --from-image model.jpg --wear dress.png --accessory hat.png

# 迭代360度生成（高一致性）
python scripts/generate_character.py --from-image ref.jpg --iterative-360 8 --strict

# 智能补全缺失视角
python scripts/generate_character.py "战士" --views 8 --auto-complete

# 风格转换
python scripts/generate_character.py --mode-style --style-preset anime --from-style photo.jpg
```

## 环境变量

| 变量名 | 用途 |
|--------|------|
| `AIPROXY_TOKEN` | AiProxy模式认证令牌 |
| `GEMINI_API_KEY` | 直连Gemini API密钥 |
| `ZIMAGE_URL` | 本地Z-Image服务地址（默认：http://localhost:8199） |

## 注意事项

1. **模式选择**：推荐使用 `proxy` 模式，具有更好的稳定性
2. **视角一致性**：使用 `--iterative-360` 可获得更好的角色一致性
3. **高质量输出**：使用 `--pro` 和 `--resolution 4K` 可获得最佳质量
4. **性能优化**：使用 `--geometry-only` 可显著提升3D生成速度
5. **错误恢复**：使用 `--auto-complete` 可自动修复不完整的多视角生成

## 版本信息

本文档基于 Cortex3d 项目的 `generate_character.py` 脚本生成，涵盖了所有可用的命令参数和功能选项。