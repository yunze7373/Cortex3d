#!/bin/bash
# Cortex3d + InstantMesh Docker 部署脚本
# 用法: bash deploy.sh

set -e

echo "=========================================="
echo "Cortex3d + InstantMesh Docker 部署"
echo "=========================================="

# 检查 Docker 和 GPU
echo "[1/5] 检查环境..."
docker --version || { echo "❌ Docker 未安装"; exit 1; }
nvidia-smi --query-gpu=name --format=csv,noheader || { echo "❌ GPU 不可用"; exit 1; }
echo "✅ 环境检查通过"

# 进入项目目录
PROJECT_DIR=~/projects/cortex3d
cd "$PROJECT_DIR"
echo "[INFO] 项目目录: $PROJECT_DIR"

# 创建 compose.yml
echo "[2/5] 创建 Docker Compose 配置..."
cat > compose.yml << 'EOF'
services:
  instantmesh:
    build:
      context: .
      dockerfile: Dockerfile
    image: instantmesh:latest
    container_name: instantmesh-dev
    working_dir: /workspace
    volumes:
      - ./:/workspace
      - pip-cache:/root/.cache/pip
      - hf-cache:/root/.cache/huggingface
      - ~/data:/data
    shm_size: "8gb"
    stdin_open: true
    tty: true
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

volumes:
  pip-cache:
  hf-cache:
EOF

# 创建 Dockerfile
echo "[3/5] 创建 Dockerfile..."
cat > Dockerfile << 'EOF'
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
# RTX 3080 Ti = Ampere 8.6
ENV TORCH_CUDA_ARCH_LIST="8.6"

# 基础依赖
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev git \
    libgl1-mesa-glx libglib2.0-0 \
    ninja-build g++ \
    && rm -rf /var/lib/apt/lists/*

# PyTorch
RUN pip3 install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cu121

# nvdiffrast
RUN pip3 install --no-cache-dir --no-build-isolation \
    git+https://github.com/NVlabs/nvdiffrast/

# 其他依赖
RUN pip3 install --no-cache-dir \
    pytorch-lightning \
    diffusers transformers accelerate \
    einops omegaconf \
    trimesh xatlas pymcubes \
    rembg onnxruntime \
    pillow tqdm huggingface_hub safetensors \
    kiui pygltflib imageio

WORKDIR /workspace
EOF

# 构建镜像
echo "[4/5] 构建 Docker 镜像 (可能需要 10-20 分钟)..."
docker compose build

# 启动容器
echo "[5/5] 启动容器..."
docker compose up -d

echo ""
echo "=========================================="
echo "✅ 部署完成!"
echo "=========================================="
echo ""
echo "进入容器:"
echo "  docker compose exec instantmesh bash"
echo ""
echo "测试 GPU:"
echo "  docker compose exec instantmesh python3 -c \"import torch; print(torch.cuda.get_device_name(0))\""
echo ""
echo "运行 InstantMesh:"
echo "  docker compose exec instantmesh python3 run.py examples/hatsune_miku.png --output_dir outputs"
echo ""
