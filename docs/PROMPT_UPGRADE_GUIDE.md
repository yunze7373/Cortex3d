# 四面图提示词改进实施指南

## 📋 改动清单

### 已完成的改动 ✅

#### 1. 更新了 `scripts/config.py` 中的三个关键模板

- **_LEGACY_MULTIVIEW_TEMPLATE** (标准多视图生成)
- **_LEGACY_IMAGE_REF_TEMPLATE** (基于参考图像的生成)
- **_LEGACY_STRICT_COPY_TEMPLATE** (严格复制模式)

所有三个模板现在都采用：
- ✅ "STATIC OBJECT" 认知框架
- ✅ 显式的相机定义 (固定半径和高度)
- ✅ 明确的空间锁定指令
- ✅ 针对常见模型错误的禁止项
- ✅ 纯中性背景要求
- ✅ 配置参数 (4K, 3:2, deterministic)

#### 2. 创建了新的提示词样本文件

- `2d图生成提示词/英文4视角提示词sample_v3.0.md`
- `2d图生成提示词/中文4视角提示词sample_v3.0.md`

这两个文件包含：
- 完整的改进版提示词
- 三个高级变体 (重建导向、摄影风格、严格几何)
- 详细的关键改进说明
- 使用和测试建议

#### 3. 生成了详细的分析文档

- `docs/PROMPT_IMPROVEMENT_ANALYSIS.md`

包含：
- 完整的对比分析表
- 6个关键改进点的深度解释
- 3个实施方案
- 迁移建议
- 验证清单
- 预期效果评估

---

## 🚀 立即可用的用法

### 情景1: 直接使用更新后的脚本

```bash
# 使用已更新的提示词生成四面图
python scripts/gemini_generator.py \
  --description "坚毅的末日幸存者，穿着破烂的西装，手持手枪" \
  --token YOUR_API_KEY \
  --auto-cut
```

这会自动使用新的 `_LEGACY_MULTIVIEW_TEMPLATE` 提示词。

### 情景2: 使用新版本提示词

如果想尝试专门的重建导向版本：

```
[使用 docs/PROMPT_IMPROVEMENT_ANALYSIS.md 中"方案二"的代码]
[或直接复制 2d图生成提示词/英文4视角提示词sample_v3.0.md 的内容到 Gemini]
```

### 情景3: 对比测试

```bash
# 生成一个字符两次，对比效果
python scripts/gemini_generator.py \
  --description "Your character description" \
  --output outputs/v3_test_1

# 等待一段时间，再生成一次
python scripts/gemini_generator.py \
  --description "Your character description" \
  --output outputs/v3_test_2

# 使用 image_processor.py 处理两个输出进行对比
```

---

## 📊 预期效果对标

使用新提示词后应该观察到的改进：

### 必然改进 (高信心)
- [ ] 四个视角中角色总体尺寸更一致
- [ ] 衣服褶皱位置在各视角间保持稳定
- [ ] 背景更加一致和中性
- [ ] 整体几何正确性提升

### 可能改进 (中等信心)
- [ ] 生成成功率提升 (避免重大错误)
- [ ] 首次生成就符合要求的概率增加
- [ ] 角色姿态在各视角中更加稳定

### 监测指标 (需要测试)
- [ ] 生成速度变化
- [ ] API 费用变化 (分辨率调整)
- [ ] 不同模型在新提示词下的表现差异

---

## 🔄 后续改进路线

### 第一阶段 (这周)
- ✅ 更新基础模板
- ✅ 创建新版本提示词文件
- ⏳ **待做**: 测试新提示词的实际效果
- ⏳ **待做**: 收集用户反馈

### 第二阶段 (下周)
- ⏳ 根据测试结果微调提示词
- ⏳ 添加 `--prompt-version` 参数以支持版本选择
- ⏳ 为不同场景创建专门的提示词预设

### 第三阶段 (后续优化)
- ⏳ 建立 A/B 测试框架
- ⏳ 为不同模型创建优化版本
- ⏳ 添加提示词效果评分系统

---

## 🧪 测试方案

### 快速验证 (5分钟)

使用同一角色描述生成一次，检查：

```
检查清单:
[ ] 四个视角的角色尺寸是否基本一致？(视觉检查)
[ ] 衣服褶皱是否在四个视角中位置相近？
[ ] 背景是否是纯灰/白色，没有场景细节？
[ ] 有无文字标签或标记？
```

### 深度对比 (30分钟)

```bash
# 生成两组测试
CHAR_DESC="A confident warrior in steel armor, holding a greatsword, facing forward with determined expression"

# 旧版本提示词的结果（如果你还保留了备份）
# 新版本提示词的结果（使用当前的 config.py）

# 对比维度：
# 1. 尺寸一致性: 用工具测量四个视角中角色的像素高度
# 2. 姿态稳定性: 比较四个视角中肩膀、头部的相对位置
# 3. 布料细节: 检查衣服褶皱是否在几何上合理
# 4. 背景: 计算背景色的标准差（应该很小）
```

### 自动化测试 (待实现)

```python
# 在 test_pipeline.py 中添加
def evaluate_multiview_consistency(image_paths):
    """评估四面图的一致性"""
    # 1. 检测角色尺寸
    # 2. 检测颜色一致性
    # 3. 检测背景均匀性
    # 4. 返回一致性分数
    pass
```

---

## 📝 使用新提示词的示例

### 示例1: 直接在 Gemini 中使用

```
[复制 2d图生成提示词/英文4视角提示词sample_v3.0.md 的内容]

[然后在 CHARACTER DESCRIPTION 部分填入你的角色描述，例如:]

A fierce pirate captain in a tattered red coat and tricorn hat, 
with a hook prosthetic on left hand, one eye patch, holding a cutlass. 
Weathered skin, scar across left cheek, determined grimace.
Standing in a confident wide-legged stance, hands on hips.
```

### 示例2: 在脚本中自定义使用

```python
# scripts/generate_character.py 中的使用方式
from config import build_multiview_prompt

description = """
A medieval knight with ornate plate armor and tabard,
blonde long hair, holding a shield with family crest.
Noble expression, standing upright with spear in right hand.
"""

prompt = build_multiview_prompt(
    character_description=description,
    style="photorealistic 3D render",
    view_mode="4-view"
)

# prompt 现在包含新的改进版提示词
print(prompt)
```

---

## 🐛 问题排查

### 问题: 生成仍然有面部朝向摄像机的现象

**原因**: 模型可能仍在遵循旧的"设计展示"模式

**解决方案**:
1. 尝试使用"版本C: 严格几何"变体
2. 在提示词前添加: "This task is intended for 3D reconstruction and modeling reference. Accuracy is more important than aesthetics."
3. 考虑切换到不同的模型

### 问题: 四个视角的尺寸仍然不一致

**原因**: 相机焦距或距离可能在变化

**解决方案**:
1. 确认提示词中包含 "fixed radius and height"
2. 增加对此约束的重复强调
3. 检查生成的图像中是否确实违反了规则

### 问题: 背景仍然有场景细节

**原因**: 可能是模型偏差或提示词理解问题

**解决方案**:
1. 检查使用的是否是最新的 config.py
2. 尝试添加: "Background MUST be completely plain neutral color. No ground, no stage, no geometry."
3. 生成后用 image_processor.py 的背景去除功能

### 问题: 生成变慢了

**原因**: 可能是 4K 分辨率的要求

**解决方案**:
1. 可以在提示词中改为 "Resolution: 2K"
2. 或者在生成后才做分辨率提升
3. 检查是否是 API 端点的问题

---

## 🎯 验收标准

新提示词实施成功的标志：

✅ **几何维度**
- 四个视角中角色尺寸偏差 < 5%
- 肩膀宽度在各视角中保持一致
- 头部大小相对于身体保持一致

✅ **姿态维度**
- 没有观察到面部朝向摄像机的优化
- 衣服褶皱在各视角中位置相同
- 手臂方向和角度保持一致

✅ **背景维度**
- 背景是纯单色 (灰或白)
- 没有可见的地板、舞台或几何体
- 背景在四个视角中看起来相同

✅ **可靠性维度**
- 生成成功率 > 80% (首次就符合要求)
- 不需要多次重试来获得满意结果
- 不同用户描述下都能保持一致

---

## 📞 相关文件速查

| 目的 | 文件 | 行号 |
|------|------|------|
| 查看更新的标准提示词 | [scripts/config.py](scripts/config.py) | ~366 |
| 查看完整分析 | [docs/PROMPT_IMPROVEMENT_ANALYSIS.md](docs/PROMPT_IMPROVEMENT_ANALYSIS.md) | 全文 |
| 英文样本提示词 | [2d图生成提示词/英文4视角提示词sample_v3.0.md](2d图生成提示词/英文4视角提示词sample_v3.0.md) | 全文 |
| 中文样本提示词 | [2d图生成提示词/中文4视角提示词sample_v3.0.md](2d图生成提示词/中文4视角提示词sample_v3.0.md) | 全文 |
| 生成器脚本 | [scripts/gemini_generator.py](scripts/gemini_generator.py) | ~115-145 |
| 配置管理 | [scripts/config.py](scripts/config.py) | 全文 |

---

## ✨ 总结

你的脚本现在已经升级到了新的、更高成功率的四面图生成提示词。主要改进包括：

1. **认知框架**: 从"设计展示"转向"静态物体扫描"
2. **摄像机定义**: 明确的几何约束 (固定半径、高度)
3. **空间锁定**: 逐项列举需要保持一致的属性
4. **禁止项**: 明确列出模型常见的"优化"行为
5. **背景**: 纯中性，消除几何推理困扰
6. **配置**: 完整的技术规格参数

预期会看到四面图生成的一致性和成功率有显著提升。祝测试顺利！

