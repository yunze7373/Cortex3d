---
title: "P1 Phase 1 风格转换 - 快速参考卡"
format: "cheat-sheet"
date: "2024-12-26"
---

# 🎨 P1 Phase 1 风格转换 - 快速参考卡

## ⚡ 即时使用

### 最简单的命令
```bash
# 动漫风格
python scripts/generate_character.py --mode-style --style-preset anime --from-style test_images/character_20251226_013442_front.png
```

### 6 种风格速查
```bash
anime            # 日本动漫风格
cinematic        # 电影风格
oil-painting     # 油画风格
watercolor       # 水彩风格
comic            # 漫画风格
3d               # 3D/CGI 风格
```

---

## 🎯 参数速查表

| 参数 | 必需 | 值 | 说明 |
|------|-----|-----|------|
| `--mode-style` | ✅ | 标志 | 激活风格转换 |
| `--style-preset` | ✅ | 6选1 | 风格选择 |
| `--from-style` | ✅ | 路径 | 源图像 |
| `--custom-style` | ❌ | 字符串 | 自定义风格 |
| `--preserve-details` | ❌ | 标志 | 保留细节 |
| `--character` | ❌ | 字符串 | 角色描述 |
| `--output` | ❌ | 路径 | 输出目录 |

---

## 📖 文档速览

| 需求 | 文档 | 位置 |
|------|------|------|
| 立即开始 | 快速开始 | `docs/P1_STYLE_TRANSFER_QUICKSTART.md` |
| 技术细节 | 实现文档 | `docs/P1_STYLE_TRANSFER_IMPLEMENTATION.md` |
| 进度追踪 | 状态报告 | `docs/P1_IMPLEMENTATION_STATUS.md` |
| 文档导航 | 导航中心 | `P1_NAVIGATION_CENTER.md` |
| 总体计划 | P1 计划 | `docs/P1_UPGRADE_PLAN.md` |

---

## 💡 常用命令模板

```bash
# 模板 1: 预设风格
python scripts/generate_character.py --mode-style \
  --style-preset [PRESET] \
  --from-style [IMAGE_PATH]

# 模板 2: 自定义风格
python scripts/generate_character.py --mode-style \
  --custom-style "[STYLE_DESCRIPTION]" \
  --from-style [IMAGE_PATH]

# 模板 3: 完整命令
python scripts/generate_character.py --mode-style \
  --style-preset [PRESET] \
  --from-style [IMAGE_PATH] \
  --character "[CHARACTER_DESC]" \
  --output [OUTPUT_DIR] \
  --preserve-details
```

---

## 🔧 关键文件

```
scripts/gemini_generator.py
  └─ style_transfer_character() [行 863-992]

scripts/generate_character.py
  ├─ --mode-style 参数 [行 477-512]
  └─ 路由逻辑 [行 648-717]

scripts/image_editor_utils.py
  └─ compose_style_transfer_prompt() [行 281-305]
```

---

## 📤 输出格式

**文件名**: `styled_{preset}_{YYYYMMDD_HHMMSS}.png`  
**示例**: `styled_anime_20241226_120530.png`  
**位置**: `test_images/` 或指定的 `--output` 目录

---

## ✅ 验证步骤

```bash
# 1. 检查 API Key
$env:GEMINI_API_KEY = 'your-key'

# 2. 运行测试
python test_p1_style_transfer.py

# 3. 执行风格转换
python scripts/generate_character.py --mode-style ...

# 4. 检查输出
ls test_images/styled*.png
```

---

## 🎨 风格预设详解

| 预设 | 特征 | 最佳用途 |
|------|------|--------|
| **anime** | 明亮、夸张、表现力强 | 日本风格转换 |
| **cinematic** | 专业、真实、光照完美 | 质感提升 |
| **oil-painting** | 古典、笔触可见、丰富色彩 | 艺术化处理 |
| **watercolor** | 柔和、流动、轻盈 | 温和效果 |
| **comic** | 轮廓粗黑、颜色纯正 | 漫画风格 |
| **3d** | 现代、光滑、数字感 | 现代渲染 |

---

## 🚀 下一步

```
Phase 1: 风格转换             ✅ 完成
  ↓
Phase 2: 图像合成             ⏳ 即将推出
Phase 3: 批量处理             ⏳ 计划中
Phase 4: 历史跟踪             ⏳ 计划中
```

---

## 🆘 快速故障排除

| 问题 | 解决方案 |
|------|---------|
| API Key 错误 | 设置 `$env:GEMINI_API_KEY` |
| 找不到图像 | 检查路径是否正确 |
| 导入失败 | 检查 scripts 目录是否存在 |
| 没有输出 | 检查 API 配额和网络连接 |

---

**参考**: [完整文档](P1_NAVIGATION_CENTER.md)  
**状态**: ✅ P1 Phase 1 完成  
**日期**: 2024-12-26
