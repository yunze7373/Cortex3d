#!/bin/bash

# Cortex3d 开发环境一键配置脚本

PROJECT_ROOT="$(dirname "$0")"
BASHRC_FILE="$HOME/.bashrc"
CONFIG_MARKER="# Cortex3d Development Environment"

echo "🚀 配置 Cortex3d 开发环境..."
echo ""

# 1. 给 dev.sh 赋予执行权限
echo "✅ 设置 dev.sh 执行权限..."
chmod +x "$PROJECT_ROOT/dev.sh"

# 2. 检查并重建虚拟环境
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "✅ 创建 Python 虚拟环境..."
    cd "$PROJECT_ROOT"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -q -r requirements.txt
    echo "   ✅ 虚拟环境已创建并安装依赖"
else
    echo "✅ 虚拟环境已存在"
fi

# 3. 检查前端依赖
if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
    echo "✅ 安装前端依赖..."
    cd "$PROJECT_ROOT/frontend"
    npm install -q
    echo "   ✅ 前端依赖已安装"
else
    echo "✅ 前端依赖已存在"
fi

# 4. 添加 bash 别名（如果还没添加）
if ! grep -q "$CONFIG_MARKER" "$BASHRC_FILE"; then
    echo "✅ 添加 bash 别名到 ~/.bashrc..."
    cat >> "$BASHRC_FILE" << 'EOF'

# Cortex3d Development Environment
alias 3d='source ~/projects/cortex3d/.venv/bin/activate && cd ~/projects/cortex3d && ./dev.sh start'
alias 3d-stop='~/projects/cortex3d/dev.sh stop'
alias 3d-restart='~/projects/cortex3d/dev.sh restart'
alias 3d-status='~/projects/cortex3d/dev.sh status'
EOF
    echo "   ✅ 别名已添加，运行 'source ~/.bashrc' 以激活"
else
    echo "✅ bash 别名已存在"
fi

# 5. 创建日志目录
mkdir -p "$PROJECT_ROOT/logs"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       ✨ Cortex3d 开发环境配置完成！                       ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ 📝 后续步骤：                                               ║"
echo "║                                                            ║"
echo "║ 1️⃣  激活 bash 别名：                                        ║"
echo "║    source ~/.bashrc                                        ║"
echo "║                                                            ║"
echo "║ 2️⃣  一键启动前端 + 后端：                                    ║"
echo "║    3d                                                      ║"
echo "║                                                            ║"
echo "║ 3️⃣  访问应用：                                              ║"
echo "║    📱 http://localhost:5173  (本地)                         ║"
echo "║    🌐 http://172.28.124.41:5173  (局域网)                   ║"
echo "║                                                            ║"
echo "║ 4️⃣  停止/重启：                                             ║"
echo "║    3d-stop     停止                                         ║"
echo "║    3d-restart  重启                                         ║"
echo "║    3d-status   查看状态                                     ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║ 💡 提示：                                                   ║"
echo "║    - 进入 ~/projects/cortex3d 后，bash 会自动识别 3d 别名   ║"
echo "║    - 首次使用需要运行 source ~/.bashrc 激活别名             ║"
echo "║    - 后续再进入 WSL 时直接运行 3d 即可                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
