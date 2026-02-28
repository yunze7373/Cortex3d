---
title: "P1 风格转换快速开始指南"
version: "1.0"
date: "2024-12-26"
---

# 🎨 P1 风格转换 - 快速开始

## 快速命令

### 1️⃣ 预设风格转换

```bash
# 动漫风格
python scripts/generate_character.py --mode-style --style-preset anime --from-style test_images/character_20251226_013442_front.png

# 电影风格
python scripts/generate_character.py --mode-style --style-preset cinematic --from-style test_images/character_20251226_013442_front.png

# 油画风格
python scripts/generate_character.py --mode-style --style-preset oil-painting --from-style test_images/character_20251226_013442_front.png

# 水彩风格
python scripts/generate_character.py --mode-style --style-preset watercolor --from-style test_images/character_20251226_013442_front.png

# 漫画风格
python scripts/generate_character.py --mode-style --style-preset comic --from-style test_images/character_20251226_013442_front.png

# 3D/CGI 风格
python scripts/generate_character.py --mode-style --style-preset 3d --from-style test_images/character_20251226_013442_front.png
```

### 2️⃣ 自定义风格转换

```bash
# 自定义风格描述
python scripts/generate_character.py --mode-style --custom-style "impressionist Renaissance painting" --from-style test_images/character_20251226_013442_front.png

# 另一个例子
python scripts/generate_character.py --mode-style --custom-style "Soviet propaganda poster style with bold colors" --from-style test_images/character_20251226_013442_front.png
```

### 3️⃣ 高级选项

```bash
# 不保留原始细节 (更激进的风格转换)
python scripts/generate_character.py --mode-style --style-preset anime --from-style test_images/character.png --preserve-details False

# 指定输出目录
python scripts/generate_character.py --mode-style --style-preset cinematic --from-style test_images/character.png --output styled_output/

# 完整示例
python scripts/generate_character.py \
    --mode-style \
    --style-preset oil-painting \
    --from-style test_images/character_20251226_013442_front.png \
    --character "anime character with blue hair and armor" \
    --preserve-details \
    --output test_images/ \
    --model gemini-3.1-flash-image-preview
```

## 参数参考

| 参数 | 值 | 说明 |
|------|-----|------|
| `--mode-style` | 标志 | 激活风格转换模式 |
| `--style-preset` | 见下 | 预设风格 (必需) |
| `--custom-style` | 字符串 | 自定义风格 (覆盖预设) |
| `--from-style` | 路径 | 源图像路径 **(必需)** |
| `--preserve-details` | 标志 | 保留原始细节 (默认: 是) |
| `--character` | 字符串 | 角色描述 (可选) |
| `--output` | 路径 | 输出目录 (默认: test_images/) |
| `--model` | 字符串 | 使用的模型 (默认: gemini-3.1-flash-image-preview) |
| `--token` | 字符串 | Gemini API Key (默认: 环境变量) |

## 预设风格详解

### 1. `anime` - 动漫风格
- 风格特征：夸张的特征、明亮的颜色、表现力强的眼睛
- 最佳用途：将真实图像转换为动漫风格
- 示例输出：带有典型日本动漫元素的角色

### 2. `cinematic` - 电影风格
- 风格特征：电影感、专业光照、完美构图
- 最佳用途：提升图像质感和专业度
- 示例输出：好莱坞级别的渲染效果

### 3. `oil-painting` - 油画风格
- 风格特征：可见笔触、丰富色彩、古典艺术
- 最佳用途：创建艺术感强的版本
- 示例输出：经典油画般的图像

### 4. `watercolor` - 水彩风格
- 风格特征：柔和边缘、流动色彩、轻盈感
- 最佳用途：创建温和、艺术化的效果
- 示例输出：水彩画般的半透明效果

### 5. `comic` - 漫画风格
- 风格特征：粗黑轮廓、有限调色板、简化图形
- 最佳用途：创建漫画书风格的图像
- 示例输出：带有黑线条和纯色的漫画艺术

### 6. `3d` - 3D/CGI 风格
- 风格特征：3D 渲染、现代数字美学、光滑表面
- 最佳用途：创建现代 3D 游戏或视觉效果风格
- 示例输出：专业 CG 渲染质感

## 输出文件

**格式:** `styled_{风格}_{时间戳}.png`

**示例:**
- `styled_anime_20241226_120530.png`
- `styled_cinematic_20241226_120545.png`
- `styled_custom_20241226_120600.png`

## 常见问题

### Q: 怎样设置 API Key?
**A:** 使用环境变量:
```powershell
# PowerShell
$env:GEMINI_API_KEY = 'your-api-key-here'

# CMD
set GEMINI_API_KEY=your-api-key-here

# Linux/Mac
export GEMINI_API_KEY='your-api-key-here'
```

### Q: 可以使用本地图像吗?
**A:** 是的! 只需提供完整路径:
```bash
python scripts/generate_character.py --mode-style --style-preset anime --from-style /path/to/your/image.png
```

### Q: 如何保存为不同格式?
**A:** 目前输出始终为 PNG 格式，带有时间戳。

### Q: 风格转换需要多长时间?
**A:** 取决于 Gemini API 的响应时间，通常 10-30 秒。

### Q: 可以使用自己的模型吗?
**A:** 可以，使用 `--model` 参数指定:
```bash
python scripts/generate_character.py --mode-style --style-preset anime --from-style image.png --model models/gemini-2-5-pro-vision
```

## 测试风格转换功能

```bash
# 运行测试脚本
python test_style_transfer.py
```

测试脚本会:
1. 检查 API Key
2. 加载测试图像
3. 尝试 3 种风格转换
4. 验证输出文件
5. 显示详细结果

## 工作流示例

### 场景 1: 将角色转换为动漫风格

```bash
# 步骤 1: 生成原始角色
python scripts/generate_character.py --prompt "a warrior in armor"

# 步骤 2: 转换为动漫风格
python scripts/generate_character.py --mode-style --style-preset anime --from-style test_images/character_20251226_013442_front.png
```

### 场景 2: 创建多风格版本

```bash
# 创建风格版本集合
for $style in @("anime", "cinematic", "oil-painting", "watercolor", "comic", "3d") {
    python scripts/generate_character.py --mode-style --style-preset $style --from-style test_images/character_20251226_013442_front.png
}
```

## 故障排除

### 错误: "无法加载源图像"
- 检查文件路径是否正确
- 确保文件存在
- 尝试使用完整路径而不是相对路径

### 错误: "API 未返回图像数据"
- 检查 API Key 是否有效
- 检查网络连接
- 尝试使用不同的风格

### 错误: "模型未找到"
- 检查模型名称是否正确
- 使用默认模型: `gemini-3.1-flash-image-preview` (Nano Banana 2)

## 下一步

✅ **已完成:** P1 Phase 1 - 风格转换  
⏳ **即将推出:** P1 Phase 2 - 图像合成  
⏳ **即将推出:** P1 Phase 3 - 批量处理  
⏳ **即将推出:** P1 Phase 4 - 历史跟踪  

---

**需要帮助?** 查看完整文档: [P1_STYLE_TRANSFER_IMPLEMENTATION.md](P1_STYLE_TRANSFER_IMPLEMENTATION.md)
