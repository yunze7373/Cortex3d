from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

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
