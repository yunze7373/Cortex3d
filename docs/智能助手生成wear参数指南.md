# 🎯 智能助手生成 --wear 参数指南

## 📝 如何向智能助手表达生成 --wear 参数

### ✅ 推荐的表达方式

要让智能助手生成 `--wear` 参数，您可以使用以下关键词：

```text
"快速换装"
"简单换装"  
"wear模式"
"轻量换装"
"wear功能"
```

### 🔄 完整对话流程

**第1步：表达换装需求**
```text
用户: "快速换装，给角色换件衣服"
```

**第2步：补充风格信息**  
```text
助手: [询问风格和质量偏好]
用户: "写实风格，快速模式"
```

**第3步：获得智能推荐**
```bash
智能助手生成:
python scripts/generate_character.py \
  --wear clothing_item.png \
  --wear-model flash \
  --res 2K \
  --from-image your_image.jpg \
  --preview
```

### 📋 两种换装模式对比

| 表达方式 | 生成参数 | 适用场景 |
|----------|----------|----------|
| **快速换装、简单换装** | `--wear` | 单一服装快速替换 |
| **图像合成、复杂换装** | `--mode-composite` | 多元素复杂合成 |

### ⚠️ 避免的表达（会生成 --mode-composite）

以下表达会让助手生成复杂的合成参数而不是简单的 `--wear`：
- "图像合成"
- "复杂换装"
- "composite模式" 
- "多图合成"
- "元素组合"

### 🎯 实际使用示例

**您想要的效果：**
```bash
python scripts/generate_character.py \
  --from-image model.jpg \
  --wear dress.png
```

**智能助手表达：**
```text
"快速换装，给角色换衣服，写实风格，快速模式"
```

**智能助手生成：**
```bash
python scripts/generate_character.py \
  --wear clothing_item.png \
  --wear-model flash \
  --res 2K \
  --from-image your_image.jpg \
  --preview
```

然后您只需要：
1. 将 `clothing_item.png` 替换为实际的服装图片路径
2. 将 `your_image.jpg` 替换为实际的人物图片路径

### 💡 关键点

- 使用"快速"、"简单"、"轻量"等关键词
- 明确提到"wear"会提高识别准确率
- 避免"合成"、"复杂"等词汇，除非您确实需要 `--mode-composite`