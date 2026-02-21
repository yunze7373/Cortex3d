from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from backend.api.endpoints import generate, health

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(generate.router, prefix="/api", tags=["Generation"])


@app.get("/")
async def root():
    return {"message": "Cortex3d API", "version": "1.0.0"}
