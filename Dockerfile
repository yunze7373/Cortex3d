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

# 升级 pip 及构建工具
RUN pip3 install --upgrade pip setuptools wheel

# PyTorch + CUDA 12.1
RUN pip3 install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cu121

# InstantMesh 依赖 (使用官方版本，分步安装避免 resolver 问题)
RUN pip3 install --no-cache-dir pytorch-lightning==2.1.2 einops omegaconf torchmetrics
RUN pip3 install --no-cache-dir diffusers==0.20.2 transformers==4.34.1
RUN pip3 install --no-cache-dir accelerate tensorboard trimesh xatlas pymcubes rembg onnxruntime
RUN pip3 install --no-cache-dir pillow tqdm safetensors kiui pygltflib imageio[ffmpeg] plyfile

# nvdiffrast - 移到最后安装，防止被其他 pip 操作影响
RUN git clone https://github.com/NVlabs/nvdiffrast.git /opt/nvdiffrast \
    && cd /opt/nvdiffrast \
    && sed -i 's/from importlib.metadata import version/__version__ = "0.3.1"  # patched\n# from importlib.metadata import version/' nvdiffrast/__init__.py \
    && sed -i 's/__version__ = version(__package__ or .nvdiffrast.)/__version__ = __version__  # patched/' nvdiffrast/__init__.py \
    && pip3 install --no-cache-dir --no-build-isolation . \
    && python3 -c "import nvdiffrast.torch as dr; print('✅ nvdiffrast installed successfully')"

WORKDIR /workspace

# 最终验证
RUN python3 -c "import torch; import nvdiffrast.torch as dr; print('✅ All dependencies OK')"



