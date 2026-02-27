# ComfyUI-Cortex3d 全面审计报告

> 审计时间: 2025-01  
> 审计范围: `ComfyUI-Cortex3d/` 全部 45 个文件  
> 对照文档: `docs/COMFYUI_MIGRATION_PLAN.md` (1415 行)  
> **修复更新: 2025-01 — 全部 CRITICAL + HIGH 问题已修复**

---

## 一、总体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **架构设计** | ⭐⭐⭐⭐⭐ | 分层清晰 (Node → Adapter → Bridge)，解耦合理 |
| **节点完整性** | ⭐⭐⭐⭐⭐ | 33/33 节点全部实现，INPUT_TYPES/RETURN_TYPES 完整 |
| **适配器层** | ⭐⭐⭐⭐⭐ | 12/12 适配器全部实现，懒惰导入 + fallback + ResultCache |
| **类型系统** | ⭐⭐⭐⭐⭐ | 4 个自定义类型完备，序列化/反序列化齐全 |
| **桥接层** | ⭐⭐⭐⭐ | Docker/HTTP/File 三种桥接完整 |
| **前端扩展** | ⭐⭐⭐⭐ | Three.js 3D 预览面板、节点着色、自定义 Widget |
| **部署配置** | ⭐⭐⭐⭐⭐ | Dockerfile + compose.yml + entrypoint + install.py 完整 |
| **错误处理** | ⭐⭐⭐⭐⭐ | node_guard 全覆盖、ResultCache 全集成、ProgressReporter 全覆盖 |
| **文档** | ⭐⭐⭐⭐ | README 详尽，但含少量失实描述 |

**总体完成度: ~97%** — 全部 CRITICAL 和 HIGH 问题已修复，仅余少量 MODERATE/MINOR。

---

## 二、严重问题 (CRITICAL) — 必须修复

### C1. `node_guard` 装饰器未应用于任何节点 — ✅ 已修复

**文件:** `utils/errors.py` 已实现 `node_guard()` 装饰器  
**问题:** 33 个节点中没有任何一个使用了 `@node_guard()`  
**修复:** 已在全部 7 个 node 文件的 33 个 `execute()` 方法上添加 `@node_guard()` 装饰器  
**涉及文件:** prompt_nodes.py, generation_nodes.py, process_nodes.py, reconstruction_nodes.py, postprocess_nodes.py, edit_nodes.py, utility_nodes.py

---

### C2. `ResultCache` 未集成到任何适配器 — ✅ 已修复

**文件:** `adapters/cache.py` 已实现完整缓存系统  
**问题:** 5 个 3D 重建适配器均未检查缓存  
**修复:** 已在全部 5 个重建适配器中集成 ResultCache（含 hunyuan3d 的两个方法各有独立缓存）  
**涉及文件:** instantmesh_adapter.py, triposr_adapter.py, trellis2_adapter.py, hunyuan3d_adapter.py, ultrashape_adapter.py

---

### C3. `ProgressReporter` 未集成 — ✅ 已修复

**文件:** `utils/errors.py` 已实现 `ProgressReporter`  
**问题:** 3D 重建耗时 2-30 分钟，但没有任何节点向前端推送进度  
**修复:** 已在全部 6 个 3D 重建节点的 `execute()` 方法中集成 ProgressReporter（2 步：进行中 → 完成）  
**涉及文件:** reconstruction_nodes.py

---

### C4. `install.py` 缺失 — ✅ 已修复

**问题:** ComfyUI 自动安装钩子 `install.py` 不存在  
**修复:** 已创建 `install.py`，自动运行 `pip install -r requirements.txt`

---

### C5. TripoSR 适配器有严重 Bug — 双重执行 — ✅ 已修复

**文件:** `adapters/triposr_adapter.py`  
**问题:** exec_script + subprocess.run 双重执行  
**修复:** 移除 `exec_script` 调用，只保留 `subprocess.run` 方式（与其他适配器一致）

---

## 三、高优先级问题 (HIGH)

### H1. `view_mode` 值不匹配 — ✅ 已修复

**问题:** 节点使用 `"standard_4"` 但 config.py 期望 `"4-view"`  
**修复:** 在 `PromptAdapter` 添加 `_VIEW_MODE_MAP` 字典 + `_map_view_mode()` 方法，在 4 个方法中自动映射

---

### H2. CompositePromptBuilder 节点↔适配器接口不匹配 — ✅ 已修复

**问题:** 节点传 `character_description + scene_description`，适配器期望 `instruction + composite_type`  
**修复:** 节点现在组合字段为 `instruction`，映射 view_mode 到 num_images，传递 `composite_type="character_scene"`

---

### H3. NegativePrompt 节点↔适配器接口不匹配 — ✅ 已修复

**问题:** 节点传 `style` 字符串，适配器期望 `categories` 列表  
**修复:** 添加 `_STYLE_CATEGORIES` 映射表，将 style 字符串转为分类列表后调用 `get_negative_prompt(categories=...)`

---

### H4. 工作流 JSON 链路错误 — ✅ 已修复

**文件:** `workflows/text_to_3d_basic.json`  
**问题:** Link [3] 将 NegativePrompt 输出连接到 GeminiGenerator 的 `input[0]`(prompt)，与 Link[1] 冲突  
**修复:** 在 GeminiGenerator 节点 inputs 数组添加 `negative_prompt` 输入 (slot 2)，Link[3] 目标改为 slot 2

---

### H5. DockerManager 缺少 `clear_cache` 动作 — ✅ 已修复

**文件:** `nodes/utility_nodes.py`  
**修复:** ACTIONS 列表添加 `"clear_cache"`，execute 方法添加 `clear_all_caches()` 调用分支

---

## 四、中等问题 (MODERATE)

### M1. Gemini 模型名称不一致
- **节点 widget:** `gemini-2.0-flash-exp`, `gemini-1.5-pro`, `gemini-1.5-flash`
- **适配器默认:** `gemini-3-pro-image-preview`
- **影响:** 节点传值覆盖默认值所以能工作，但默认值过时

### M2. Web 前端依赖外部 CDN
- Three.js 从 `cdn.jsdelivr.net` 加载
- 离线/内网环境无法使用 3D 预览

### M3. Edit 节点使用 Qwen 而非 Gemini
- 迁移计划规定 ClothingExtractor/WardrobeChange 使用 Gemini
- 实际使用 QwenAdapter
- 功能可用但与设计文档不一致

### M4. `configs/docker_services.yaml` 仅作文档用
- YAML 配置详尽（92行），但没有任何代码读取它
- 适配器硬编码服务名，应改为从 YAML 加载

### M5. Trellis2 多视角降级未告知
```python
def reconstruct_multiview(self, image_paths, **kwargs):
    return Trellis2Adapter.reconstruct(image_path=image_paths[0], **kwargs)
```
- 静默丢弃除第一张以外的所有图像，应至少 log warning

---

## 五、次要问题 (MINOR)

| 编号 | 说明 |
|------|------|
| L1 | 包缺少 `__version__` 版本号 |
| L2 | 缺少 `.gitignore` 排除缓存/输出目录 |
| L3 | `configs/quality_presets.yaml` 未创建（计划有，实际硬编码在 `types/config.py`） |
| L4 | README 描述 "35+ 工业级 Python 脚本" 但实际是 "33 个节点" — 数字混淆 |
| L5 | AiProxyGenerator 节点模型列表包含 `stable-diffusion-3.5` 但 AiProxy 未必支持 |

---

## 六、修复实施状态

| 优先级 | 编号 | 修复内容 | 状态 |
|--------|------|----------|------|
| 🔴 P0 | C1 | 应用 node_guard 到全部 33 个节点 | ✅ 已完成 |
| 🔴 P0 | C2 | 集成 ResultCache 到 5 个重建适配器 | ✅ 已完成 |
| 🔴 P0 | C3 | 集成 ProgressReporter 到 6 个重建节点 | ✅ 已完成 |
| 🔴 P0 | C4 | 创建 install.py | ✅ 已完成 |
| 🔴 P0 | C5 | 修复 TripoSR 适配器双重执行 Bug | ✅ 已完成 |
| 🟠 P1 | H1 | 修复 view_mode 映射 | ✅ 已完成 |
| 🟠 P1 | H2 | 修复 CompositePromptBuilder 接口 | ✅ 已完成 |
| 🟠 P1 | H3 | 修复 NegativePrompt 接口 | ✅ 已完成 |
| 🟠 P1 | H4 | 修复工作流 JSON 链路 | ✅ 已完成 |
| 🟠 P1 | H5 | DockerManager 添加 clear_cache | ✅ 已完成 |
| 🟢 P3 | M1-M5 | 中等问题（可后续处理） | ⏳ 待定 |
| ⚪ P4 | L1-L5 | 次要问题 | ⏳ 待定 |

---

## 七、与迁移计划的差异摘要

| 项目 | 迁移计划 | 实际实现 | 评估 |
|------|----------|----------|------|
| 节点总数 | 33 | 33 | ✅ 一致 |
| ImagePreview | 有 | 改为 ImageListMerge | ⚠️ 功能变更（可接受） |
| install.py | 有 | ✅ 已创建 | ✅ 已修复 |
| quality_presets.yaml | 有 | 硬编码在 config.py | ⚠️ 可接受 |
| Gemini 模型 | gemini-3-pro | gemini-2.0-flash-exp | ⚠️ 节点已更新，适配器默认值过时 |
| Edit 节点后端 | Gemini API | Qwen API | ⚠️ 实际可能更好，需更新文档 |
| view_mode 格式 | "4"/"6"/"8" | "standard_4" 经 _VIEW_MODE_MAP 映射 | ✅ 已修复 |
| node_guard | 全部应用 | ✅ 33/33 节点已应用 | ✅ 已修复 |
| ResultCache | 自动启用 | ✅ 5/5 重建适配器已集成 | ✅ 已修复 |
| ProgressReporter | 长任务使用 | ✅ 6/6 重建节点已集成 | ✅ 已修复 |
