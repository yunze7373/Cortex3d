from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Cortex3d API is running"}


@router.get("/")
async def root():
    return {"message": "Cortex3d API is running"}
