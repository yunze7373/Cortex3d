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

# PyTorch + CUDA 12.1
RUN pip3 install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cu121

# nvdiffrast - 安装并修补 __init__.py 以解决包元数据问题
RUN git clone https://github.com/NVlabs/nvdiffrast.git /opt/nvdiffrast \
    && cd /opt/nvdiffrast \
    # 修补 __init__.py，移除 version 查询以避免 PackageNotFoundError
    && sed -i 's/from importlib.metadata import version/__version__ = "0.3.1"  # patched\n# from importlib.metadata import version/' nvdiffrast/__init__.py \
    && sed -i 's/__version__ = version(__package__ or .nvdiffrast.)/__version__ = __version__  # patched/' nvdiffrast/__init__.py \
    && pip3 install --no-cache-dir --no-build-isolation -e . \
    && python3 -c "import nvdiffrast.torch as dr; print('✅ nvdiffrast installed successfully')"



# InstantMesh 依赖 (diffusers 需要固定版本以兼容 zero123plus)
RUN pip3 install --no-cache-dir \
    pytorch-lightning \
    diffusers==0.27.0 transformers accelerate \
    einops omegaconf \
    trimesh xatlas pymcubes \
    rembg onnxruntime \
    pillow tqdm huggingface_hub safetensors \
    kiui pygltflib imageio

WORKDIR /workspace

# 最终验证
RUN python3 -c "import torch; import nvdiffrast.torch as dr; print('✅ All dependencies OK')"


