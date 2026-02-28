#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"  # 获取脚本所在目录的绝对路径
BACKEND_PID_FILE="$PROJECT_ROOT/.backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/.frontend.pid"
CADDY_PID_FILE="$PROJECT_ROOT/.caddy.pid"
LOG_DIR="$PROJECT_ROOT/logs"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 获取局域网 IP
get_wsl_ip() {
    hostname -I | awk '{print $1}'
}

start_backend() {
    if [ -f "$BACKEND_PID_FILE" ] && ps -p $(cat "$BACKEND_PID_FILE") > /dev/null 2>&1; then
        echo "✅ 后端已在运行 (PID: $(cat "$BACKEND_PID_FILE"))"
        return
    fi
    
    echo "🚀 启动后端服务..."
    cd "$PROJECT_ROOT/backend"
    nohup python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    sleep 2
    echo "   ✅ 后端已启动 (PID: $(cat "$BACKEND_PID_FILE"))"
}

start_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ] && ps -p $(cat "$FRONTEND_PID_FILE") > /dev/null 2>&1; then
        echo "✅ 前端已在运行 (PID: $(cat "$FRONTEND_PID_FILE"))"
        return
    fi
    
    echo "🚀 启动前端服务..."
    cd "$PROJECT_ROOT/frontend"
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    sleep 4
    echo "   ✅ 前端已启动 (PID: $(cat "$FRONTEND_PID_FILE"))"
}

stop_backend() {
    if [ -f "$BACKEND_PID_FILE" ]; then
        PID=$(cat "$BACKEND_PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID 2>/dev/null
            rm "$BACKEND_PID_FILE"
            echo "⏹️  后端已停止"
        fi
    fi
}

stop_frontend() {
    if [ -f "$FRONTEND_PID_FILE" ]; then
        PID=$(cat "$FRONTEND_PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID 2>/dev/null
            rm "$FRONTEND_PID_FILE"
            echo "⏹️  前端已停止"
        fi
    fi
}

start_caddy() {
    # 检查 Caddy 是否已安装
    if ! command -v caddy &> /dev/null; then
        echo "⚠️  Caddy 未安装，跳过反向代理"
        echo "   要启用无端口访问 (https://3d.home.lan)，请运行："
        echo "   chmod +x install-caddy.sh && ./install-caddy.sh"
        return
    fi

    if [ -f "$CADDY_PID_FILE" ] && ps -p $(cat "$CADDY_PID_FILE") > /dev/null 2>&1; then
        echo "✅ 反向代理已在运行 (PID: $(cat "$CADDY_PID_FILE"))"
        return
    fi
    
    echo "🚀 启动 Caddy 反向代理..."
    # 需要 sudo 来使用 80/443 端口
    nohup sudo caddy run --config "$PROJECT_ROOT/Caddyfile" > "$LOG_DIR/caddy.log" 2>&1 &
    echo $! > "$CADDY_PID_FILE"
    # Caddy 可能需要一点时间来启动
    sleep 2
    if ps -p $(cat "$CADDY_PID_FILE") > /dev/null 2>&1; then
        echo "   ✅ 反向代理已启动 (PID: $(cat "$CADDY_PID_FILE"))"
    else
        echo "   ⚠️  反向代理启动可能失败（查看日志：tail -f $LOG_DIR/caddy.log）"
    fi
}

stop_caddy() {
    if [ -f "$CADDY_PID_FILE" ]; then
        PID=$(cat "$CADDY_PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            sudo kill $PID 2>/dev/null
            rm "$CADDY_PID_FILE"
            echo "⏹️  反向代理已停止"
        fi
    fi
}

show_status() {
    echo ""
    WSL_IP=$(get_wsl_ip)
    # 尝试获取 Tailscale IP
    TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
    DOMAIN_NAME="${CORTEX3D_DOMAIN:-3d.home.lan}"
    # 检查 Caddy 是否运行
    CADDY_RUNNING=false
    if [ -f "$CADDY_PID_FILE" ] && ps -p $(cat "$CADDY_PID_FILE") > /dev/null 2>&1; then
        CADDY_RUNNING=true
    fi

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          🎉 Cortex3d 开发环境已启动                        ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    
    if [ "$CADDY_RUNNING" = true ]; then
    echo "║ 🚀 无端口访问（推荐 ⭐）：                                  ║"
    echo "║    📱 前端：https://$DOMAIN_NAME/                          ║"
    echo "║    📖 文档：https://$DOMAIN_NAME:8000/docs                ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    fi
    
    echo "║ 🖥️  本地访问（开发）：                                     ║"
    echo "║    📱 前端：http://localhost:5173                          ║"
    echo "║    🔌 API：http://localhost:8000                           ║"
    echo "║    📖 文档：http://localhost:8000/docs                     ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ 🌐 局域网 IP 访问：                                        ║"
    echo "║    📱 前端：http://$WSL_IP:5173                          ║"
    echo "║    🔌 API：http://$WSL_IP:8000                           ║"
    if [ -n "$TS_IP" ]; then
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ 🔗 Tailscale IP 访问：                                     ║"
    echo "║    📱 前端：http://$TS_IP:5173                           ║"
    echo "║    🔌 API：http://$TS_IP:8000                            ║"
    fi
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ 💡 命令：                                                   ║"
    echo "║    ./dev.sh start       - 启动所有服务                     ║"
    echo "║    ./dev.sh stop        - 停止所有服务                     ║"
    echo "║    ./dev.sh restart     - 重启所有服务                     ║"
    echo "║    ./dev.sh status      - 显示状态                         ║"
    if ! command -v caddy &> /dev/null; then
    echo "║    ./install-caddy.sh   - 安装 Caddy 反向代理              ║"
    fi
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
}

status() {
    echo ""
    if [ -f "$BACKEND_PID_FILE" ] && ps -p $(cat "$BACKEND_PID_FILE") > /dev/null 2>&1; then
        echo "✅ 后端：运行中 (PID: $(cat "$BACKEND_PID_FILE"))"
    else
        echo "❌ 后端：已停止"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ] && ps -p $(cat "$FRONTEND_PID_FILE") > /dev/null 2>&1; then
        echo "✅ 前端：运行中 (PID: $(cat "$FRONTEND_PID_FILE"))"
    else
        echo "❌ 前端：已停止"
    fi
    echo ""
}

case "$1" in
    start)
        source "$PROJECT_ROOT/.venv/bin/activate"
        cd "$PROJECT_ROOT"
        start_backend
        start_frontend
        start_caddy
        show_status
        ;;
    stop)
        stop_backend
        stop_frontend
        stop_caddy
        ;;
    restart)
        stop_backend
        stop_frontend
        stop_caddy
        sleep 1
        source "$PROJECT_ROOT/.venv/bin/activate"
        cd "$PROJECT_ROOT"
        start_backend
        start_frontend
        start_caddy
        show_status
        ;;
    status)
        status
        ;;
    *)
        source "$PROJECT_ROOT/.venv/bin/activate"
        cd "$PROJECT_ROOT"
        start_backend
        start_frontend
        show_status
        ;;
esac
