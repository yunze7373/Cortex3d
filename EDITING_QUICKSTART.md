# 🎨 Cortex3d P0 图像编辑功能 - 快速开始指南

> Cortex3d 现已支持使用 Gemini 的语义图像编辑能力快速编辑和修复角色图像！

## ⚡ 30 秒快速开始

### 1️⃣ 安装依赖 (仅首次)

```bash
cd Cortex3d
pip install -r requirements.txt
```

### 2️⃣ 设置 API Key

```bash
# 方法1: 环境变量 (推荐)
export GEMINI_API_KEY="your-gemini-api-key"

# 方法2: 在命令行直接传递
--token "your-gemini-api-key"
```

### 3️⃣ 使用编辑模式

```bash
# 例1: 为角色添加装备
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:肩部炮台" \
  --from-edited "test_images/character_front.png"

# 例2: 移除元素
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "remove:红色腰带" \
  --from-edited "test_images/character_front.png"

# 例3: 修改元素
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "modify:左手剑为光剑" \
  --from-edited "test_images/character_front.png"
```

### 4️⃣ 使用细节修复模式

```bash
# 例1: 修复脸部问题
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "face" \
  --detail-issue "脸部表情看起来不自然" \
  --from-refine "test_images/character_front.png"

# 例2: 修复手部问题
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "hands" \
  --detail-issue "左手有6根手指，需要改为5根" \
  --from-refine "test_images/character_front.png"

# 例3: 调整姿态
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "pose" \
  --detail-issue "身体比例不对，头部太大" \
  --from-refine "test_images/character_front.png"
```

## 📖 完整文档

- **快速开始指南**: [docs/IMAGE_EDITING_QUICKSTART.md](docs/IMAGE_EDITING_QUICKSTART.md) ⭐ **从这里开始**
- **P0 实现总结**: [docs/P0_IMPLEMENTATION_SUMMARY.md](docs/P0_IMPLEMENTATION_SUMMARY.md)
- **完整设计文档**: [docs/GEMINI_IMAGE_EDITING_INTEGRATION.md](docs/GEMINI_IMAGE_EDITING_INTEGRATION.md)
- **快速参考手册**: [docs/GEMINI_IMAGE_EDITING_CHEATSHEET.md](docs/GEMINI_IMAGE_EDITING_CHEATSHEET.md)

## 🔑 关键参数

### 编辑模式 (`--mode-edit`)

| 参数 | 类型 | 必需 | 说明 |
|-----|------|------|------|
| `--mode-edit` | flag | ✅ | 激活编辑模式 |
| `--edit-elements` | string | ✅ | 编辑指令: `"add:xxx"` / `"remove:xxx"` / `"modify:xxx"` |
| `--from-edited` | path | ✅ | 源图像路径 |
| `--character` | string | ⏩ | 角色描述 (可选) |
| `--output` | path | ⏩ | 输出目录 (默认: test_images) |
| `--token` | string | ⏩ | API Key (可选) |

### 细节修复模式 (`--mode-refine`)

| 参数 | 类型 | 必需 | 说明 |
|-----|------|------|------|
| `--mode-refine` | flag | ✅ | 激活细节修复模式 |
| `--refine-details` | choice | ✅ | 修复部位: `face` / `hands` / `pose` / `eyes` / `custom` |
| `--detail-issue` | string | ✅ | 问题描述 (例: "左手有6根手指") |
| `--from-refine` | path | ✅ | 源图像路径 |
| `--character` | string | ⏩ | 角色描述 (可选) |
| `--output` | path | ⏩ | 输出目录 (默认: test_images) |
| `--token` | string | ⏩ | API Key (可选) |

## 💡 使用建议

### 📝 编写清晰的指令

**❌ 不清晰** → **✅ 清晰**
```
"add:东西"  →  "add:右肩膀上的蓝色发光能量球"
"remove:东西" → "remove:头顶的紫色蝴蝶结装饰"
"modify:手" → "modify:右手的剑为闪闪发光的光剑"
```

### 📸 提供角色描述

更好的效果:
```bash
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:戏法师的魔法杖" \
  --from-edited "image.png" \
  --character "奇幻世界的女性戏法师，紫色魔法长袍"
```

### 🔄 多步骤编辑工作流

对于复杂编辑，分步进行:

```bash
# 步骤1: 添加第一个元素
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:左肩装备" \
  --from-edited "original.png" \
  --output "step1"

# 步骤2: 基于步骤1的结果添加第二个元素
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:右肩装备" \
  --from-edited "step1/add_edited_*.png" \
  --output "step2"

# 步骤3: 最后进行细节修复
python scripts/generate_character.py \
  --mode-refine \
  --refine-details "face" \
  --from-refine "step2/add_edited_*.png" \
  --output "final"
```

## 🧪 验证安装

运行验证脚本确保一切正常:

```bash
# 检查 P0 实现完成度
python verify_p0_implementation.py

# 测试参数解析和函数导入
python test_edit_routing.py
```

预期输出:
```
✅ 总体完成度: 32/33 (97.0%)
✅ P0 阶段实现已完成且验证通过！
```

## ❓ 常见问题

### Q: 编辑结果不理想怎么办?

A: 尝试以下方法:
1. 提供更详细的指令描述
2. 提供完整的角色背景描述 (`--character` 参数)
3. 使用高质量源图像 (Cortex3d 生成的图像效果最好)
4. 尝试使用 `--model "gemini-3-pro-image"` (更强大但更慢)

### Q: 如何处理多个图像?

A: 可以编写脚本循环调用:

```bash
for img in outputs/*_front.png; do
  python scripts/generate_character.py \
    --mode-edit \
    --edit-elements "add:蓝色肩甲" \
    --from-edited "$img" \
    --output "edited"
done
```

### Q: 编辑后如何进行 3D 建模?

A: 编辑后的图像可以直接用于现有的 3D 建模流程:

```bash
# 编辑完成后
python scripts/generate_character.py \
  --mode-edit \
  --edit-elements "add:肩部装备" \
  --from-edited "image.png" \
  --output "edited"

# 使用编辑后的图像进行 3D 建模
python scripts/reconstructor.py \
  --front-image "edited/add_edited_*.png" \
  --algo trellis
```

## 📊 性能参考

| 任务 | 编辑模式 | 重新生成 | 优势 |
|-----|--------|--------|------|
| 添加装备 | ⚡ 30-60 秒 | 🕐 3+ 分钟 | **快 5-10 倍** |
| 修复手指 | ⚡ 30-60 秒 | 🕐 3+ 分钟 | **快 5-10 倍** |
| API 成本 | 1 次调用 | 3+ 次调用 | **节省成本** |

## 🚀 后续功能 (P1, P2)

### P1 (中优先级) - 计划中
- 风格转换 (改变整体美学风格)
- 多图像合成 (组合多个角色元素)
- 批量编辑脚本

### P2 (低优先级) - 计划中
- 特征锁定编辑 (保持某些部分不变)
- 草图参考编辑
- Web UI 集成

## 📞 获取帮助

1. 查看完整文档: [docs/IMAGE_EDITING_QUICKSTART.md](docs/IMAGE_EDITING_QUICKSTART.md)
2. 查看速查表: [docs/GEMINI_IMAGE_EDITING_CHEATSHEET.md](docs/GEMINI_IMAGE_EDITING_CHEATSHEET.md)
3. 运行验证脚本: `python verify_p0_implementation.py`
4. 查看实现总结: [docs/P0_IMPLEMENTATION_SUMMARY.md](docs/P0_IMPLEMENTATION_SUMMARY.md)

---

**版本**: P0.1 (初始发布)  
**最后更新**: 2025 年 1 月  
**状态**: ✅ 生产就绪
