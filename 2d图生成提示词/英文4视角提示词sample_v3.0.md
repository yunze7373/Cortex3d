# 改进的英文四面图生成提示词 (v3.0)

这是基于高成功率提示词的改进版本，融合了"static object"和"camera orbit"的核心概念。

## 完整提示词

```
Generate a STRICT multi-view reference sheet with EXACTLY 4 panels.

This is a GEOMETRIC CAMERA ORBIT TASK, not a character redesign task.

The subject is a STATIC OBJECT in 3D space.
Only the CAMERA position changes.
NO pose correction, NO aesthetic adjustment, NO reinterpretation.

==================================================
## OUTPUT LAYOUT (MANDATORY)
Single image with exactly 4 equal-sized panels in ONE horizontal row only.

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

Failure to follow these rules is unacceptable.

[CHARACTER DESCRIPTION]
```

## 高级变体

### 版本A: 重建导向 (推荐用于3D重建流程)

在原提示词基础上，最后添加：

```
This task is intended for 3D reconstruction and modeling reference.
Accuracy is more important than aesthetics.
Geometric correctness is critical for downstream 3D processing.
```

### 版本B: 摄影风格 (推荐用于photorealistic风格)

在原提示词基础上，修改背景部分为：

```
## BACKGROUND & ENVIRONMENT
- Pure neutral gray or white background
- Professional studio photography lighting
- Even, diffuse illumination (no harsh shadows or dramatic effects)
- Seamless background
- Subject appears naturally grounded without visible stage
```

### 版本C: 严格几何 (推荐用于需要最高精度的场景)

在原提示词最后添加：

```
## 🎯 GEOMETRIC PRECISION REQUIREMENTS

This is NOT character art. This is 3D reference documentation.

Every millimeter matters. Accuracy > Aesthetics.

- Geometric consistency across panels is the ONLY metric that matters
- Do NOT optimize for visual appeal or symmetry
- Do NOT correct perceived anatomy issues
- Do NOT smooth or idealize forms

Treat this as if you are photographing a physical scanned object.
```

## 关键改进总结

✅ **认知转换**: 从"角色设计"转向"静态物体扫描"  
✅ **显式相机定义**: 固定半径、固定高度、固定中心点  
✅ **极具体的空间锁定**: 逐项列举每个需要保持一致的属性  
✅ **禁止"优化"**: 明确列出模型的常见"好心帮忙"行为  
✅ **配置参数**: 提供分辨率、宽高比、采样策略  
✅ **中性背景**: 消除复杂背景的几何推理困难  
✅ **最终约束**: "Failure to follow these rules is unacceptable" 提升权重  

## 测试建议

使用这个提示词与之前的版本对比生成同一个角色，观察：

1. 四个视角中角色尺寸是否更一致？
2. 是否仍有"面部朝向相机"现象？
3. 衣服褶皱位置是否在四个视角中稳定？
4. 背景是否真的是纯中性的？
5. 生成速度是否有变化？

