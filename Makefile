# Cortex3d Makefile - 统一运行入口
# 所有命令都在 Docker 容器内执行

SVC = instantmesh

# 进入容器 shell
shell:
	docker compose exec $(SVC) bash

# 运行 InstantMesh
run:
	docker compose exec $(SVC) python3 /workspace/InstantMesh/run.py $(ARGS)

# 使用测试图片运行
test:
	docker compose exec $(SVC) python3 /workspace/InstantMesh/run.py \
		/workspace/InstantMesh/configs/instant-mesh-large.yaml \
		/workspace/test_images/character_20251226_013442_front.png \
		--output_path /workspace/outputs

# 检查环境
check:
	docker compose exec $(SVC) python3 -c "import torch; import nvdiffrast.torch as dr; print('✅ OK:', torch.cuda.get_device_name(0))"

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
