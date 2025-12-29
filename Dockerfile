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

# PyTorch + CUDA 12.1 (Upgraded to Torch 2.6.0+ for security fixes CVE-2025-32434)
RUN pip3 install --no-cache-dir \
    "torch>=2.6.0" "torchvision>=0.21.0" \
    --index-url https://download.pytorch.org/whl/cu124

# InstantMesh & TripoSR 统一依赖
# transformers 4.35.0: TripoSR needs this specific version range usually
# diffusers 0.29.0: Upgrade for Marigold support
RUN pip3 install --no-cache-dir pytorch-lightning==2.1.2 einops omegaconf torchmetrics
RUN pip3 install --no-cache-dir diffusers==0.29.0 transformers==4.35.2 huggingface-hub>=0.23.2
RUN pip3 install --no-cache-dir accelerate==0.24.1 tensorboard trimesh xatlas pymcubes rembg onnxruntime moderngl
RUN pip3 install --no-cache-dir pillow tqdm safetensors kiui pygltflib imageio[ffmpeg] plyfile

# TripoSR 额外依赖 (需编译)
RUN pip3 install --no-cache-dir git+https://github.com/tatsy/torchmcubes.git

# Blender 4.2 LTS Installation
RUN apt-get update && apt-get install -y \
    wget xz-utils libxi6 libxrender1 libxxf86vm1 libxfixes3 \
    libsm6 libgl1 libxkbcommon0 libegl1 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/blender && \
    wget -q https://download.blender.org/release/Blender4.2/blender-4.2.0-linux-x64.tar.xz -O /tmp/blender.tar.xz && \
    tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 && \
    rm /tmp/blender.tar.xz && \
    ln -s /opt/blender/blender /usr/local/bin/blender

# nvdiffrast - 移到最后安装，防止被其他 pip 操作影响
RUN git clone https://github.com/NVlabs/nvdiffrast.git /opt/nvdiffrast \
    && cd /opt/nvdiffrast \
    && sed -i 's/from importlib.metadata import version/__version__ = "0.3.1"  # patched\\n# from importlib.metadata import version/' nvdiffrast/__init__.py \
    && sed -i 's/__version__ = version(__package__ or .nvdiffrast.)/__version__ = __version__  # patched/' nvdiffrast/__init__.py \
    && pip3 install --no-cache-dir --no-build-isolation . \
    && python3 -c "import nvdiffrast.torch as dr; print('✅ nvdiffrast installed successfully')"

WORKDIR /workspace

# 最终验证
RUN python3 -c "import torch; import nvdiffrast.torch as dr; import diffusers; print(f'✅ All dependencies OK. Diffusers: {diffusers.__version__}')"
RUN blender --version



