from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import logging
import os
from pathlib import Path

load_dotenv()

# 配置日志 - 只显示 WARNING 及以上级别
# 避免 Python 脚本中的调试信息刷屏
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Cortex3d API",
    description="2D Image Generation API for Cortex3d",
    version="1.0.0",
)

# CORS middleware
# 允许来源: 开发环境 + 生产环境 (通过环境变量 CORS_ORIGINS 配置)
_cors_origins = os.environ.get("CORS_ORIGINS", "")
_allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://172.28.124.41:5173",    # WSL 局域网 IP - 前端
    "http://172.28.124.41:8000",    # WSL 局域网 IP - 后端
]
if _cors_origins:
    _allowed_origins.extend([o.strip() for o in _cors_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from backend.api.endpoints import generate, health

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(generate.router, prefix="/api", tags=["Generation"])

# Mount outputs directory for static file serving
project_root = Path(__file__).parent.parent
outputs_dir = project_root / "outputs"
os.makedirs(outputs_dir, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")


@app.get("/")
async def root():
    return {"message": "Cortex3d API", "version": "1.0.0"}
