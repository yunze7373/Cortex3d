#!/bin/bash
# Cortex3d Docker 清理脚本
# 用于释放 WSL 磁盘空间

set -e

echo "======================================"
echo "Cortex3d Docker 清理工具"
echo "======================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 显示当前空间使用
show_space() {
    echo -e "${YELLOW}📊 当前 Docker 空间使用:${NC}"
    echo ""
    docker system df
    echo ""
}

# 清理函数
clean_containers() {
    echo -e "${GREEN}🧹 清理停止的容器...${NC}"
    docker container prune -f
    echo ""
}

clean_images() {
    echo -e "${GREEN}🧹 清理未使用的镜像...${NC}"
    docker image prune -a -f
    echo ""
}

clean_build_cache() {
    echo -e "${GREEN}🧹 清理构建缓存...${NC}"
    docker builder prune -a -f
    echo ""
}

clean_volumes() {
    echo -e "${YELLOW}⚠️  清理卷 (保留 hf-cache)...${NC}"
    docker volume prune -f --filter "label!=com.docker.compose.volume=hf-cache"
    echo ""
}

clean_networks() {
    echo -e "${GREEN}🧹 清理未使用的网络...${NC}"
    docker network prune -f
    echo ""
}

# 主菜单
show_menu() {
    echo "请选择清理选项:"
    echo ""
    echo "1) 查看空间使用"
    echo "2) 清理停止的容器"
    echo "3) 清理未使用的镜像"
    echo "4) 清理构建缓存 (推荐)"
    echo "5) 清理未使用的卷"
    echo "6) 完全清理 (保留 HF 缓存)"
    echo "7) 危险：清理所有 (包括模型缓存)"
    echo "8) 显示 WSL 压缩指令"
    echo "0) 退出"
    echo ""
}

# 完全清理
full_clean() {
    echo -e "${YELLOW}⚠️  即将执行完全清理...${NC}"
    echo "这将清理:"
    echo "  - 停止的容器"
    echo "  - 未使用的镜像"
    echo "  - 构建缓存"
    echo "  - 未使用的卷 (保留 hf-cache)"
    echo "  - 未使用的网络"
    echo ""
    read -p "确认继续? (y/N): " confirm
    
    if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
        show_space
        clean_containers
        clean_images
        clean_build_cache
        clean_volumes
        clean_networks
        echo -e "${GREEN}✅ 完全清理完成！${NC}"
        echo ""
        show_space
    else
        echo "已取消"
    fi
}

# 危险清理
dangerous_clean() {
    echo -e "${RED}⚠️  危险操作！${NC}"
    echo "这将删除 ${RED}所有${NC} Docker 数据，包括:"
    echo "  - 所有容器"
    echo "  - 所有镜像"
    echo "  - 所有构建缓存"
    echo "  - 所有卷 (${RED}包括 Hugging Face 模型缓存${NC})"
    echo "  - 所有网络"
    echo ""
    echo -e "${YELLOW}删除模型缓存后需要重新下载 30-50GB 数据！${NC}"
    echo ""
    read -p "输入 'DELETE' 确认: " confirm
    
    if [[ $confirm == "DELETE" ]]; then
        echo -e "${RED}开始危险清理...${NC}"
        docker system prune -a --volumes -f
        echo -e "${GREEN}✅ 危险清理完成！${NC}"
        echo -e "${YELLOW}提示: 记得在 PowerShell 中运行 WSL 压缩！${NC}"
        show_space
    else
        echo "已取消"
    fi
}

# WSL 压缩指令
show_wsl_compact() {
    echo -e "${YELLOW}💡 WSL 磁盘压缩步骤:${NC}"
    echo ""
    echo "在 Windows PowerShell (管理员) 中运行:"
    echo ""
    echo -e "${GREEN}# 1. 关闭 WSL${NC}"
    echo "wsl --shutdown"
    echo ""
    echo -e "${GREEN}# 2. 压缩磁盘${NC}"
    echo "Optimize-VHD -Path \$env:LOCALAPPDATA\\Docker\\wsl\\data\\ext4.vhdx -Mode Full"
    echo ""
    echo -e "${GREEN}# 3. 重启 Docker Desktop${NC}"
    echo ""
    echo "压缩可能需要 10-30 分钟，取决于磁盘大小。"
    echo ""
}

# 主循环
while true; do
    show_menu
    read -p "请选择 [0-8]: " choice
    echo ""
    
    case $choice in
        1)
            show_space
            ;;
        2)
            clean_containers
            ;;
        3)
            clean_images
            ;;
        4)
            clean_build_cache
            ;;
        5)
            clean_volumes
            ;;
        6)
            full_clean
            ;;
        7)
            dangerous_clean
            ;;
        8)
            show_wsl_compact
            ;;
        0)
            echo "退出清理工具"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择，请重试${NC}"
            ;;
    esac
    
    read -p "按 Enter 继续..."
    clear
done
