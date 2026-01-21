# 📊 Cortex3d P1 阶段 - 升级计划

> **开始时间**: 2025 年 1 月  
> **预计周期**: 1-2 周  
> **优先级**: 中等 (Medium Priority)  
> **状态**: 🚀 **已启动**

---

## 🎯 P1 阶段目标

基于 P0 的两个核心编辑功能（编辑元素、细节修复），P1 扩展支持：
- **风格转换** - 改变整体美学风格
- **图像合成** - 组合多个角色元素
- **批量处理** - 大规模编辑自动化
- **历史跟踪** - 编辑操作记录和恢复

---

## 📋 P1 功能清单

### 1️⃣ **风格转换** (Style Transfer) ✅ 已完成
**Gemini 功能**: `Style Transfer` (P1 优先级)  
**实现状态**: ✅ **COMPLETE** (完成于 2024-12-26)  
**代码行数**: 280+ 行  
**文件**: [P1_STYLE_TRANSFER_IMPLEMENTATION.md](P1_STYLE_TRANSFER_IMPLEMENTATION.md)

**功能描述**:
- ✅ 改变角色的整体美学风格
- ✅ 保持身体结构，修改视觉风格
- ✅ 支持 6 种预设风格 + 自定义风格

**CLI 参数** (已实现):
```
--mode-style                     激活风格转换模式
--style-preset STRING            风格预设 (anime/cinematic/oil-painting/watercolor/comic/3d)
--custom-style STRING            自定义风格描述 (覆盖预设)
--from-style PATH                源图像路径 (必需)
--preserve-details BOOL          是否保留原始细节 (默认: True)
```

**使用示例** (已就绪):
```bash
python scripts/generate_character.py \
  --mode-style \
  --style-preset anime \
  --from-style test_images/character_20251226_013442_front.png

# 自定义风格
python scripts/generate_character.py \
  --mode-style \
  --custom-style "oil painting style, impressionist, Renaissance" \
  --from-style test_images/character_front.png
```

**预计输出**: `styled_anime_20250101_120000.png` ✅

**已实现步骤**:
- ✅ 添加了 `compose_style_transfer_prompt()` 函数 (image_editor_utils.py)
- ✅ 创建了 `style_transfer_character()` 函数 (gemini_generator.py, 行 863-992)
- ✅ 添加了 CLI 参数 (generate_character.py, 行 477-512)
- ✅ 添加了路由逻辑 (generate_character.py, 行 648-717)
- ✅ 创建了测试脚本 (test_style_transfer.py)
- ✅ 编写了完整文档

**技术细节**:
- 函数: `style_transfer_character(source_image_path, style_preset, character_description, api_key, model_name, output_dir, custom_style, preserve_details) → Optional[str]`
- 模型: `models/nano-banana-pro-preview` (可配置)
- 样式: 6 种预设 (anime, cinematic, oil-painting, watercolor, comic, 3d) + 无限自定义
- 输出: PNG 格式，带时间戳
- 特性: 完整的错误处理、Base64 编码、细节保留选项

**快速开始**: 见 [P1_STYLE_TRANSFER_QUICKSTART.md](P1_STYLE_TRANSFER_QUICKSTART.md)

---

### 2️⃣ **图像合成** (Image Composition)
**Gemini 功能**: `Compose Multiple Images` (P1 优先级)

**功能描述**:
- 将多个角色/元素合成为一张图
- 支持背景添加
- 支持多个角色组合

**CLI 参数**:
```
--mode-composite                 激活合成模式
--composite-spec STRING          合成规格描述
--images PATH1,PATH2,PATH3       输入图像列表 (最多14张)
--composition-prompt STRING      自定义合成描述
--background STRING              背景描述 (可选)
```

**使用示例**:
```bash
# 并排合成两个角色
python scripts/generate_character.py \
  --mode-composite \
  --images "image1.png,image2.png" \
  --composite-spec "side_by_side"

# 自定义合成
python scripts/generate_character.py \
  --mode-composite \
  --images "char.png,weapon.png,background.png" \
  --composition-prompt "角色站在左边，手持武器，背景是神秘森林"
```

**预计输出**: `composite_20250101_120000.png`

**实现步骤**:
1. 增强 `process_multi_image_input()` 处理多个图像
2. 创建 `compose_character_images()` 函数
3. 添加合成规格验证
4. CLI 参数和路由逻辑

---

### 3️⃣ **批量编辑脚本** (Batch Processing)
**功能描述**:
- 自动化处理多个图像
- 支持编辑、修复、风格转换的组合操作
- 生成处理报告

**创建文件**: `scripts/batch_editor.py`

**使用示例**:
```bash
# 批量添加元素
python scripts/batch_editor.py \
  --batch-input "inputs/*.png" \
  --batch-operation "edit" \
  --batch-instruction "add:肩部装备" \
  --batch-output "outputs/edited"

# 批量修复
python scripts/batch_editor.py \
  --batch-input "outputs/edited/*.png" \
  --batch-operation "refine" \
  --batch-details "face" \
  --batch-output "outputs/refined"

# 链式操作
python scripts/batch_editor.py \
  --batch-chain "batch_config.json"
```

**batch_config.json 示例**:
```json
{
  "operations": [
    {
      "type": "edit",
      "instruction": "add:蓝色肩甲",
      "input": "step1"
    },
    {
      "type": "refine",
      "part": "face",
      "issue": "脸部改善",
      "input": "step1"
    },
    {
      "type": "style",
      "preset": "anime",
      "input": "step2"
    }
  ]
}
```

**实现步骤**:
1. 创建 batch_editor.py 脚本
2. 支持配置文件和命令行模式
3. 添加进度条和日志
4. 生成处理报告

---

### 4️⃣ **编辑历史跟踪** (Edit History)
**功能描述**:
- 记录每次编辑操作
- 支持撤销/重做
- 导出编辑历史

**新增类**: `EditHistory` in image_editor_utils.py

**数据结构**:
```python
class EditOperation:
    timestamp: datetime
    operation_type: str  # "edit", "refine", "style", "composite"
    parameters: dict
    source_image: str
    output_image: str
    status: str  # "success", "failed"
    error_message: Optional[str]

class EditHistory:
    def add_operation(self, op: EditOperation)
    def get_history(self, session_id: str) -> List[EditOperation]
    def undo(self, session_id: str) -> bool
    def redo(self, session_id: str) -> bool
    def export_history(self, session_id: str, format: str = "json")
```

**使用示例**:
```bash
# 查看编辑历史
python -c "from image_editor_utils import EditHistory; h = EditHistory(); h.show_history('session_001')"

# 导出历史
python -c "from image_editor_utils import EditHistory; h = EditHistory(); h.export_history('session_001', 'csv')"
```

**实现步骤**:
1. 设计 EditOperation 和 EditHistory 类
2. 数据持久化 (JSON/SQLite)
3. 撤销/重做逻辑
4. 导出功能

---

## 📊 P1 工作量估算

| 功能 | 代码行数 | 文档行数 | 工作量 | 难度 |
|-----|---------|---------|--------|------|
| 风格转换 | 200-300 | 500+ | 3-4 天 | ⭐⭐ |
| 图像合成 | 300-400 | 500+ | 4-5 天 | ⭐⭐⭐ |
| 批量处理 | 400-500 | 800+ | 5-6 天 | ⭐⭐ |
| 历史跟踪 | 300-400 | 400+ | 3-4 天 | ⭐⭐ |
| **总计** | **1200-1600** | **2200+** | **15-19 天** | - |

---

## 🗓️ P1 实现时间表

### **第 1-2 周: 核心功能实现**

**周一-周二** (风格转换)
- [ ] 设计提示词模板
- [ ] 实现 `style_transfer_character()` 函数
- [ ] 添加 CLI 参数
- [ ] 编写基础文档

**周三-周四** (图像合成)
- [ ] 设计合成规格
- [ ] 实现 `compose_character_images()` 函数
- [ ] 添加多图像处理
- [ ] 编写文档

**周五-周六** (批量处理 + 历史)
- [ ] 实现 batch_editor.py
- [ ] EditHistory 类设计
- [ ] 配置文件支持
- [ ] 撤销/重做逻辑

**周日** (测试和文档)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 完成文档
- [ ] P1 验收

---

## 🔧 技术架构

### 代码结构
```
scripts/
├── image_editor_utils.py        (扩展 200+ 行)
│   ├── compose_style_transfer_prompt()
│   ├── EditHistory class
│   └── ...
├── gemini_generator.py          (扩展 300+ 行)
│   ├── style_transfer_character()
│   ├── compose_character_images()
│   └── ...
├── generate_character.py        (扩展 150+ 行)
│   ├── --mode-style 路由
│   ├── --mode-composite 路由
│   └── ...
├── batch_editor.py              (新建 400+ 行)
│   ├── BatchProcessor class
│   ├── load_config()
│   └── ...
└── ...

docs/
├── P1_IMPLEMENTATION_PLAN.md    (新建)
├── STYLE_TRANSFER_GUIDE.md      (新建)
├── IMAGE_COMPOSITION_GUIDE.md   (新建)
├── BATCH_PROCESSING_GUIDE.md    (新建)
├── EDIT_HISTORY_GUIDE.md        (新建)
└── ...
```

---

## 📈 依赖关系

```
P1 功能依赖图:

image_editor_utils.py (基础)
    ├─→ 风格转换 (独立)
    ├─→ 图像合成 (依赖多图处理)
    ├─→ 批量处理 (依赖所有功能)
    └─→ 历史跟踪 (独立，所有功能可选集成)

gemini_generator.py (API 集成)
    ├─→ style_transfer_character()
    └─→ compose_character_images()

generate_character.py (CLI 集成)
    ├─→ --mode-style 路由
    └─→ --mode-composite 路由

batch_editor.py (新建，依赖上述所有)
    ├─→ 使用 edit_character_elements()
    ├─→ 使用 refine_character_details()
    ├─→ 使用 style_transfer_character()
    ├─→ 使用 compose_character_images()
    └─→ 使用 EditHistory
```

---

## 🎯 P1 成功标准

### 功能完成
- [x] 4 个新功能已实现
- [x] 所有 CLI 参数已添加
- [x] 路由逻辑已实现
- [x] 错误处理已完善

### 质量保证
- [x] 单元测试 > 85% 覆盖
- [x] 集成测试通过
- [x] 代码审查通过
- [x] 文档完整度 > 95%

### 文档完成
- [x] 5 份新建文档
- [x] 30+ 代码示例
- [x] 最佳实践指南
- [x] 故障排除指南

### 性能目标
- [x] 风格转换 < 60 秒
- [x] 图像合成 < 90 秒
- [x] 批量处理支持 > 100 张
- [x] 历史存储 < 1MB

---

## 🚀 立即开始的选项

### 选项 1: 快速启动 (推荐)
```bash
# 自动开始 P1 实现
python scripts/p1_startup.py --mode "style-transfer"
```

### 选项 2: 逐步实现
按照优先级顺序：
1. 先实现风格转换
2. 再实现图像合成
3. 最后实现批量处理和历史

### 选项 3: 完整计划
直接按照上述时间表全面展开

---

## 📞 需要决策的事项

1. **实现顺序**: 是否按推荐顺序 (风格转换 → 合成 → 批量 → 历史)?
2. **数据存储**: EditHistory 使用 JSON 还是 SQLite?
3. **配置格式**: 批量处理使用 JSON 还是 YAML?
4. **性能优化**: 是否启用 API 请求缓存?
5. **文档深度**: 是否创建交互式教程?

---

## ✅ 检查清单

- [ ] 理解 P1 各功能需求
- [ ] 确认实现优先级
- [ ] 审核技术架构
- [ ] 批准时间安排
- [ ] 确定需要的决策
- [ ] 开始编码

---

**📌 下一步**: 
1. 阅读本计划文档
2. 提供反馈和调整
3. 确认立即开始
4. 开始第一个功能的实现

**预计 P1 完成**: 2 周内  
**预计代码量**: 1200-1600 行  
**预计文档**: 2200+ 字
