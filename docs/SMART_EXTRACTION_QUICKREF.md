# 智能换装功能 - 快速参考

## ✨ 新功能：一条命令搞定所有换装场景

### 你的命令现在已支持智能处理！

```bash
python scripts/generate_character.py \
    --mode-composite \
    --composite-images 3.png b92b7d77-bda2-4374-bd8c-cedf9cd55195.jpg \
    --composite-instruction "让这个人穿上这件衣服"
```

---

## 🎯 新增功能详解

### 自动智能检测 🧠

系统会自动分析 `b92b7d77-bda2-4374-bd8c-cedf9cd55195.jpg`：

| 检测结果 | 自动处理 |
|---------|---------|
| 仅衣服 + 无背景 | ✅ 直接使用 |
| 仅衣服 + 有背景 | ✅ 去除背景 → 使用 |
| 穿衣服的人 + 有背景 | ✅ 去背景 → AI提取衣服 → 使用 |

**你不需要做任何额外操作！** 🎉

---

## 📊 处理流程示例

### 场景：衣服图是穿着衣服的人

```
输入: 3.png (主图) + b92b7d77...jpg (穿着衣服的人)
  ↓
AI检测: "这是一个穿着衣服的人"
  ↓
步骤1: 去除背景
  ↓
步骤2: AI提取衣服 (从人身上剥离衣服)
  ↓
步骤3: 将衣服穿到 3.png 的人物身上
  ↓
输出: 3.png的人穿上了那件衣服 ✨
```

---

## 🔧 额外选项

### 如果你想跳过智能处理（直接用原图）

```bash
python scripts/generate_character.py \
    --mode-composite \
    --composite-images 3.png dress.jpg \
    --composite-instruction "让这个人穿上这件衣服" \
    --composite-no-smart-extract
```

### 使用高保真模型（更好的质量）

```bash
python scripts/generate_character.py \
    --mode-composite \
    --composite-images 3.png dress.jpg \
    --composite-instruction "让这个人穿上这件衣服" \
    --wear-model pro
```

---

## 💰 成本估算

| 场景 | AI调用次数 | 大约成本 (flash) |
|-----|-----------|----------------|
| 纯衣服(无背景) | 1次 | ~$0.001 |
| 纯衣服(有背景) | 1次 | ~$0.002 |
| 穿衣服的人 | 3次 | ~$0.006 |

使用 `--wear-model pro`：约贵10倍，但质量更好

---

## ⏱️ 处理时间

- 纯衣服：2-5秒
- 穿衣服的人：10-15秒

---

## 🎨 支持的其他换装方式

### 方式1: --wear (简便)
```bash
python scripts/generate_character.py \
    --from-image 3.png \
    --wear dress.jpg "换上这件红色裙子"
```

### 方式2: --mode-composite (你在用的)
```bash
python scripts/generate_character.py \
    --mode-composite \
    --composite-images 3.png dress.jpg \
    --composite-instruction "让这个人穿上这件衣服"
```

### 方式3: --accessory (添加配饰)
```bash
python scripts/generate_character.py \
    --from-image 3.png \
    --accessory hat.png bag.png
```

### 方式4: --mode-edit (精细编辑)
```bash
python scripts/generate_character.py \
    --mode-edit \
    --from-edited 3.png \
    --edit-elements "modify:穿上晚礼服"
```

---

## 🆚 对比：新旧行为

### 旧行为（无智能提取）
```bash
# 如果 dress.jpg 是穿着衣服的人
❌ 直接使用原图 → 可能效果不好
```

### 新行为（默认智能提取）
```bash
# 如果 dress.jpg 是穿着衣服的人
✅ AI分析 → 去背景 → 提取衣服 → 完美合成
```

---

## 📝 关键参数总结

| 参数 | 作用 | 默认 |
|-----|------|-----|
| `--mode-composite` | 激活合成模式 | - |
| `--composite-images` | 图片列表 | - |
| `--composite-instruction` | 合成指令 | - |
| `--composite-smart-extract` | 智能提取 | ✅ 开启 |
| `--composite-no-smart-extract` | 禁用智能提取 | - |
| `--wear-model pro` | 高保真模型 | flash |

---

## 🎯 使用建议

✅ **推荐**：
- 衣服图清晰
- 简单背景
- 光照均匀

⚠️ **注意**：
- 复杂背景可能需要更多时间
- 衣服被遮挡可能影响提取质量
- 极端姿势可能需要手动调整

---

## 🔗 更多信息

- 详细文档：[SMART_CLOTHING_EXTRACTION.md](SMART_CLOTHING_EXTRACTION.md)
- 换装速查：[GEMINI_IMAGE_EDITING_CHEATSHEET.md](GEMINI_IMAGE_EDITING_CHEATSHEET.md)

---

**核心优势**：🚀 一条命令，所有场景自动处理！

**版本**: v1.0 | **日期**: 2026-01-24
