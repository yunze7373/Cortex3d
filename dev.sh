#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"  # 获取脚本所在目录的绝对路径
BACKEND_PID_FILE="$PROJECT_ROOT/.backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/.frontend.pid"
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

show_status() {
    echo ""
    WSL_IP=$(get_wsl_ip)
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          🎉 Cortex3d 开发环境已启动                        ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ 🖥️  本地访问：                                              ║"
    echo "║    📱 前端：http://localhost:5173                           ║"
    echo "║    🔌 API：http://localhost:8000                            ║"
    echo "║    📖 文档：http://localhost:8000/docs                      ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ 🌐 局域网访问（其他设备）：                                ║"
    echo "║    📱 前端：http://$WSL_IP:5173                          ║"
    echo "║    🔌 API：http://$WSL_IP:8000                           ║"
    echo "║    📖 文档：http://$WSL_IP:8000/docs                     ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ ✨ 已启用智能 API 地址检测：                               ║"
    echo "║    •前端会自动检测访问地址并连接对应后端                    ║"
    echo "║    •无需手工配置即可支持本地和局域网访问                    ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ 📋 日志文件：                                               ║"
    echo "║    tail -f $LOG_DIR/backend.log                     ║"
    echo "║    tail -f $LOG_DIR/frontend.log                    ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ 💡 命令：                                                   ║"
    echo "║    ./dev.sh start   - 启动                                  ║"
    echo "║    ./dev.sh stop    - 停止                                  ║"
    echo "║    ./dev.sh restart - 重启                                  ║"
    echo "║    ./dev.sh status  - 状态                                  ║"
    echo "╠════════════════════════════════════════════════════════════╣"
    echo "║ ❓ 无法访问？查看日志：                                      ║"
    echo "║    tail -f $LOG_DIR/backend.log                     ║"
    echo "║    tail -f $LOG_DIR/frontend.log                    ║"
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
        show_status
        ;;
    stop)
        stop_backend
        stop_frontend
        ;;
    restart)
        stop_backend
        stop_frontend
        sleep 1
        source "$PROJECT_ROOT/.venv/bin/activate"
        cd "$PROJECT_ROOT"
        start_backend
        start_frontend
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
