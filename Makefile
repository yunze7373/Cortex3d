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

# NEW: Multi-View Pipeline (Uses real 4-view images for higher quality)
pipeline-mv: reconstruct-mv stage4

# Stage 2: Unified Reconstruction (Auto/InstantMesh/TripoSR)
# Defaulting to High Quality for better input to Blender
reconstruct:
	docker compose exec $(SVC) python3 /workspace/scripts/reconstructor.py \
		/workspace/test_images/character_20251226_013442_front.png \
		--algo auto --quality high

# NEW: Multi-View Reconstruction (Uses 4 real views: front, back, left, right)
reconstruct-mv:
	docker compose exec $(SVC) python3 /workspace/scripts/reconstructor.py \
		/workspace/test_images/character_20251226_013442_front.png \
		--algo multiview --quality high

# Stage 3: Detail Generation (Marigold) - OPTIONAL / DEPRECATED for now
# Keeping it for reference but not processing it in main pipeline
stage3:
	docker compose exec $(SVC) python3 /workspace/scripts/stage3_details.py \
		/workspace/test_images/character_20251226_013442_front.png

# Stage 4: Blender Refinement
# Note: Requires Blender installed in Docker or local path mapped
stage4:
	docker compose exec $(SVC) python3 /workspace/scripts/blender_factory.py \
		--mesh /workspace/outputs/latest.obj \
		--output /workspace/outputs/final_print.stl \
		--height_mm 100 \
		--voxel_size_mm 0.1

# --- TRELLIS Targets (High Quality) ---

# Build TRELLIS Docker image
build-trellis:
	docker compose build trellis

# Start TRELLIS container
up-trellis:
	docker compose up -d trellis

# TRELLIS reconstruction
reconstruct-trellis:
	docker compose exec trellis python3 /workspace/scripts/run_trellis.py \
		/workspace/test_images/character_20251226_013442_front.png \
		--output /workspace/outputs/trellis

# TRELLIS + Blender pipeline
pipeline-trellis: reconstruct-trellis stage4-trellis

# Helper for TRELLIS post-processing (runs in instantmesh container because it has Blender)
stage4-trellis:
	docker compose exec $(SVC) python3 /workspace/scripts/blender_factory.py \
		--mesh /workspace/outputs/trellis/character_20251226_013442_front.obj \
		--output /workspace/outputs/final_print_trellis.stl \
		--height_mm 100 \
# Helper for TRELLIS post-processing (runs in instantmesh container because it has Blender)
stage4-trellis:
	docker compose exec $(SVC) python3 /workspace/scripts/blender_factory.py \
		--mesh /workspace/outputs/trellis/character_20251226_013442_front.obj \
		--output /workspace/outputs/final_print_trellis.stl \
		--height_mm 100 \
		--voxel_size_mm 0.1 \
		--skip_remesh

# --- TRELLIS2 Targets (New Microsoft TRELLIS) ---

# Build TRELLIS2 Docker image
build-trellis2:
	docker compose build trellis2

# Start TRELLIS2 container
up-trellis2:
	docker compose up -d trellis2

# TRELLIS2 reconstruction (using official Microsoft TRELLIS)
reconstruct-trellis2:
	docker compose exec trellis2 python3 /workspace/scripts/run_trellis2.py \
		/workspace/test_images/character_20251226_013442_front.png \
		--output /workspace/outputs/trellis2

# TRELLIS2 + Blender pipeline
pipeline-trellis2: reconstruct-trellis2 stage4-trellis2

# Helper for TRELLIS2 post-processing
stage4-trellis2:
	docker compose exec $(SVC) python3 /workspace/scripts/blender_factory.py \
		--mesh /workspace/outputs/trellis2/character_20251226_013442_front.glb \
		--output /workspace/outputs/final_print_trellis2.stl \
		--height_mm 100 \
		--voxel_size_mm 0.1

# 检查环境
check:
	docker compose exec $(SVC) python3 -c "import torch; import nvdiffrast.torch as dr; print('✅ OK:', torch.cuda.get_device_name(0))"

# === UltraShape Targets (Universal Geometry Refiner) ===
# UltraShape 可以细化任何模型的输出，提升几何质量

.PHONY: build-ultrashape
build-ultrashape:
	@echo "🔨 构建 UltraShape 容器..."
	docker compose build ultrashape

# 启动 UltraShape Gradio UI（交互式细化）
.PHONY: run-ultrashape-ui
run-ultrashape-ui:
	@echo "🎨 启动 UltraShape Gradio UI..."
	@echo "   访问 http://localhost:7863"
	docker compose up ultrashape

# 细化任意网格（通用命令）
# 用法: make refine-mesh IMAGE=test.png MESH=outputs/xxx/mesh.glb PRESET=balanced
.PHONY: refine-mesh
refine-mesh:
	@echo "✨ UltraShape 细化网格..."
	docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
		--image /workspace/test_images/$(IMAGE) \
		--mesh /workspace/$(MESH) \
		--output /workspace/outputs/ultrashape \
		--preset $(or $(PRESET),balanced)

# 快速细化（低显存，30秒）
.PHONY: refine-fast
refine-fast:
	@echo "⚡ 快速细化模式..."
	docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
		--image /workspace/test_images/$(IMAGE) \
		--mesh /workspace/$(MESH) \
		--output /workspace/outputs/ultrashape \
		--preset fast \
		--low-vram

# 高质量细化（5分钟）
.PHONY: refine-high
refine-high:
	@echo "🎯 高质量细化模式..."
	docker compose exec ultrashape python3 /workspace/scripts/run_ultrashape.py \
		--image /workspace/test_images/$(IMAGE) \
		--mesh /workspace/$(MESH) \
		--output /workspace/outputs/ultrashape \
		--preset high

# === 集成流水线：模型生成 + UltraShape 细化 ===

# InstantMesh → UltraShape
.PHONY: pipeline-instantmesh-refined
pipeline-instantmesh-refined:
	@echo "🔄 InstantMesh + UltraShape 完整流水线..."
	$(MAKE) reconstruct IMAGE=$(IMAGE)
	$(MAKE) refine-mesh IMAGE=$(IMAGE) MESH=outputs/latest.obj PRESET=balanced

# TRELLIS.2 → UltraShape
.PHONY: pipeline-trellis2-refined
pipeline-trellis2-refined:
	@echo "🔄 TRELLIS.2 + UltraShape 完整流水线..."
	$(MAKE) reconstruct-trellis2 IMAGE=$(IMAGE)
	@TRELLIS_MESH=$$(find outputs/trellis2 -name "*.glb" | head -1); \
	$(MAKE) refine-mesh IMAGE=$(IMAGE) MESH=$$TRELLIS_MESH PRESET=balanced

# Hunyuan3D-Omni → UltraShape
.PHONY: pipeline-hunyuan-refined
pipeline-hunyuan-refined:
	@echo "🔄 Hunyuan3D-Omni + UltraShape 完整流水线..."
	$(MAKE) reconstruct-hunyuan3d-omni IMAGE=$(IMAGE)
	@HUNYUAN_MESH=$$(find outputs/hunyuan3d_omni -name "*.glb" | head -1); \
	$(MAKE) refine-mesh IMAGE=$(IMAGE) MESH=$$HUNYUAN_MESH PRESET=balanced

# TripoSR → UltraShape
.PHONY: pipeline-triposr-refined
pipeline-triposr-refined:
	@echo "🔄 TripoSR + UltraShape 完整流水线..."
	$(MAKE) test-triposr IMAGE=$(IMAGE)
	@TRIPOSR_MESH=$$(find outputs/triposr -name "*.obj" -o -name "*.glb" | head -1); \
	$(MAKE) refine-mesh IMAGE=$(IMAGE) MESH=$$TRIPOSR_MESH PRESET=balanced

# 批量细化已有模型输出
.PHONY: refine-existing
refine-existing:
	@echo "🎯 细化指定目录下的网格..."
	@for mesh in outputs/$(DIR)/*.glb outputs/$(DIR)/*.obj; do \
		if [ -f "$$mesh" ]; then \
			echo "细化: $$mesh"; \
			$(MAKE) refine-mesh IMAGE=$(IMAGE) MESH=$$mesh PRESET=$(or $(PRESET),fast); \
		fi; \
	done

# === Docker 清理命令 ===

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

# --- Docker 清理命令 (释放WSL空间) ---

# 清理所有停止的容器
clean-containers:
	@echo "🧹 清理停止的容器..."
	docker container prune -f

# 清理未使用的镜像
clean-images:
	@echo "🧹 清理未使用的镜像..."
	docker image prune -a -f

# 清理 Docker 构建缓存
clean-build-cache:
	@echo "🧹 清理 Docker 构建缓存..."
	docker builder prune -a -f
	@echo ""
	@echo "Docker 清理 (释放空间):"
	@echo "  make docker-space      - 查看 Docker 空间使用"
	@echo "  make images-size       - 查看所有镜像大小"
	@echo "  make clean-containers  - 清理停止的容器"
	@echo "  make clean-images      - 清理未使用的镜像"
	@echo "  make clean-build-cache - 清理构建缓存"
	@echo "  make clean-all         - 完全清理 (保留 HF 缓存)"
	@echo "  make wsl-compact       - 显示 WSL 磁盘压缩方法"

# 清理未使用的卷
clean-volumes:
	@echo "🧹 清理未使用的卷..."
	docker volume prune -f

# 清理未使用的网络
clean-networks:
	@echo "🧹 清理未使用的网络..."
	docker network prune -f

# 完全清理 (保留 hf-cache 卷)
clean-all:
	@echo "⚠️  即将清理所有 Docker 资源 (保留 Hugging Face 缓存)..."
	@echo "按 Ctrl+C 取消，或等待 5 秒继续..."
	@sleep 5
	docker container prune -f
	docker image prune -a -f
	docker builder prune -a -f
	docker volume prune -f --filter "label!=com.docker.compose.volume=hf-cache"
	docker network prune -f
	@echo "✅ 清理完成！"

# 显示 Docker 空间使用情况
docker-space:
	@echo "📊 Docker 空间使用情况:"
	@echo ""
	docker system df -v

# 查看所有镜像大小
images-size:
	@echo "📦 镜像列表 (按大小排序):"
	@docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | sort -k3 -h

# 删除旧的 TRELLIS 镜像 (如果重新构建失败)
clean-trellis-old:
	@echo "🧹 删除旧的 TRELLIS 相关镜像..."
	docker rmi -f $$(docker images | grep "trellis" | awk '{print $$3}') 2>/dev/null || true

# WSL 磁盘压缩 (需要在 PowerShell 中运行)
wsl-compact:
	@echo "ℹ️  WSL 磁盘压缩需要在 Windows PowerShell 中运行:"
	@echo ""
	@echo "  1. 关闭 WSL: wsl --shutdown"
	@echo "  2. 压缩磁盘: Optimize-VHD -Path %%LOCALAPPDATA%%\\Docker\\wsl\\data\\ext4.vhdx -Mode Full"
	@echo "  3. 重启 Docker Desktop"
	@echo ""

# === Z-Image-Turbo 本地图像生成 ===

# 构建 Z-Image Docker 镜像
.PHONY: build-zimage
build-zimage:
	@echo "🔨 构建 Z-Image-Turbo 容器..."
	docker compose build zimage

# 启动 Z-Image 服务
.PHONY: up-zimage
up-zimage:
	@echo "🚀 启动 Z-Image-Turbo 服务..."
	@echo "   API 地址: http://localhost:8199"
	docker compose up -d zimage

# 停止 Z-Image 服务
.PHONY: down-zimage
down-zimage:
	@echo "⏹️  停止 Z-Image-Turbo 服务..."
	docker compose stop zimage

# 查看 Z-Image 日志
.PHONY: logs-zimage
logs-zimage:
	docker compose logs -f zimage

# 测试 Z-Image 服务
.PHONY: test-zimage
test-zimage:
	@echo "🧪 测试 Z-Image-Turbo 服务..."
	@curl -s http://localhost:8199/health | python3 -m json.tool || echo "❌ 服务未启动"

# 使用 Z-Image 本地生成角色
# 用法: make generate-local PROMPT="赛博朋克风格的女战士"
.PHONY: generate-local
generate-local:
	@echo "🎨 使用 Z-Image 本地生成角色..."
	python scripts/generate_character.py "$(PROMPT)" --mode local

# 使用 Z-Image 生成多视角
# 用法: make generate-local-mv PROMPT="Q版卡通小猫"
.PHONY: generate-local-mv
generate-local-mv:
	@echo "🎨 使用 Z-Image 本地生成多视角..."
	python scripts/generate_character.py "$(PROMPT)" --mode local --multi-view

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
	@echo ""
	@echo "Z-Image-Turbo (本地图像生成):"
	@echo "  make build-zimage      - 构建 Z-Image 镜像"
	@echo "  make up-zimage         - 启动 Z-Image 服务"
	@echo "  make down-zimage       - 停止 Z-Image 服务"
	@echo "  make logs-zimage       - 查看 Z-Image 日志"
	@echo "  make test-zimage       - 测试 Z-Image 服务"
	@echo "  make generate-local PROMPT='描述' - 本地生成角色"
	@echo ""
	@echo "TRELLIS (官方):"
	@echo "  make build-trellis2    - 构建 TRELLIS 镜像"
	@echo "  make up-trellis2       - 启动 TRELLIS 容器"
	@echo "  make reconstruct-trellis2 - 运行 TRELLIS 生成"
	@echo "  make pipeline-trellis2 - TRELLIS 完整流程"
