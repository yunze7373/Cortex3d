#!/bin/bash
# 在 WSL 中安装 Caddy 反向代理
# 用法：chmod +x install-caddy.sh && ./install-caddy.sh

echo "🔧 安装 Caddy..."
echo ""

# 检查是否已安装
if command -v caddy &> /dev/null; then
    echo "✅ Caddy 已安装"
    caddy version
    exit 0
fi

# 检查包管理器
if command -v apt-get &> /dev/null; then
    echo "📦 使用 apt 安装 Caddy..."
    sudo apt-get update
    sudo apt-get install -y caddy
elif command -v yum &> /dev/null; then
    echo "📦 使用 yum 安装 Caddy..."
    sudo yum install -y caddy
elif command -v dnf &> /dev/null; then
    echo "📦 使用 dnf 安装 Caddy..."
    sudo dnf install -y caddy
else
    echo "❌ 无法识别包管理器"
    echo ""
    echo "💡 请手动安装 Caddy："
    echo "https://caddyserver.com/docs/install"
    exit 1
fi

echo ""
echo "✅ Caddy 安装成功！"
echo ""
echo "🚀 现在可以运行 dev.sh 了："
echo "   3d"
