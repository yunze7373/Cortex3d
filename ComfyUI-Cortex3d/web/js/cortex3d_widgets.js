/**
 * ComfyUI-Cortex3d — UI 扩展入口
 * 注册自定义 Widget、节点标注，以及 3D 预览面板。
 */
import { app }         from "../../scripts/app.js";
import { api }         from "../../scripts/api.js";

// ── 颜色主题（与 cortex3d.css 中的变量对应）──────────────────────────────────
const THEME = {
    prompt:   "#1a3a5c",
    generate: "#1a4a2a",
    process:  "#3a2a1a",
    recon:    "#2a1a4a",
    post:     "#4a2a1a",
    edit:     "#4a1a3a",
    utility:  "#2a2a2a",
};

// ── 节点分类 → 颜色映射 ────────────────────────────────────────────────────
const NODE_COLORS = {
    "Cortex3d/Prompt":      THEME.prompt,
    "Cortex3d/Generate":    THEME.generate,
    "Cortex3d/Process":     THEME.process,
    "Cortex3d/3D":          THEME.recon,
    "Cortex3d/PostProcess": THEME.post,
    "Cortex3d/Edit":        THEME.edit,
    "Cortex3d/Utility":     THEME.utility,
};

// ── 自定义数据类型显示标签 ────────────────────────────────────────────────
const TYPE_LABELS = {
    "CORTEX_MESH":        "🧊 Mesh",
    "CORTEX_VIEW_CONFIG": "🎥 ViewCfg",
    "CORTEX_CONFIG":      "⚙️ Config",
    "CORTEX_CONTROL":     "🕹️ Control",
};

/**
 * 注册 ComfyUI 应用扩展
 */
app.registerExtension({
    name: "Cortex3d.Core",

    // ── 节点定义回调 ─────────────────────────────────────────────────────
    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        const category = nodeData.category || "";
        const color = NODE_COLORS[category];
        if (!color) return;

        const onDrawForeground = nodeType.prototype.onDrawForeground;
        nodeType.prototype.onDrawForeground = function(ctx) {
            if (onDrawForeground) onDrawForeground.apply(this, arguments);
            // 绘制类别标签
            const label = category.split("/").pop();
            ctx.save();
            ctx.fillStyle = "rgba(255,255,255,0.15)";
            ctx.font = "10px monospace";
            ctx.fillText(`[${label}]`, 6, -4);
            ctx.restore();
        };

        // 设置节点颜色
        if (!nodeType.prototype._cortex3d_colored) {
            nodeType.prototype._cortex3d_colored = true;
            const origDrawTitle = nodeType.prototype.drawTitle;
            nodeType.prototype.drawTitle = function(ctx) {
                this.bgcolor = color;
                if (origDrawTitle) return origDrawTitle.apply(this, arguments);
            };
        }
    },

    // ── 节点创建回调 ─────────────────────────────────────────────────────
    async nodeCreated(node) {
        // 为 IMAGE 输出的预览连接线着色
        if (node.outputs) {
            for (const output of node.outputs) {
                if (TYPE_LABELS[output.type]) {
                    output.label = TYPE_LABELS[output.type];
                }
            }
        }
        // 为 CORTEX_MESH 输出添加"查看3D"按钮
        if (node.outputs && node.outputs.some(o => o.type === "CORTEX_MESH")) {
            node.addWidget("button", "🧊 预览 3D", null, () => {
                openMeshPreview(node);
            });
        }
    },
});

// ── 3D 预览面板 ──────────────────────────────────────────────────────────────
function openMeshPreview(node) {
    const existingPanel = document.getElementById("cortex3d-preview-panel");
    if (existingPanel) existingPanel.remove();

    const panel = document.createElement("div");
    panel.id = "cortex3d-preview-panel";
    panel.className = "cortex3d-panel";
    panel.innerHTML = `
        <div class="cortex3d-panel-header">
            <span>🧊 Cortex3d — 3D 预览</span>
            <button class="cortex3d-close" onclick="this.closest('#cortex3d-preview-panel').remove()">✕</button>
        </div>
        <div class="cortex3d-panel-body">
            <canvas id="cortex3d-canvas" width="480" height="360"></canvas>
            <div class="cortex3d-panel-info" id="cortex3d-info">等待网格数据...</div>
        </div>
        <div class="cortex3d-panel-footer">
            <small>拖拽旋转 · 滚轮缩放 · 右键平移</small>
        </div>`;
    document.body.appendChild(panel);

    // 加载 Three.js 渲染器
    loadMeshPreviewRenderer(panel);
}

async function loadMeshPreviewRenderer(panel) {
    const script = document.createElement("script");
    script.src = "/extensions/ComfyUI-Cortex3d/js/mesh_preview.js";
    script.type = "module";
    script.onload = () => {
        if (window.CortexMeshPreview) {
            window.CortexMeshPreview.init("cortex3d-canvas");
        }
    };
    document.head.appendChild(script);
}
