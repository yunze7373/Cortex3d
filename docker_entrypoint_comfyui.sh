#!/bin/bash
set -e

COMFYUI_DIR="${COMFYUI_DIR:-/app/ComfyUI}"
CUSTOM_NODES="${COMFYUI_DIR}/custom_nodes"
CORTEX3D_SRC="${CORTEX3D_WORKSPACE:-/workspace}/ComfyUI-Cortex3d"

# ── 软链接 Cortex3d 节点包 ────────────────────────────────────────────────
mkdir -p "${CUSTOM_NODES}"
if [ ! -L "${CUSTOM_NODES}/ComfyUI-Cortex3d" ]; then
    ln -s "${CORTEX3D_SRC}" "${CUSTOM_NODES}/ComfyUI-Cortex3d"
    echo "[cortex3d] Linked: ${CORTEX3D_SRC} → ${CUSTOM_NODES}/ComfyUI-Cortex3d"
fi

# ── 拷贝工作流模板 ────────────────────────────────────────────────────────
WORKFLOW_DST="${COMFYUI_DIR}/user/default/workflows"
mkdir -p "${WORKFLOW_DST}"
cp -n "${CORTEX3D_SRC}"/workflows/*.json "${WORKFLOW_DST}/" 2>/dev/null || true

# ── 等待关键 GPU 服务就绪（可选）─────────────────────────────────────────
wait_for() {
    local name=$1 url=$2 max_tries=${3:-30}
    echo "[cortex3d] Waiting for ${name} (${url})..."
    for i in $(seq 1 ${max_tries}); do
        if curl -sf --max-time 3 "${url}" > /dev/null 2>&1; then
            echo "[cortex3d] ${name} ready ✓"
            return 0
        fi
        sleep 2
    done
    echo "[cortex3d] WARN: ${name} not ready after ${max_tries} attempts, continuing anyway"
}

# ZImage 和 Qwen 服务启动较慢，等待健康检查
[ -n "${WAIT_FOR_ZIMAGE}" ] && wait_for "zimage" "http://zimage:8199/health"
[ -n "${WAIT_FOR_QWEN}" ]   && wait_for "qwen" "http://qwen-image-edit:8200/health"

# ── 启动 ComfyUI ─────────────────────────────────────────────────────────
cd "${COMFYUI_DIR}"
exec python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --enable-cors-header "*" \
    ${COMFYUI_EXTRA_ARGS:-}
