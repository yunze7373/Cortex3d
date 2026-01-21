# 迭代 360° 生成模式指南

## 📌 概述

新增 `--iterative-360 {4,6,8}` 模式实现 **Gemini API 360° 角色一致性生成**，严格遵循官方文档建议：

> **Character Consistency: 360 view** - You can generate 360-degree views of a character by iteratively prompting for different angles. For best results, include previously generated images in subsequent prompts to maintain consistency.
> 
> 来源: [Gemini API 文档](https://ai.google.dev/gemini-api/docs/image-generation)

### 支持视角数量

- **4-view**: FRONT (0°) → RIGHT (90°) → BACK (180°) → LEFT (270°)
- **6-view**: FRONT → FRONT_RIGHT (45°) → RIGHT (90°) → BACK (180°) → BACK_LEFT (225°) → LEFT (270°)
- **8-view**: 6-view + TOP + BOTTOM

**优势**：
- ✅ 每一步都基于前一步的输出，最大化 Gemini 对角色的理解一致性
- ✅ 符合 Gemini API 官方最佳实践
- ✅ 比一次性生成 4 视角更稳定
- ✅ 适合复杂姿势或多细节角色

---

## 📝 使用方法

### 基础命令

```bash
python scripts/generate_character.py \
  --from-image reference_images/character.png \
  --iterative-360 \
  --mode direct \
  --photorealistic
```

### 完整示例（带所有选项）

```bash
python scripts/generate_character.py \
  --from-image reference_images/character.png \
  --iterative-360 \
  --mode direct \
  --photorealistic \
  --resolution 2K \
  --strict \
  --output test_images \
  --preview
```

### 参数说明

| 参数 | 必需 | 说明 |
|------|------|------|
| `--from-image <path>` | ✅ 必需 | 参考图像路径。迭代 360° 模式强制需要 |
| `--iterative-360` | ✅ 必需 | 启用迭代 360° 模式 |
| `--mode direct` | 推荐 | 使用 Gemini 直连模式（需要 GEMINI_API_KEY） |
| `--photorealistic` | 可选 | 生成写实风格（推荐配合） |
| `--strict` | 可选 | 严格复制模式（100% 基于参考图） |
| `--resolution` | 可选 | 分辨率: 1K/2K(默认)/4K |
| `--preview` | 可选 | 生成完成后自动打开预览 |

---

## 🔄 执行流程详解

### 第 1/4 步：FRONT 视图 (0°)
```
输入: 原始参考图 + 角色描述 + 初始提示词
输出: FRONT_0°.png
```

### 第 2/4 步：RIGHT 视图 (90°)
```
输入: FRONT_0°.png (作为新参考) + 修改后的提示词
      ⚠️ 额外指令: "Keep the subject's pose, expression, and positioning 
                    IDENTICAL to the previous view. Only the camera 
                    angle changes to 90°."
输出: RIGHT_90°.png
```

### 第 3/4 步：BACK 视图 (180°)
```
输入: RIGHT_90°.png (作为新参考) + 修改后的提示词
      ⚠️ 相同的一致性强调
输出: BACK_180°.png
```

### 第 4/4 步：LEFT 视图 (270°)
```
输入: BACK_180°.png (作为新参考) + 修改后的提示词
      ⚠️ 相同的一致性强调
输出: LEFT_270°.png
```

### 最终：合成
```
将 4 张图合成为: iterative_360_composite.png (水平排列)
```

---

## 🛠️ 与 Gemini API 最佳实践对应

| 文档建议 | 本实现 |
|---------|--------|
| "Include previously generated images in subsequent prompts" | ✅ 每一步都用前一张作为参考 |
| "Provide Context and Intent" | ✅ 每步提示词明确说明意图（保持姿势，仅改角度） |
| "Use Semantic Negative Prompts" | ✅ 已集成 QUALITY REQUIREMENTS |
| "Iterate and Refine" | ✅ 4 步迭代过程本质上就是细化 |
| "Control the Camera" | ✅ 每步明确相机角度（0/90/180/270°） |

---

## 📊 预期结果

### 成功指标
- ✅ 所有 4 视角生成完毕
- ✅ 角色头部方向在所有视角中一致
- ✅ 身体姿势锁定，不会因视角改变
- ✅ 肢体位置（腿交叉、手臂位置等）在所有视角保持一致

### 输出文件结构
```
test_images/
├── iterative_360_composite.png     # 最终 4 视角合成图
├── FRONT_0°.png                    # 中间产物
├── RIGHT_90°.png
├── BACK_180°.png
└── LEFT_270°.png
```

---

## ⚠️ 注意事项

### 1. 必须使用 `--from-image`
```bash
# ❌ 错误
python scripts/generate_character.py "角色描述" --iterative-360

# ✅ 正确
python scripts/generate_character.py --from-image ref.png --iterative-360
```

### 2. 仅适配 Gemini 直连模式
```bash
# ❌ 代理模式不支持（目前）
python scripts/generate_character.py --from-image ref.png --iterative-360 --mode proxy

# ✅ 必须用直连
python scripts/generate_character.py --from-image ref.png --iterative-360 --mode direct
```

### 3. 生成时间 ~4 倍
- 标准模式: ~1-2 分钟
- 迭代 360°: ~4-8 分钟（每步 1-2 分钟 × 4 步）

### 4. API 配额消耗
每次迭代 360° 生成相当于调用 Gemini API 4 次（FRONT + RIGHT + BACK + LEFT）

---

## 📈 性能对比

### 一次性 4 视角 vs 迭代 360°

| 方面 | 一次性生成 | 迭代 360° |
|------|----------|---------|
| 生成时间 | 快 (1-2 min) | 慢 (4-8 min) |
| 角色一致性 | 中等 | 优秀 ⭐ |
| API 调用次数 | 1 次 | 4 次 |
| 复杂姿势支持 | 低 | 高 ⭐ |
| 官方推荐 | 否 | 是 ✅ |

---

## 🎬 使用场景

### ✅ 推荐使用
- 复杂角色（多个细节、奇特姿势）
- 高保真需求
- 需要完美 360° 一致性
- 商业/专业用途

### ⏸️ 可不使用
- 快速原型测试
- 简单角色生成
- API 配额有限
- 只需要少数视角

---

## 🔧 故障排除

### Q: 生成失败，提示"ImageNotFound"
**A**: 检查参考图路径是否正确
```bash
python scripts/generate_character.py \
  --from-image reference_images/47.png \
  --iterative-360
```

### Q: 某个中间步骤失败
**A**: 查看完整日志，可能是 API 限流。稍后重试。

### Q: 4 个视角的角色看起来不一样
**A**: 属于正常现象（不同角度确实会有差异）。如果是 **姿势变化**（头转向、腿交叉反向），说明 Gemini 仍有优化空间，可尝试：
- 更详细的参考图
- 使用 `--strict` 模式
- 提供更清晰的文字描述

---

## 📚 相关资源

- [Gemini API 图像生成文档](https://ai.google.dev/gemini-api/docs/image-generation)
- [Cortex3d 主文档](README.md)
- [多视角生成详细指南](docs/MULTIVIEW_GUIDE.md)

---

## 💡 技术细节

### 动态提示词注入
每次迭代时，系统会自动在提示词中注入：
```
⚠️ **CRITICAL for Consistency**: Keep the subject's pose, expression, 
and positioning IDENTICAL to the previous view. Only the camera 
angle changes to {new_angle}°.
```

这确保 Gemini 明白：**只改变相机视角，姿势必须锁定**。

### 图像合成算法
使用 PIL 将 4 张图水平拼接：
- 保持原始分辨率
- 无损压缩
- 输出格式: PNG

---

**最后更新**: 2026-01-22  
**版本**: 1.0 (First Release)
