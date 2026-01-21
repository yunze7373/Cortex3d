# Gemini 图像编辑功能集成方案
> Cortex3d 项目中 Gemini API 的高级图像编辑能力设计

**当前日期**: 2026年1月22日  
**版本**: v1.0 (初始版本)  
**状态**: 设计方案

---

## 📋 目录

1. [Gemini 官方图像编辑功能](#1-gemini-官方图像编辑功能概览)
2. [当前项目能力分析](#2-当前项目能力分析)
3. [功能集成设计方案](#3-功能集成设计方案)
4. [API 限制与考量](#4-api-限制与考量)
5. [实现优先级](#5-实现优先级)
6. [代码集成路线图](#6-代码集成路线图)

---

## 1. Gemini 官方图像编辑功能概览

根据 [Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/image-generation?authuser=5#python_17)，支持以下图像编辑模式：

### 1.1 **添加和移除元素** ✅ (图片修改)
```
用途: 在现有图像中添加或删除对象/元素
模型: Gemini 3 Pro Image / Gemini 2.5 Flash Image
语法: 提供图片 + 编辑文本提示 → 输出修改后的图像

示例: 
  输入: 赛博女战士(正面视图图片) + "添加右肩炮台装置"
  输出: 带有炮台的赛博女战士正面视图
```

**Cortex3d 用途**:
- 添加配件: 武器、背包、特殊道具等
- 移除元素: 移除某些部位上的配件
- 样式调整: 修改服装细节

---

### 1.2 **语义遮盖/局部重绘** (Inpainting)
```
用途: 修改图像的特定部分，保留其余部分不变
模型: 通过对话定义"蒙版"，无需显式mask
语法: "只改变[特定元素]为[新元素]，保留其他不变"

示例:
  输入: 完整角色图片 + "只改变脸部表情，保留身体姿态"
  输出: 新表情的角色图像
```

**Cortex3d 用途**:
- 修复面部: 改善脸部表情、眼睛方向
- 细节纠正: 修复手指、姿势错误
- 风格一致: 在保持身体的情况下调整特定部位

---

### 1.3 **风格迁移** (Style Transfer)
```
用途: 以不同艺术风格重新创作图像内容
模型: Gemini 3 Pro Image (高级推理)
语法: "以[艺术风格]风格重新创作...，保持原始构图"

示例:
  输入: 3D角色模型图 + "以蒸汽朋克插画风格重新绘制"
  输出: 蒸汽朋克风格的角色插画
```

**Cortex3d 用途**:
- 角色美化: 从3D模型→插画级效果
- 风格多样化: 同一角色的不同艺术呈现
- 输出优化: 提升视觉质感

---

### 1.4 **高级构图/多图合成** (Advanced Composition)
```
用途: 合并多个图像元素创建新场景
模型: Gemini 3 Pro Image (支持最多14张参考图)
语法: 提供多张图片 + 构图指令 → 合成图像

支持:
  • 最多6张高保真对象图片(物品)
  • 最多5张人物图片(保持角色一致性)
  • 最多3张背景/场景图片

示例:
  输入: [角色正面图] + [背景1] + [道具] + "在战场中组合"
  输出: 角色在指定背景和道具中的合成图
```

**Cortex3d 用途**:
- 场景渲染: 角色 + 背景组合
- 多角色组合: 创建团队、合照效果
- 配件整合: 多个部件合成完整角色

---

### 1.5 **高保真细节保留** (High-fidelity Detail Preservation)
```
用途: 确保关键细节(脸部、logo等)在编辑时保留
机制: 在编辑请求中详细描述重要细节
语法: "确保[元素A]保持完全不变，仅修改[元素B]"

示例:
  输入: 品牌角色 + "保留脸部特征不变，更新背景"
  输出: 相同脸部、新背景的角色图
```

**Cortex3d 用途**:
- 脸部锁定: 编辑时保持脸部完全一致
- 姿势锁定: 编辑衣服时保持姿势
- 品牌一致性: 保留特征元素

---

### 1.6 **让事物焕发活力** (Bring Something to Life)
```
用途: 从粗糙草图/素描→精细成品图
模型: Gemini 3 Pro Image
语法: "将这个[素材]草图优化为[风格]照片，保留[特征]"

示例:
  输入: 手绘草图 + "转换为高质量漫画风格角色图"
  输出: 精细化的漫画风格角色
```

**Cortex3d 用途**:
- 艺术升级: 概念图 → 生产就绪图
- 质量提升: 低质参考 → 高质输出
- 风格优化: 快速草图 → 精致设计

---

### 1.7 **角色一致性: 360° 全景** ⭐ (已实现)
```
用途: 迭代生成不同角度保持角色一致性
模型: Gemini 3 Pro Image (官方推荐方法)
语法: 迭代提示 + 前一张图片作参考 → 新角度图像

示例:
  Step 1: 生成正面 → 保存为 reference_front.png
  Step 2: "侧视图，保持一致" + front.png → 侧视图
  Step 3: "背面，保持一致" + side.png → 背面
  ...
  最后: 拼接4/6/8视图
```

**Status**: ✅ 已实现 (--iterative-360 {4,6,8})

---

## 2. 当前项目能力分析

### 2.1 已实现功能

| 功能 | 实现状态 | 代码位置 | 说明 |
|------|--------|--------|------|
| **文生图** | ✅ 已实现 | `gemini_generator.py` | 基础多视图生成 |
| **图生图** | ✅ 已实现 | `gemini_generator.py` | 参考图像输入 |
| **迭代360°** | ✅ 已实现 | `generate_character.py#L17-219` | 4/6/8视图逐步生成 |
| **严格复制模式** | ✅ 已实现 | `generate_character.py#L286-293` | 基于参考图的严格模式 |
| **语义负提示** | ✅ 已实现 | `gemini_generator.py#L255-268` | QUALITY REQUIREMENTS格式 |

### 2.2 未实现但支持的功能

| 功能 | 支持度 | 优先级 | 原因 |
|------|--------|--------|------|
| **添加/移除元素** | 🟢 完全支持 | 🔴 高 | 手办细节优化、配件编辑 |
| **语义遮盖** | 🟢 完全支持 | 🔴 高 | 脸部/姿势修复、细节纠正 |
| **风格迁移** | 🟢 完全支持 | 🟡 中 | 美学优化、多风格输出 |
| **多图合成** | 🟢 完全支持 | 🟡 中 | 场景生成、多元素组合 |
| **细节保留** | 🟢 完全支持 | 🟡 中 | 保持一致性、品牌锁定 |
| **草图精细化** | 🟢 完全支持 | 🟡 中 | 概念→成品、快速迭代 |

---

## 3. 功能集成设计方案

### 3.1 高优先级 - 添加/移除元素编辑模式

#### 3.1.1 设计目标
```
功能名: --edit-add-remove 模式
输入: 已生成的角色图 + 编辑指令
输出: 修改后的新图像
```

#### 3.1.2 实现方案

**新参数**:
```python
parser.add_argument("--edit-elements", 
    type=str,
    help="""
    编辑模式: add|remove|modify
    格式: --edit-elements "add:右肩火焰炮"
    或: --edit-elements "remove:背包"
    或: --edit-elements "modify:衣服颜色为深红"
    """)

parser.add_argument("--from-edited",
    type=str,
    help="要编辑的源图像路径")
```

**函数签名**:
```python
def edit_character_elements(
    source_image_path: str,
    edit_instruction: str,  # "add:xxx", "remove:xxx", "modify:xxx"
    character_description: str,  # 原角色描述(用于上下文)
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    output_dir: str = "test_images",
) -> Optional[str]:
    """
    编辑角色的元素(添加/移除/修改)
    
    Args:
        source_image_path: 源图像路径
        edit_instruction: 编辑指令(add/remove/modify:细节)
        character_description: 角色描述
        ...
    
    Returns:
        编辑后图像的保存路径
    
    Prompt 模板:
        "Using the provided image of [角色描述], please [add/remove/modify] 
         [元素] to/from the scene. Ensure the change is [集成描述]."
    """
```

**调用示例**:
```bash
# 添加配件
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --edit-elements "add:双肩火焰炮台,发光胸甲" \
    --from-edited outputs/character_front.png

# 移除元素
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --edit-elements "remove:头部天线,腰部护甲" \
    --from-edited outputs/character_front.png

# 修改样式
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --edit-elements "modify:皮肤纹理为金属纹理,眼睛改为发光蓝色" \
    --from-edited outputs/character_front.png
```

---

### 3.2 高优先级 - 语义遮盖/脸部修复模式

#### 3.2.1 设计目标
```
功能名: --refine-details 模式
用途: 修复特定部位的细节问题
输入: 图像 + 修复部位 + 问题描述
输出: 修复后的图像
```

#### 3.2.2 实现方案

**新参数**:
```python
parser.add_argument("--refine-details",
    type=str,
    choices=["face", "hands", "pose", "custom"],
    help="指定要优化的细节部位")

parser.add_argument("--detail-issue",
    type=str,
    help="描述具体问题，例如: '左手有6根手指，需要修正为5根'")

parser.add_argument("--from-refine",
    type=str,
    help="要优化的源图像路径")
```

**函数签名**:
```python
def refine_character_details(
    source_image_path: str,
    detail_part: str,  # "face", "hands", "pose", or custom description
    issue_description: str,  # 具体问题描述
    character_description: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    output_dir: str = "test_images",
) -> Optional[str]:
    """
    优化角色的特定细节部位
    
    Prompt 模板:
        "Using the provided image, change only the [具体部位] to [新描述].
         Keep everything else in the image exactly the same, preserving the 
         original style, lighting, and composition."
    """
```

**调用示例**:
```bash
# 修复脸部表情
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --refine-details face \
    --detail-issue "脸部表情应该更凶悍，眼神更锐利" \
    --from-refine outputs/character_front.png

# 修复手指
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --refine-details hands \
    --detail-issue "左手应该是5根手指，不是6根" \
    --from-refine outputs/character_front.png

# 修复姿势
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --refine-details pose \
    --detail-issue "左脚应该往前迈一步，右脚往后" \
    --from-refine outputs/character_front.png

# 自定义修复
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --refine-details custom \
    --detail-issue "头部天线应该发出蓝色光芒" \
    --from-refine outputs/character_front.png
```

---

### 3.3 中优先级 - 风格迁移模式

#### 3.3.1 设计目标
```
功能名: --style-transfer 模式
用途: 将同一角色转换为不同艺术风格
输入: 角色图像 + 目标风格描述
输出: 新风格的角色图像
```

#### 3.3.2 实现方案

**新参数**:
```python
parser.add_argument("--style-transfer",
    type=str,
    help="""
    目标风格描述，例如:
    - '迪士尼卡通'
    - '日本漫画风'
    - '油画艺术风格'
    - 'steampunk illustration'
    - 'cyberpunk street art'
    """)

parser.add_argument("--from-style",
    type=str,
    help="要转换风格的源图像路径")
```

**函数签名**:
```python
def apply_style_transfer(
    source_image_path: str,
    target_style: str,  # 目标风格描述
    character_description: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    output_dir: str = "test_images",
) -> Optional[str]:
    """
    应用风格迁移
    
    Prompt 模板:
        "Transform the provided photograph of [角色] into the artistic style 
         of [目标风格]. Preserve the original composition but render it with 
         [风格特征]."
    """
```

**调用示例**:
```bash
# 转换为漫画风
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --style-transfer "高质量日本漫画风格，线条流畅，色彩鲜艳" \
    --from-style outputs/character_front_3d.png

# 转换为蒸汽朋克插画
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --style-transfer "维多利亚蒸汽朋克插画风格，古铜色调，齿轮装饰" \
    --from-style outputs/character_front_3d.png

# 转换为水彩艺术
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --style-transfer "精致水彩艺术风格，笔触细腻，优雅色彩" \
    --from-style outputs/character_front_3d.png
```

---

### 3.4 中优先级 - 多图合成模式

#### 3.4.1 设计目标
```
功能名: --composite-scene 模式
用途: 合并多个元素(角色+背景+道具)创建场景
输入: 多张图片(最多14张) + 场景描述
输出: 合成后的场景图像
```

#### 3.4.2 实现方案

**新参数**:
```python
parser.add_argument("--composite-scene",
    type=str,
    help="场景构图描述，例如: '在龙背上飞行，远景是赛博城市'")

parser.add_argument("--composite-images",
    type=str,
    nargs="+",
    help="""
    要合成的图像列表(最多14张):
    - 最多6张对象/道具图
    - 最多5张角色图
    - 最多3张背景图
    例: --composite-images char1.png char2.png bg.png prop.png
    """)
```

**函数签名**:
```python
def composite_scene(
    image_paths: List[str],  # 最多14张
    scene_description: str,  # 场景构图描述
    api_key: str,
    model_name: str = "gemini-3-pro-image-preview",  # 需Pro版本
    output_dir: str = "test_images",
) -> Optional[str]:
    """
    合成多个图像元素
    
    Prompt 模板:
        "Create a new image by combining the elements from the provided images.
         Take [元素1] and place it with/on [元素2]. The final image should be 
         a [场景描述]."
    
    注意: 需要使用 Gemini 3 Pro Image
    """
```

**调用示例**:
```bash
# 两个角色+背景
python scripts/generate_character.py \
    --composite-scene "两个赛博朋克战士在霓虹夜市中并肩站立" \
    --composite-images \
        outputs/warrior1_front.png \
        outputs/warrior2_front.png \
        backgrounds/neon_night_market.png

# 角色+多个道具
python scripts/generate_character.py \
    --composite-scene "赛博女战士在军事基地中央，双手握着能量剑" \
    --composite-images \
        outputs/character_front.png \
        props/energy_sword.png \
        props/energy_sword.png \
        backgrounds/military_base.png
```

---

### 3.5 低优先级 - 高保真细节保留模式

#### 3.5.1 设计目标
```
功能名: --lock-features 模式
用途: 在编辑时锁定关键细节(脸部/姿势)不变
输入: 图像 + 锁定部位列表 + 编辑指令
输出: 编辑后保留锁定部位的图像
```

#### 3.5.2 实现方案

**新参数**:
```python
parser.add_argument("--lock-features",
    type=str,
    nargs="+",
    choices=["face", "pose", "eyes", "hands", "torso", "legs"],
    help="要锁定的部位，保证编辑时保持不变")

parser.add_argument("--edit-with-lock",
    type=str,
    help="编辑指令(同时指定了锁定部位)")

parser.add_argument("--from-lock",
    type=str,
    help="源图像路径")
```

**调用示例**:
```bash
# 锁定脸部，修改衣服
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --lock-features face \
    --edit-elements "modify:衣服从黑色改为红色" \
    --from-lock outputs/character_front.png

# 锁定脸部和姿势，修改背景效果
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --lock-features face pose \
    --edit-elements "modify:添加背景霓虹灯光效果" \
    --from-lock outputs/character_front.png
```

---

### 3.6 低优先级 - 草图精细化模式

#### 3.6.1 设计目标
```
功能名: --refine-sketch 模式
用途: 将粗糙草图/低质图→精细高质图
输入: 草图/低质图 + 风格描述
输出: 精细化的高质图像
```

#### 3.6.2 实现方案

**新参数**:
```python
parser.add_argument("--refine-sketch",
    action="store_true",
    help="激活草图精细化模式")

parser.add_argument("--sketch-style",
    type=str,
    help="目标风格，例如: 'high-quality digital art', '3D render'等")

parser.add_argument("--from-sketch",
    type=str,
    help="草图源文件路径")
```

**调用示例**:
```bash
# 精细化概念草图
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --refine-sketch \
    --sketch-style "高保真3D渲染角色模型" \
    --from-sketch concepts/rough_sketch.png

# 改进低质参考图
python scripts/generate_character.py \
    "赛博朋克女战士" \
    --refine-sketch \
    --sketch-style "专业数字艺术插画" \
    --from-sketch references/low_quality_ref.jpg
```

---

## 4. API 限制与考量

### 4.1 模型选择

| 需求 | 推荐模型 | 原因 |
|------|--------|------|
| **快速编辑** | `gemini-2.5-flash-image` | 低成本、低延迟 |
| **高质编辑** | `gemini-3-pro-image-preview` | 高级推理、思考过程 |
| **多图合成** | `gemini-3-pro-image-preview` | 仅支持14张参考 |
| **精细保留** | `gemini-3-pro-image-preview` | 思考模式优化 |

### 4.2 输入限制

```python
限制总结:
{
    "gemini-2.5-flash-image": {
        "max_images": 3,
        "max_resolution": "1024x1024",
        "supported_formats": ["png", "jpeg", "gif", "webp"],
        "cost_per_image": "低"
    },
    "gemini-3-pro-image-preview": {
        "max_images": 14,  # 可混合
        "max_resolution": "4096x4096",  # 最高4K
        "supported_formats": ["png", "jpeg", "gif", "webp"],
        "object_images_max": 6,
        "person_images_max": 5,
        "cost_per_image": "高"
    }
}
```

### 4.3 多轮对话管理

```python
# 需要处理思维签名(Thought Signature)
# Gemini 3 Pro 返回的响应包含思维签名，用于保持推理上下文

chat = client.chats.create(model="gemini-3-pro-image-preview")
response1 = chat.send_message(prompt1)  # 返回thought_signature

# 后续轮次必须包含完整历史和签名
response2 = chat.send_message(
    prompt2,
    history=[response1]  # SDK自动处理签名
)
```

### 4.4 成本优化

```python
建议策略:
1. 开发用 gemini-2.5-flash-image (成本低)
2. 生产用 gemini-3-pro-image-preview (质量高)
3. 批量操作使用 Batch API (24小时等待，便宜)
4. 实时编辑使用同步 API (快速，贵)
```

---

## 5. 实现优先级

### 5.1 优先级排序

```
第一阶段 (高优先 - Cortex3d 核心需求)
├─ P0.1: 添加/移除元素编辑 (edit_character_elements)
│  └─ 用途: 手办配件编辑、细节定制
│  └─ 工作量: 中等 (基础实现)
│  └─ 收益: 高 (直接提升手办质量)
│
└─ P0.2: 语义遮盖/脸部修复 (refine_character_details)
   └─ 用途: 脸部表情/手指/姿势修复
   └─ 工作量: 中等
   └─ 收益: 高 (解决常见质量问题)

第二阶段 (中优先 - 增强功能)
├─ P1.1: 风格迁移 (apply_style_transfer)
│  └─ 用途: 美学多样化、渲染优化
│  └─ 工作量: 中等
│  └─ 收益: 中 (提升视觉效果)
│
└─ P1.2: 多图合成 (composite_scene)
   └─ 用途: 场景生成、多角色组合
   └─ 工作量: 高 (复杂构图管理)
   └─ 收益: 中 (高级功能)

第三阶段 (低优先 - 高级功能)
├─ P2.1: 细节保留锁定 (lock_features)
│  └─ 用途: 保持一致性、品牌锁定
│  └─ 工作量: 低
│  └─ 收益: 低 (已有iterative-360)
│
└─ P2.2: 草图精细化 (refine_sketch)
   └─ 用途: 概念→成品、快速迭代
   └─ 工作量: 低
   └─ 收益: 低 (特定用例)
```

---

## 6. 代码集成路线图

### 6.1 模块结构设计

```
scripts/
├── gemini_generator.py              (已有，核心生成)
│   ├── generate_character_views()   (已实现: 基础生成)
│   └── [新增] generate_character_edits()
│       ├── _edit_add_remove_elements()
│       ├── _refine_character_details()
│       ├── _apply_style_transfer()
│       ├── _composite_scene()
│       └── _lock_features_edit()
│
├── generate_character.py            (已有，CLI入口)
│   ├── _iterative_360_generation()  (已实现)
│   ├── [新增] edit_mode_handler()
│   ├── [新增] refine_mode_handler()
│   ├── [新增] style_mode_handler()
│   ├── [新增] composite_mode_handler()
│   └── main() - 路由逻辑
│
└── image_editor_utils.py            (新增工具库)
    ├── validate_image_input()
    ├── process_multi_image_input()
    ├── compose_prompt_for_editing()
    ├── handle_thought_signatures()
    └── manage_edit_session_history()
```

### 6.2 第一阶段实现 (P0 功能)

#### 步骤1: 扩展 gemini_generator.py

```python
# 新增函数 (在 generate_character_views 之后)

def edit_character_elements(
    source_image_path: str,
    edit_instruction: str,
    character_description: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    output_dir: str = "test_images",
    auto_cut: bool = True,
    style: str = "cinematic character",
    export_prompt: bool = False
) -> Optional[str]:
    """编辑角色的元素(添加/移除/修改)"""
    # 实现逻辑...

def refine_character_details(
    source_image_path: str,
    detail_part: str,
    issue_description: str,
    character_description: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL,
    output_dir: str = "test_images",
    export_prompt: bool = False
) -> Optional[str]:
    """优化角色的特定细节部位"""
    # 实现逻辑...
```

#### 步骤2: 扩展 generate_character.py

```python
# 新增参数解析

parser.add_argument("--mode", 
    choices=["generate", "edit", "refine", "style", "composite"],
    default="generate",
    help="操作模式")

parser.add_argument("--edit-elements", type=str)
parser.add_argument("--from-edited", type=str)

parser.add_argument("--refine-details", 
    choices=["face", "hands", "pose", "custom"])
parser.add_argument("--detail-issue", type=str)
parser.add_argument("--from-refine", type=str)

# 路由逻辑
if args.mode == "edit":
    result = edit_mode_handler(args)
elif args.mode == "refine":
    result = refine_mode_handler(args)
```

### 6.3 集成检查清单

```
P0 功能集成 (添加/移除/语义遮盖):
□ 扩展 gemini_generator.py (2 个新函数)
□ 扩展 generate_character.py 参数 (6 个新参数)
□ 创建 image_editor_utils.py (工具函数)
□ 添加单元测试 (tests/test_image_editing.py)
□ 更新文档 (docs/IMAGE_EDITING_GUIDE.md)
□ 集成 smoke 测试
□ 性能基准测试

预计工作量: 20-30 小时
预计成本影响: 中等 (API调用增加)
```

---

## 7. 设计关键决策

### 7.1 为什么优先 P0 功能?

1. **直接解决核心问题**
   - 手办生成中最常见的质量问题: 细节错误、表情不满意
   - 添加/移除元素 = 高度定制化

2. **快速收益**
   - 不需要复杂的多图管理
   - API 支持简单直接

3. **用户体验**
   - 单步操作 (源图 + 编辑指令 → 输出)
   - 清晰的CLI接口

### 7.2 为什么延迟 P1/P2 功能?

1. **复杂性**
   - 多图合成需要精心的模型指导
   - 场景构图有更多变量

2. **成本考虑**
   - 多图合成更贵 (需Pro版本 + 多图input)
   - 应先验证 P0 ROI

3. **用户需求**
   - P0 更符合 Cortex3d 的直接需求
   - P1/P2 是"锦上添花"功能

---

## 8. 与现有迭代360°模式的关系

```
现有: --iterative-360 {4,6,8}
功能: 多视角生成 (仅关心不同视角)
特点: 图→图, 参考链
约束: 每次一个视角

新增: --edit-elements / --refine-details
功能: 质量优化 (关心特定部位的改进)
特点: 图→修改图→输出
约束: 单次编辑

集成建议:
workflow1 = --iterative-360 8 (生成8视图)
     ↓
[检查质量]
     ↓
workflow2 = --refine-details face (修复脸部)
     ↓
[final check]
```

---

## 9. 后续增强方向

### 9.1 短期 (1-2周)
- 实现 P0 两个函数
- 完成单元测试
- 文档和示例

### 9.2 中期 (3-4周)
- 实现 P1 功能
- 性能优化 (批处理)
- 成本分析和优化

### 9.3 长期 (1-2月)
- 实现 P2 功能
- 工作流编排 (pipeline)
- 高级场景管理

---

## 📚 参考资源

- [Gemini 图像生成API文档](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini 3 Pro Image 官方文档](https://ai.google.dev/gemini-api/docs/models/gemini?authuser=5&hl=zh-cn#gemini-3-pro-image-preview)
- [Cortex3d 项目文档](../README.md)
- [迭代360°生成指南](ITERATIVE_360_GUIDE_V2.md)

---

**最后更新**: 2026-01-22
**维护者**: Cortex3d 开发团队
**反馈**: 欢迎提交 Issue 和 Pull Request
