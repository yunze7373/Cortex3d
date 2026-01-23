# 四面图生成提示词对比分析与改进方案

## 📊 对比总结

### 现有提示词的问题

你现有的提示词（在 `2d图生成提示词/` 和 `config.py` 中）采用了 **"旋转平台/Turntable"** 范式，但在几个关键点上与新提示词存在明显差异：

| 维度 | 现有版本 | 新版本 | 影响 |
|------|---------|--------|------|
| **核心概念** | "旋转平台上的角色" | "摄像机绕静止物体轨道" | 🔴 关键差异 |
| **角色认知** | CHARACTER DESIGN (设计图) | STATIC OBJECT / scanned physical object (扫描物体) | 🔴 认知转换 |
| **相机定义** | 隐含的旋转轨迹 | 显式的固定半径和高度 | 🟡 精度差异 |
| **视距控制** | 未明确指定 | "fixed radius and height" | 🟡 一致性 |
| **禁止指令** | 基础禁止项 | 明确禁止"fix/adjust/correct" | 🔴 成功率 |
| **约束强度** | 中等强制性 | "Failure is unacceptable" | 🟡 模型遵守率 |
| **背景描述** | 详细场景(城市废墟等) | 纯中性背景(灰/白) | 🟡 背景统一性 |

---

## 🧠 核心改进点深度分析

### 1️⃣ **认知范式转换** (最关键)

#### 现有方式：
```
"Generate a professional 3D character turntable reference sheet..."
"Imagine the character standing on a rotating platform..."
```
❌ **问题**: 模型将其理解为"设计展示"，容易：
- 美化角色
- 调整姿态以获得更好的视觉效果
- 在不同视角中微调表情/姿态

#### 新方式：
```
"The subject is a STATIC OBJECT in 3D space."
"This is a GEOMETRIC CAMERA ORBIT TASK, not a character redesign task."
"Treat the subject as a scanned physical object"
```
✅ **优势**: 
- 强制模型进入"三维重建"而非"角色设计"思维
- 所有变化都来自几何透视，而非美学调整
- 显著提升四面体的几何正确性

**核心语义差异** = 模型底层处理逻辑的根本不同

---

### 2️⃣ **显式相机轨迹定义**

#### 现有方式：
```
- Panel 1 (FRONT): Platform at 0° - We see the FACE, chest, front of body
- Panel 2 (RIGHT SIDE): Platform rotated 90° clockwise
```
⚠️ **隐含问题**:
- 相机距离在不同视角可能变化
- 上下视角漂移未被约束
- 不同 panel 可能尺寸不一致

#### 新方式：
```
Camera rotates around the subject at a **fixed radius and height**.
Camera target is the subject's **original center**.
The subject does NOT rotate.
```
✅ **好处**:
- 所有视角距离相同 → 尺寸一致
- 固定高度 → 不会出现上下漂移
- 几何关系明确可验证

---

### 3️⃣ **绝对禁止指令** (成功率直接提升)

#### 现有方式：
```
❌ NO pose correction
❌ NO mirroring
```
只是简单的否定列表。

#### 新方式：
```
❌ DO NOT adjust pose for visibility
❌ DO NOT rotate body to face the camera
❌ DO NOT mirror or swap left/right anatomy
❌ DO NOT "fix" anatomy per view

ONLY perspective changes due to camera rotation are allowed.
```
**+关键一句**:
```
"Failure to follow these rules is unacceptable."
```

✅ **为何更强有力**:
1. 明确说出模型最常犯的错误 ("fix" / "adjust" / "correct")
2. 正面阐述唯一允许的变化来源 (perspective only)
3. 最后一句提升了约束权重 (虽然是人类语言，但对部分大模型有效)

---

### 4️⃣ **空间锁定的明确声明**

#### 现有方式：
```
"Same pose in ALL panels"
```
笼统的要求。

#### 新方式：
```
## 🔒 ABSOLUTE SPATIAL LOCK — ZERO DEVIATION ALLOWED

The subject is FROZEN in world space.

ALL spatial relationships are locked relative to the BODY, not the camera.

The following MUST remain 100% IDENTICAL across ALL panels:
- Head tilt, head rotation
- Eye direction and gaze angle (NO eye contact correction)
- Facial expression
- Shoulder angle
- Arm position, bend angle, hand orientation
- Leg stance, weight distribution, crossing order
- Torso lean, twist, and center of mass
- Clothing folds and attachment points
- Accessories, weapons, props and their relative positions
```

✅ **优势**:
- **极其具体** - 逐项列举，排除了模型的"创意自由"
- **数值化** - "100% IDENTICAL" 比 "same" 更强有力
- **排除常见偷工** - 特别标注 "NO eye contact correction" (模型常做的优化)

---

### 5️⃣ **背景处理的差异**

#### 现有方式：
```
环境：废弃的城市废墟/末日街道
元素：破碎的沥青路、碎片、翻倒的生锈汽车
背景：大气雾霭，远处模糊的建筑废墟
```
📌 **问题**: 详细的背景会导致：
- 四个视角中背景不一致 (因为角色转身，背景看起来不同)
- 模型可能"创意修复"背景的透视错误
- 浪费模型的注意力

#### 新方式：
```
Pure neutral gray or white background
Seamless, studio-style environment
No visible floor, horizon, ground texture, or stage
No turntable, pedestal, disc, or platform
Subject appears naturally grounded without visible geometry
```
✅ **好处**:
- **背景一致** - 中性背景在任何视角都看起来相同
- **减少歧义** - 模型不需要处理复杂的空间推理
- **聚焦主体** - 所有模型能力都用在正确生成角色上

---

### 6️⃣ **配置参数建议的加入**

#### 新增：
```
Resolution: 4K
Aspect Ratio: 3:2
Sampling: deterministic / low randomness
```
现有提示词完全缺少这些。

✅ **意义**:
- 告诉模型预期的输出规格
- "deterministic" 减少随机性，提升一致性
- 3:2 比例是标准工业设计参考尺寸

---

## 📝 改进方案

### 方案一：直接替换标准模板 (推荐)

在 `scripts/config.py` 中，将 `_LEGACY_MULTIVIEW_TEMPLATE` 替换为新版本：

```python
_LEGACY_MULTIVIEW_TEMPLATE = """Generate a STRICT multi-view reference sheet with EXACTLY 4 panels, based on the reference image.

This is a GEOMETRIC CAMERA ORBIT TASK, not a character redesign task.

The subject is a STATIC OBJECT in 3D space.
Only the CAMERA position changes.
NO pose correction, NO aesthetic adjustment, NO reinterpretation.

==================================================
## OUTPUT LAYOUT (MANDATORY)
Single image.
Exactly 4 equal-sized panels in ONE horizontal row only.

Order (left to right):
[FRONT 0°] [RIGHT 90°] [BACK 180°] [LEFT 270°]

No labels, no text, no markers inside the image.
==================================================

## CAMERA DEFINITION (CRITICAL)

Camera rotates around the subject at a fixed radius and height.
Camera target is the subject's original center.

The subject does NOT rotate.

--------------------------------------------------
### THE 4 REQUIRED VIEWS

Panel 1 — FRONT (0°):
- Camera faces the FRONT of the subject
- Subject front is fully visible
- This view must visually MATCH the reference image orientation

Panel 2 — RIGHT (90°):
- Camera is positioned on the SUBJECT'S RIGHT side
- The SUBJECT'S RIGHT SIDE faces the camera
- The subject's FRONT points toward the LEFT edge of the image

Panel 3 — BACK (180°):
- Camera faces the BACK of the subject
- Subject back is fully visible
- Subject front is completely hidden

Panel 4 — LEFT (270°):
- Camera is positioned on the SUBJECT'S LEFT side
- The SUBJECT'S LEFT SIDE faces the camera
- The subject's FRONT points toward the RIGHT edge of the image
--------------------------------------------------

==================================================
## 🔒 ABSOLUTE SPATIAL LOCK — ZERO DEVIATION ALLOWED

The subject is FROZEN in world space.

ALL spatial relationships are locked relative to the BODY, not the camera.

The following MUST remain 100% IDENTICAL across ALL panels:

- Head tilt, head rotation
- Eye direction and gaze angle (NO eye contact correction)
- Facial expression
- Shoulder angle
- Arm position, bend angle, hand orientation
- Leg stance, weight distribution, crossing order
- Torso lean, twist, and center of mass
- Clothing folds and attachment points
- Accessories, weapons, props and their relative positions

❌ DO NOT adjust pose for visibility
❌ DO NOT rotate body to face the camera
❌ DO NOT mirror or swap left/right anatomy
❌ DO NOT "fix" anatomy per view

ONLY perspective changes due to camera rotation are allowed.
==================================================

## 🎨 STYLE CONSTRAINTS
- Cinematic character design
- EXACT style match to reference image
- Identical materials, lighting mood, and surface detail
- Consistent rendering quality across all panels

==================================================
## BACKGROUND & ENVIRONMENT
- Pure neutral gray or white background
- Seamless, studio-style environment
- No visible floor, horizon, ground texture, or stage
- No turntable, pedestal, disc, or platform
- Subject appears naturally grounded without visible geometry

==================================================
## CHARACTER DESCRIPTION
{character_description}

Style: {style}

==================================================
## CONFIGURATION PARAMETERS
Resolution: 4K
Aspect Ratio: 3:2
Sampling: deterministic (low randomness)

==================================================
## FINAL HARD RULES

- EXACTLY 4 panels — no more, no less
- Identical scale and framing across panels
- No duplicated or mirrored views
- No creative interpretation
- Treat the subject as a scanned physical object

Failure to follow these rules is unacceptable."""
```

---

### 方案二：为不同模式创建专门模板

在 `scripts/prompts/__init__.py` 中新增方法：

```python
def _get_improved_standard_template(self) -> str:
    """改进的标准4视角模板 (v3.0)"""
    return """Generate a STRICT multi-view reference sheet with EXACTLY 4 panels.

This is a GEOMETRIC CAMERA ORBIT TASK, not a character redesign task.

The subject is a STATIC OBJECT in 3D space.
Only the CAMERA position changes.
NO pose correction, NO aesthetic adjustment, NO reinterpretation.

## OUTPUT LAYOUT (MANDATORY)
Single image with exactly 4 equal-sized panels in ONE horizontal row.
Order: [FRONT 0°] [RIGHT 90°] [BACK 180°] [LEFT 270°]

## CAMERA DEFINITION (CRITICAL)
- Camera rotates around the subject at a fixed radius and height
- Camera target is the subject's original center
- The subject does NOT rotate

## THE 4 REQUIRED VIEWS

Panel 1 — FRONT (0°):
- Camera faces the FRONT of the subject
- Subject front is fully visible

Panel 2 — RIGHT (90°):
- Camera is on the SUBJECT'S RIGHT side
- SUBJECT'S RIGHT SIDE faces the camera

Panel 3 — BACK (180°):
- Camera faces the BACK of the subject
- Subject back is fully visible
- Subject front is completely hidden

Panel 4 — LEFT (270°):
- Camera is on the SUBJECT'S LEFT side
- SUBJECT'S LEFT SIDE faces the camera

## 🔒 ABSOLUTE SPATIAL LOCK — ZERO DEVIATION ALLOWED
The subject is FROZEN in world space.

The following MUST remain 100% IDENTICAL across ALL panels:
- Head tilt, head rotation
- Eye direction and gaze angle (NO eye contact correction)
- Facial expression
- Shoulder angle  
- Arm position, bend angle, hand orientation
- Leg stance, weight distribution, crossing order
- Torso lean, twist, center of mass
- Clothing folds and attachment points
- Accessories, weapons, props positions

❌ DO NOT adjust pose for visibility
❌ DO NOT rotate body to face the camera
❌ DO NOT mirror or swap left/right anatomy
❌ DO NOT "fix" anatomy per view

ONLY perspective changes from camera rotation are allowed.

## CHARACTER
{character_description}

Style: {style}

## STYLE CONSTRAINTS
- Cinematic character design
- EXACT style match to input description
- Identical materials, lighting, and surface detail
- Consistent rendering quality across all panels

## BACKGROUND & ENVIRONMENT
- Pure neutral gray or white background
- Seamless, studio-style environment
- No visible floor, horizon, ground texture, or stage
- No turntable, pedestal, or platform
- Subject appears naturally grounded

## CONFIGURATION
Resolution: 4K
Aspect Ratio: 3:2
Sampling: deterministic (low randomness)

## FINAL HARD RULES
- EXACTLY 4 panels — no more, no less
- Identical scale and framing across panels
- No duplicated or mirrored views
- No creative interpretation
- Treat the subject as a scanned physical object

Failure to follow these rules is unacceptable."""
```

---

### 方案三：添加高级约束选项

```python
def get_enhanced_prompt_variants():
    """获取改进版提示词及其变体"""
    return {
        "standard": _get_improved_standard_template(),
        "with_reconstruction_hint": _get_improved_standard_template() + """

## 🎯 RECONSTRUCTION INTENT
This task is intended for 3D reconstruction and modeling reference.
Accuracy is more important than aesthetics.
Geometric correctness is critical for downstream 3D processing.""",
        "photorealistic_strict": _get_improved_standard_template() + """

## 📸 PHOTOREALISTIC VARIANT
Generate as if capturing a scanned real object or high-quality photography.
Every detail must be consistent across all 4 angles."""
    }
```

---

## 🔄 迁移建议

### 短期（立即）
1. 在 `config.py` 中更新 `_LEGACY_MULTIVIEW_TEMPLATE`
2. 添加配置参数（分辨率、宽高比等）

### 中期（本周）
1. 在 `prompts/__init__.py` 中创建 `_get_improved_standard_template()`
2. 更新 `build_multiview_prompt()` 以支持版本选择
3. 在脚本中添加 `--prompt-version` 参数

### 长期（优化）
1. 为不同模型类型创建专门的提示词变体
2. 添加 A/B 测试框架来衡量效果改进
3. 根据实际结果再次微调

---

## ✅ 验证清单

部署新提示词后，验证以下点：

- [ ] 四个视角中角色尺寸是否一致？
- [ ] 是否仍有"面部朝向相机"的优化？
- [ ] 服装褶皱是否在四个视角中位置一致？
- [ ] 背景是否真的是中性的？
- [ ] 有无多余的文字标签？
- [ ] 生成速度/成本是否有显著变化？

---

## 📚 相关文件位置

- **现有标准模板**: [config.py#L366](scripts/config.py#L366)
- **旧版 turntable 模板**: [config.py#L366-L410](scripts/config.py#L366-L410)
- **提示词库管理**: [prompts/__init__.py#L100-L120](scripts/prompts/__init__.py#L100-L120)
- **四面图生成调用**: [gemini_generator.py#L115-L145](scripts/gemini_generator.py#L115-L145)
- **样本提示词**: [2d图生成提示词/](2d图生成提示词/)

---

## 🎯 预期效果

采用新提示词后，预期改进：

| 指标 | 改进幅度 |
|------|----------|
| 几何一致性 | ⬆️⬆️⬆️ (高) |
| 四个视角尺寸一致度 | ⬆️⬆️⬆️ (显著) |
| 姿态稳定性 | ⬆️⬆️⬆️ (显著) |
| 避免面部优化 | ⬆️⬆️ (中等) |
| 背景一致性 | ⬆️⬆️⬆️ (显著) |
| 成功率 (首次就正确) | ⬆️⬆️⬆️ (20-40% 提升) |

