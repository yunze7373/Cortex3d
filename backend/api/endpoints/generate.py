import os
import sys
import asyncio
import base64
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

router = APIRouter()

# Mock generation for demo purposes
# In production, this would integrate with the existing Python scripts


class GenerateRequest(BaseModel):
    description: str
    mode: str = "proxy"
    viewMode: str = "4-view"
    customViews: Optional[list] = []
    style: str = "realistic"
    resolution: str = "1K"
    referenceImage: Optional[str] = None
    negativePrompt: Optional[str] = ""
    subjectOnly: bool = True
    withProps: Optional[list] = []


class GenerateResponse(BaseModel):
    assetId: str
    status: str
    images: dict
    metadata: dict


# ============ 服装提取相关模型 ============

class ExtractClothesRequest(BaseModel):
    image: str
    extractProps: bool = False


class ExtractClothesResponse(BaseModel):
    assetId: str
    status: str
    originalImage: Optional[str] = None
    extractedClothes: Optional[str] = None
    extractedProps: Optional[list] = None


# ============ 换衣服相关模型 ============

class ChangeClothesRequest(BaseModel):
    characterImage: str
    clothesDescription: str
    targetStyle: Optional[str] = "realistic"
    viewMode: Optional[str] = "4-view"


class ChangeClothesResponse(BaseModel):
    assetId: str
    status: str
    images: dict


# ============ 风格切换相关模型 ============

class ChangeStyleRequest(BaseModel):
    image: str
    style: str = "anime"
    strength: float = 0.7


class ChangeStyleResponse(BaseModel):
    assetId: str
    status: str
    originalImage: Optional[str] = None
    styledImage: Optional[str] = None


async def generate_image_mock(description: str, view: str) -> str:
    """Mock image generation - returns a placeholder SVG"""
    # In production, this would call the actual AI models
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#1a1a24"/>
  <text x="256" y="256" text-anchor="middle" dominant-baseline="middle"
        font-family="Arial" font-size="24" fill="#6366f1">
    {view.upper()}
  </text>
  <text x="256" y="300" text-anchor="middle" dominant-baseline="middle"
        font-family="Arial" font-size="14" fill="#a0a0b0">
    {description[:30]}...
  </text>
</svg>'''
    return f"data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}"


async def generate_mock_styled_image(style: str) -> str:
    """生成模拟的风格转换图像"""
    style_labels = {
        "anime": "动漫风格",
        "cartoon": "卡通风格",
        "3d-render": "3D渲染",
        "sketch": "素描风格",
        "watercolor": "水彩风格",
        "oil-painting": "油画风格",
        "pixel-art": "像素风格",
        "realistic": "写实风格",
    }
    label = style_labels.get(style, style)

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#1a1a24"/>
  <text x="256" y="256" text-anchor="middle" dominant-baseline="middle"
        font-family="Arial" font-size="28" fill="#8b5cf6">
    {label}
  </text>
  <text x="256" y="310" text-anchor="middle" dominant-baseline="middle"
        font-family="Arial" font-size="14" fill="#a0a0b0">
    风格转换结果
  </text>
</svg>'''
    return f"data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}"


async def generate_mock_extracted_clothes() -> str:
    """生成模拟的提取服装图像"""
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" fill="#1a1a24"/>
  <text x="256" y="256" text-anchor="middle" dominant-baseline="middle"
        font-family="Arial" font-size="24" fill="#10b981">
    提取的服装
  </text>
  <text x="256" y="310" text-anchor="middle" dominant-baseline="middle"
        font-family="Arial" font-size="14" fill="#a0a0b0">
    透明背景
  </text>
</svg>'''
    return f"data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}"


# ============ API 端点 ============

@router.post("/generate/multiview")
async def generate_multiview(request: GenerateRequest):
    """Generate multi-view images from text description"""
    try:
        asset_id = str(uuid.uuid4())

        # Map view mode to actual views
        view_mapping = {
            "4-view": ["front", "right", "back", "left"],
            "6-view": ["front", "frontRight", "right", "back", "left", "frontLeft"],
            "8-view": ["front", "frontRight", "right", "backRight", "back", "backLeft", "left", "frontLeft"],
        }

        views = view_mapping.get(request.viewMode, ["front", "right", "back", "left"])

        # Generate placeholder images for each view
        images = {}
        for view in views:
            images[view] = await generate_image_mock(request.description, view)

        # Add master image (same as front)
        images["master"] = images.get("front", "")

        return GenerateResponse(
            assetId=asset_id,
            status="success",
            images=images,
            metadata={
                "description": request.description,
                "style": request.style,
                "model": "cortex3d-v1",
                "createdAt": "2024-01-01T00:00:00Z",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/from-image")
async def generate_from_image(request: GenerateRequest):
    """Generate multi-view images from reference image"""
    if not request.referenceImage:
        raise HTTPException(status_code=400, detail="Reference image is required")

    try:
        asset_id = str(uuid.uuid4())

        # Map view mode to actual views
        view_mapping = {
            "4-view": ["front", "right", "back", "left"],
            "6-view": ["front", "frontRight", "right", "back", "left", "frontLeft"],
            "8-view": ["front", "frontRight", "right", "backRight", "back", "backLeft", "left", "frontLeft"],
        }

        views = view_mapping.get(request.viewMode, ["front", "right", "back", "left"])

        # Generate placeholder images
        images = {}
        for view in views:
            images[view] = await generate_image_mock("Generated from image", view)

        images["master"] = images.get("front", "")

        return GenerateResponse(
            assetId=asset_id,
            status="success",
            images=images,
            metadata={
                "description": "Generated from reference image",
                "style": request.style,
                "model": "cortex3d-v1",
                "createdAt": "2024-01-01T00:00:00Z",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/clothes")
async def extract_clothes(request: ExtractClothesRequest):
    """Extract clothes from character image"""
    if not request.image:
        raise HTTPException(status_code=400, detail="Image is required")

    try:
        asset_id = str(uuid.uuid4())

        # Mock response - in production, this would call the actual image processing
        return ExtractClothesResponse(
            assetId=asset_id,
            status="success",
            originalImage=request.image,
            extractedClothes=await generate_mock_extracted_clothes(),
            extractedProps=["道具1", "道具2"] if request.extractProps else None,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit/change-clothes")
async def change_clothes(request: ChangeClothesRequest):
    """Change character's clothes"""
    if not request.characterImage:
        raise HTTPException(status_code=400, detail="Character image is required")
    if not request.clothesDescription:
        raise HTTPException(status_code=400, detail="Clothes description is required")

    try:
        asset_id = str(uuid.uuid4())

        # Map view mode to actual views
        view_mapping = {
            "4-view": ["front", "right", "back", "left"],
            "6-view": ["front", "frontRight", "right", "back", "left", "frontLeft"],
        }

        views = view_mapping.get(request.viewMode, ["front", "right", "back", "left"])

        # Generate placeholder images with changed clothes
        images = {}
        for view in views:
            images[view] = await generate_image_mock(f"换装: {request.clothesDescription}", view)

        images["master"] = images.get("front", "")

        return ChangeClothesResponse(
            assetId=asset_id,
            status="success",
            images=images,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit/change-style")
async def change_style(request: ChangeStyleRequest):
    """Change image style"""
    if not request.image:
        raise HTTPException(status_code=400, detail="Image is required")

    try:
        asset_id = str(uuid.uuid4())

        # Generate styled image mock
        styled_image = await generate_mock_styled_image(request.style)

        return ChangeStyleResponse(
            assetId=asset_id,
            status="success",
            originalImage=request.image,
            styledImage=styled_image,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    """Get generation history"""
    # In production, this would fetch from a database
    return []


@router.get("/download/{asset_id}")
async def download_asset(asset_id: str):
    """Download generated assets"""
    raise HTTPException(status_code=501, detail="Download not implemented")
