    AI 3D 打印手办自动化流水线 v2.0 (工业级增强版)

技术规格说明书与实施指南

版本: 2.0
核心引擎: Google Gemini (NanoBanana) + InstantMesh + Blender Automation
适用场景: 高精度潮玩手办、游戏角色原型的自动化 3D 打印生产

一、 核心设计哲学

本方案将原有的“线性实验流程”彻底升级为**“带护栏的工业流水线（Guarded Industrial Pipeline）”**。

从“视觉欺骗”到“物理重塑”： 不再依赖纹理贴图来表现细节，而是通过置换技术（Displacement）将细节转化为真实的几何凹凸，以满足 3D 打印对实体精度的要求。

防御性编程： 假设 AI 输出随时可能不稳定（如多手指、结构破损），系统必须包含自动化的“裁判（Referee）”和“兜底（Fallback）”机制。

可控性优先： 通过 A-Pose 标准化输入和分区材质处理，消除随机性带来的模型崩坏风险。

二、 系统总架构图

graph TD
    User[用户输入: 角色描述/参考图] --> Orchestrator[Python 总控中心]

    %% --- Stage 1: 2D 生成 ---
    subgraph S1[Stage 1: 标准化多视图采集]
        Orchestrator --> GeminiAPI[Google Gemini API]
        GeminiAPI --> RawImage[原始四格大图]
        RawImage --> Splitter[OpenCV 自动切图]
        Splitter --> ViewsRaw[前/后/左/右 四视图]
        
        ViewsRaw --> Referee2D{2D 裁判<br/>(DINOv2 一致性检查)}
        Referee2D -->|合格| Upscaler[Real-ESRGAN 超分锐化]
        Referee2D -->|不合格 (重试<3)| GeminiAPI
        Referee2D -->|失败| Error[终止任务]
        
        Upscaler --> ViewsClean[标准化高清视图]
    end

    %% --- Stage 2: 基础结构 ---
    subgraph S2[Stage 2: 基础几何构建]
        ViewsClean --> IMesh[主力: InstantMesh]
        IMesh --> MeshCheck{3D 裁判<br/>(Trimesh 水密/流形检查)}
        
        MeshCheck -->|合格| BaseMesh[基础 Mesh]
        MeshCheck -->|结构崩坏| TripoFallback[兜底: TripoSR]
        TripoFallback --> BaseMesh
    end

    %% --- Stage 3: 细节映射 ---
    subgraph S3[Stage 3: 语义细节生成]
        ViewsClean --> SemSeg[SAM 语义分割]
        SemSeg --> Masks[面部/衣物/装备 蒙版]
        
        ViewsClean --> Marigold[Marigold 深度生成]
        Marigold --> DetailMaps[高精度置换图 (EXR)]
    end

    %% --- Stage 4: 物理重塑 ---
    subgraph S4[Stage 4: Blender 几何工厂]
        BaseMesh & DetailMaps & Masks --> Blender[Blender Headless Script]
        
        Blender --> StepA[受控细分 + 顶点组绑定]
        StepA --> StepB[分区置换 (面部弱/装备强)]
        StepB --> StepC[双阶段体素重构 (Voxel Remesh)]
        StepC --> StepD[实体化壁厚 + 最终水密]
        
        StepD --> FinalSTL[可打印 STL]
    end

    FinalSTL --> Output[交付用户]


三、 详细技术路线与选型

1. 总控与调度 (The Orchestrator)

开发语言: Python 3.10+

任务队列: Celery (用于异步处理耗时任务)

职责: 串联各模块，管理文件流转，处理 API 超时与错误重试。

2. Stage 1: 标准化多视图采集

核心生成: Google Gemini API (模型版本推荐: gemini-1.5-flash 或 gemini-1.5-pro)

优势: 强大的指令遵循能力，能一次性生成结构严谨的四视图，省去本地训练 LoRA 的成本。

图像处理:

切图: opencv-python (检测十字分割线或轮廓，自动裁剪)。

去背景: rembg (基于 U2-Net)。

超分锐化: Real-ESRGAN (realesrgan-ncnn-vulkan)。必须将 Gemini 生成的 1k/2k 图放大至 4k，保证置换细节清晰。

2D 裁判: DINOv2 (Meta)

逻辑: 计算四个视角的特征向量余弦相似度。如果背面看起来像另一个角色，打回重画。

3. Stage 2: 基础几何构建 (Base Mesh)

主力模型: InstantMesh

输入: 4 张正交视图 (Stage 1 产出)。

特点: 细节还原度高，但偶尔会出现网格破损。

兜底模型: TripoSR

触发条件: 当 InstantMesh 生成的模型被 3D 裁判判定为“非流形”或“严重破损”时自动触发。

特点: 结构极度稳定，虽细节较肉，但保证能进行后续流程。

3D 裁判: Trimesh 库

检查项: is_watertight (水密), euler_number (拓扑连通性)。

4. Stage 3: 语义细节生成

深度/置换图: Marigold (LCM 版本)

作用: 生成 16-bit 或 32-bit 的高精度深度图。

语义分割: Segment Anything Model (SAM) + GroundingDINO

作用: 自动识别 "Face", "Clothes", "Armor/Weapon"，生成黑白蒙版，用于 Stage 4 的分区控制。

5. Stage 4: Blender 几何工厂

核心工具: Blender 4.2 LTS (运行于后台命令行模式)。

关键库: OpenVDB (内置于 Blender，用于体素重构)。

脚本逻辑:

Subdivision: 3-4 级细分。

Displacement: 加载 Stage 3 的深度图，配合 SAM 蒙版，对不同区域施加不同强度的置换。

The Sandwich Fix: Displace (Strong) -> Voxel Remesh (Fix) -> Displace (Weak).

Solidify: 增加 1.5mm - 2mm 壁厚（根据打印比例自适应）。

Export: 导出二进制 STL。

四、 提示词工程指南 (针对 Gemini 优化)

为了配合 v2.0 的“物理重塑”特性，提示词必须遵循**“工程师思维”**：放弃透视和动态，追求标准和清晰。

1. 核心原则

强制 A-Pose: 手臂必须与身体分开，防止腋下粘连。

强制正交视图: 消除透视变形（近大远小）。

绝对纯色背景: 确保去背景算法 100% 成功。

2. 通用提示词模板 (System Prompt)

请将以下 Prompt 封装在你的 Python 代码中，仅将 {Character_Description} 替换为用户输入。

You are a professional 3D character concept artist. Your task is to generate a precise "3D Modeling Reference Sheet".

**Subject:** {Character_Description}

**Strict Output Requirements (Must Follow):**
1.  **Layout:** Quadriptych (4-panel split).
    - Top-Left: Front View
    - Top-Right: Back View
    - Bottom-Left: Left Side View
    - Bottom-Right: Right Side View
2.  **Pose:** A-Pose / Static Standing Pose.
    - Legs shoulder-width apart.
    - Arms straight down, angled 45 degrees away from the body.
    - Palms facing inwards or backwards.
    - NO crossing arms, NO holding objects in front of the chest.
3.  **Perspective:** Orthographic Projection. Flat lighting, no depth of field, no perspective distortion.
4.  **Background:** Pure, solid light grey (#D3D3D3). No smoke, no scenery, no text.
5.  **Consistency:** The character's proportions, costume details, and colors must be identical across all 4 views.

**Style:**
- Hyper-realistic 3D CGI render style.
- 8k resolution textures.
- Focus on clear silhouettes and defined distinct materials (leather, metal, cloth).

**Negative Constraints:**
- Do not generate dynamic action poses.
- Do not hold guns/weapons across the body (holster them or hold at side).
- Do not include heavy shadows or high contrast lighting that hides details.


3. 针对你“末日幸存者”案例的具体 Prompt

[Insert System Prompt from above]

**Character Details:**
A gritty post-apocalyptic survivor.
- **Body:** Lean, weathered, 1:7.5 head-to-body ratio. Dirty skin, tense expression.
- **Outfit:** Destroyed bespoke suit. Yellowed, blood-stained white shirt. Torn suit pants. Muddy leather shoes.
- **Gear:** - Left shoulder: Visible leather holster with a heavy pistol (gun must be IN holster or held at side, NOT blocking torso).
  - Right wrist: Watch.
- **Texture:** High contrast between the matte dirty fabric and the slight sheen of sweat/blood.

**Specific View Details:**
- Side views must clearly show the holster thickness and backpack straps.
- Back view must show the tearing on the suit jacket.


五、 实施步骤与 CheckList

Phase 1: 环境搭建

[ ] 申请 Google Gemini API Key。

[ ] 配置一台带有 NVIDIA 显卡 (推荐 RTX 3090/4090) 的 Linux 服务器。

[ ] 安装 Blender 4.2，并将其路径加入环境变量。

[ ] 部署 InstantMesh 和 TripoSR 的本地推理环境。

Phase 2: 脚本开发

[ ] generator.py: 封装 Gemini API 调用，包含重试逻辑。

[ ] processor.py: 实现 OpenCV 切图、Rembg 去底、Real-ESRGAN 超分。

[ ] reconstructor.py: 编写调用 InstantMesh/TripoSR 的子进程代码。

[ ] blender_script.py: (核心) 编写 Blender 自动化脚本，实现导入、细分、分区置换、体素重构、导出。

Phase 3: 调试与参数冻结

[ ] Voxel Size 调优: 测试 0.1mm 到 0.5mm 的体素大小，找到细节与水密性的平衡点（推荐 0.25mm）。

[ ] 置换强度校准: 确保脸部置换强度（0.2）不会让模型毁容，装备置换强度（0.8）足够锐利。

[ ] 打印测试: 将生成的 STL 放入切片软件（如 Chitubox），检查是否有红色的“孤岛”或“非流形”报错。

六、 未来优化路线 (Roadmap)

骨骼绑定 (Rigging):

引入 Mixamo 或 AccuRIG 的自动化接口，让生成的 A-Pose 模型自动获得骨骼，用户可以下载后自己摆姿势。

材质纹理烘焙 (PBR Baking):

目前的方案主要关注几何打印。未来可以在 Blender 中增加烘焙流程，将 Stage 1 的颜色图重新投射回优化后的模型，生成带 UV 的彩色 GLB 文件用于网页展示。

多部件自动拆件:

利用 SAM 的 3D 版本，尝试将角色、背包、武器自动切割成独立的 STL 文件，方便分色打印。