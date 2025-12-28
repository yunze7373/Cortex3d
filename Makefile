# Cortex3d Makefile - 统一运行入口
# 所有命令都在 Docker 容器内执行

SVC = instantmesh

# 进入容器 shell
shell:
	docker compose exec $(SVC) bash

# 运行 InstantMesh
run:
	docker compose exec $(SVC) python3 /workspace/scripts/run_instantmesh.py $(ARGS)

# 使用测试图片运行 (标准质量 75 steps, 1024 tex)
test:
	docker compose exec $(SVC) python3 /workspace/scripts/run_instantmesh.py \
		/workspace/InstantMesh/configs/instant-mesh-large.yaml \
		/workspace/test_images/character_20251226_013442_front.png \
		--output_path /workspace/outputs

# 使用测试图片运行 (高质量 200 steps, 2048 tex)
# 增加 diffusion steps 和 texture resolution
test-hq:
	docker compose exec $(SVC) python3 /workspace/scripts/run_instantmesh.py \
		/workspace/configs/instant-mesh-hq.yaml \
		/workspace/test_images/character_20251226_013442_front.png \
		--output_path /workspace/outputs \
		--diffusion_steps 200 \
		--texture_resolution 2048 \
		--guidance_scale 7.5

# 运行 TripoSR 测试 (几何锐度高)
test-triposr:
	docker compose exec $(SVC) python3 /workspace/scripts/run_triposr.py \
		/workspace/test_images/character_20251226_013442_front.png \
		--output-dir /workspace/outputs/triposr \
		--bake-texture \
		--texture-resolution 2048 \
		--mc-resolution 1024

# --- Unified Pipeline Targets ---

# --- Unified Pipeline Targets ---

# Full Pipeline (Stage 2 + Stage 4)
pipeline: reconstruct stage4

# Stage 2: Unified Reconstruction (Auto/InstantMesh/TripoSR)
# Defaulting to High Quality for better input to Blender
reconstruct:
	docker compose exec $(SVC) python3 /workspace/scripts/reconstructor.py \
		/workspace/test_images/character_20251226_013442_front.png \
		--algo auto --quality high

# Stage 3: Detail Generation (Marigold) - OPTIONAL / DEPRECATED for now
# Keeping it for reference but not processing it in main pipeline
stage3:
	docker compose exec $(SVC) python3 /workspace/scripts/stage3_details.py \
		/workspace/test_images/character_20251226_013442_front.png

# Stage 4: Blender Refinement
# Note: Requires Blender installed in Docker or local path mapped
stage4:
	docker compose exec $(SVC) python3 /workspace/scripts/blender_factory.py \
		--mesh /workspace/outputs/instantmesh/instant-mesh-hq/meshes/character_20251226_013442_front.obj \
		--output /workspace/outputs/final_print.stl \
		--height_mm 100 \
		--voxel_size_mm 0.1

# 检查环境
check:
	docker compose exec $(SVC) python3 -c "import torch; import nvdiffrast.torch as dr; print('✅ OK:', torch.cuda.get_device_name(0))"

# 临时修复缺少 GL 库的问题 (避免重建镜像)
# 增加 xvfb 用于模拟 X11 环境
fix-gl:
	docker compose exec $(SVC) apt-get update
	docker compose exec $(SVC) apt-get install -y libgl1 libegl1 libx11-6 xvfb

# 构建镜像
build:
	docker compose build --no-cache

# 启动容器
up:
	docker compose up -d

# 停止容器
down:
	docker compose down

# 查看日志
logs:
	docker compose logs -f $(SVC)

# 帮助
help:
	@echo "用法:"
	@echo "  make shell   - 进入容器 bash"
	@echo "  make check   - 检查 GPU 和依赖"
	@echo "  make test    - 使用测试图片生成 3D 模型"
	@echo "  make run ARGS='input.png --output_dir out'  - 自定义参数运行"
	@echo "  make build   - 重新构建镜像"
	@echo "  make up      - 启动容器"
	@echo "  make down    - 停止容器"
