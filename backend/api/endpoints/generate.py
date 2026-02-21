import os
import sys
import base64
import uuid
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add the project root to the path
# __file__ = /home/han/projects/cortex3d/backend/api/endpoints/generate.py
# parent = endpoints, parent.parent = api, parent.parent.parent = backend, parent.parent.parent.parent = cortex3d
project_root = Path(__file__).parent.parent.parent.parent
scripts_dir = project_root / "scripts"
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(project_root))

router = APIRouter()

# ============ 请求模型 ============

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
    model: Optional[str] = "gemini-3-pro-image-preview"
    useNegativePrompt: bool = True
    negativeCategories: Optional[list] = []
    useStrictMode: bool = False
    useImageReferencePrompt: bool = False
    aspectRatio: Optional[str] = "3:2"


class GenerateResponse(BaseModel):
    assetId: str
    status: str
    images: dict
    metadata: dict


class ExtractClothesRequest(BaseModel):
    image: str
    extractProps: bool = False


class ExtractClothesResponse(BaseModel):
    assetId: str
    status: str
    originalImage: Optional[str] = None
    extractedClothes: Optional[str] = None
    extractedProps: Optional[list] = None


class ChangeClothesRequest(BaseModel):
    characterImage: str
    clothesDescription: Optional[str] = None
    clothesImage: Optional[str] = None
    targetStyle: Optional[str] = "realistic"
    viewMode: Optional[str] = "4-view"


class ChangeClothesResponse(BaseModel):
    assetId: str
    status: str
    images: dict


class ChangeStyleRequest(BaseModel):
    image: str
    style: str = "anime"
    strength: float = 0.7


class ChangeStyleResponse(BaseModel):
    assetId: str
    status: str
    originalImage: Optional[str] = None
    styledImage: Optional[str] = None


# ============ 辅助函数 ============

def base64_to_temp_file(base64_str: str, suffix: str = ".png") -> str:
    """将base64图片保存到临时文件"""
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]

    image_data = base64.b64decode(base64_str)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(image_data)
    temp_file.close()
    return temp_file.name


def image_to_base64(image_path: str) -> str:
    """将图片文件转换为base64"""
    with open(image_path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"


def get_api_token() -> str:
    """从环境变量获取API token"""
    return os.environ.get("AIPROXY_TOKEN", "")


# ============ API 端点 ============

@router.post("/generate/multiview")
async def generate_multiview(request: GenerateRequest):
    """Generate multi-view images from text description"""
    try:
        from aiproxy_client import generate_character_multiview

        token = get_api_token()
        if not token:
            raise HTTPException(status_code=400, detail="请设置 AIPROXY_TOKEN 环境变量")

        asset_id = str(uuid.uuid4())
        output_dir = str(project_root / "outputs" / asset_id)

        os.makedirs(output_dir, exist_ok=True)

        result = generate_character_multiview(
            character_description=request.description,
            token=token,
            output_dir=output_dir,
            auto_cut=True,
            model=request.model or "gemini-3-pro-image-preview",
            style=request.style or "cinematic character",
            asset_id=asset_id,
            reference_image_path=request.referenceImage,
            use_image_reference_prompt=request.useImageReferencePrompt,
            use_strict_mode=request.useStrictMode,
            resolution=request.resolution or "2K",
            view_mode=request.viewMode or "4-view",
            custom_views=request.customViews,
            use_negative_prompt=request.useNegativePrompt,
            negative_categories=request.negativeCategories,
            subject_only=request.subjectOnly,
            with_props=request.withProps,
        )

        if not result:
            raise HTTPException(status_code=500, detail="生成失败")

        # 查找生成的图片
        images = {}
        output_path = Path(output_dir)

        view_mapping = {
            "single": ["front"],
            "4-view": ["front", "right", "back", "left"],
            "6-view": ["front", "frontRight", "right", "back", "left", "frontLeft"],
            "8-view": ["front", "frontRight", "right", "backRight", "back", "backLeft", "left", "frontLeft"],
            "custom": request.customViews or ["front"],
        }

        views = view_mapping.get(request.viewMode or "4-view", ["front", "right", "back", "left"])

        for view in views:
            for ext in [".png", ".jpg", ".jpeg"]:
                file_path = output_path / f"{view}{ext}"
                if file_path.exists():
                    images[view] = image_to_base64(str(file_path))
                    break

        if "front" in images:
            images["master"] = images["front"]

        if not images:
            raise HTTPException(status_code=500, detail="未找到生成的图片")

        return GenerateResponse(
            assetId=asset_id,
            status="success",
            images=images,
            metadata={
                "description": request.description,
                "style": request.style,
                "model": request.model,
                "createdAt": "2024-01-01T00:00:00Z",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/from-image")
async def generate_from_image(request: GenerateRequest):
    """Generate multi-view images from reference image"""
    if not request.referenceImage:
        raise HTTPException(status_code=400, detail="需要上传参考图片")

    request.useImageReferencePrompt = True
    return await generate_multiview(request)


@router.post("/extract/clothes")
async def extract_clothes(request: ExtractClothesRequest):
    """Extract clothes from character image"""
    if not request.image:
        raise HTTPException(status_code=400, detail="需要上传图片")

    try:
        from gemini_generator import smart_extract_clothing

        token = get_api_token()
        if not token:
            raise HTTPException(status_code=400, detail="请设置 AIPROXY_TOKEN 环境变量")

        asset_id = str(uuid.uuid4())
        output_dir = str(project_root / "outputs" / asset_id)
        os.makedirs(output_dir, exist_ok=True)

        # 保存上传的图片
        input_path = base64_to_temp_file(request.image, ".png")

        # 调用智能衣服提取
        extracted_path = smart_extract_clothing(
            image_path=input_path,
            api_key=token,
            model_name="gemini-3-pro-image-preview",
            output_dir=output_dir,
            mode="proxy",
        )

        # 清理临时输入文件
        os.unlink(input_path)

        if not extracted_path or not Path(extracted_path).exists():
            raise HTTPException(status_code=500, detail="衣服提取失败")

        return ExtractClothesResponse(
            assetId=asset_id,
            status="success",
            originalImage=request.image,
            extractedClothes=image_to_base64(extracted_path),
            extractedProps=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit/change-clothes")
async def change_clothes(request: ChangeClothesRequest):
    """Change character's clothes"""
    if not request.characterImage:
        raise HTTPException(status_code=400, detail="需要上传角色图片")

    try:
        from aiproxy_client import generate_character_multiview

        token = get_api_token()
        if not token:
            raise HTTPException(status_code=400, detail="请设置 AIPROXY_TOKEN 环境变量")

        asset_id = str(uuid.uuid4())
        output_dir = str(project_root / "outputs" / asset_id)
        os.makedirs(output_dir, exist_ok=True)

        # 保存角色图片
        char_path = base64_to_temp_file(request.characterImage, ".png")

        description = request.clothesDescription or "character with new clothes"

        result = generate_character_multiview(
            character_description=description,
            token=token,
            output_dir=output_dir,
            auto_cut=True,
            model="gemini-3-pro-image-preview",
            style=request.targetStyle or "realistic",
            asset_id=asset_id,
            reference_image_path=char_path,
            use_image_reference_prompt=True,
            view_mode=request.viewMode or "4-view",
        )

        os.unlink(char_path)

        images = {}
        output_path = Path(output_dir)
        view_mapping = {
            "4-view": ["front", "right", "back", "left"],
            "6-view": ["front", "frontRight", "right", "back", "left", "frontLeft"],
        }
        views = view_mapping.get(request.viewMode or "4-view", ["front", "right", "back", "left"])

        for view in views:
            for ext in [".png", ".jpg", ".jpeg"]:
                file_path = output_path / f"{view}{ext}"
                if file_path.exists():
                    images[view] = image_to_base64(str(file_path))
                    break

        if "front" in images:
            images["master"] = images["front"]

        if not images:
            raise HTTPException(status_code=500, detail="换装生成失败")

        return ChangeClothesResponse(
            assetId=asset_id,
            status="success",
            images=images,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit/change-style")
async def change_style(request: ChangeStyleRequest):
    """Change image style"""
    if not request.image:
        raise HTTPException(status_code=400, detail="需要上传图片")

    try:
        from aiproxy_client import generate_character_multiview

        token = get_api_token()
        if not token:
            raise HTTPException(status_code=400, detail="请设置 AIPROXY_TOKEN 环境变量")

        style_prompts = {
            "anime": "anime style, cel-shaded, vibrant colors",
            "cartoon": "cartoon style, comic book art",
            "3d-render": "3D render, photorealistic",
            "sketch": "pencil sketch, hand-drawn",
            "watercolor": "watercolor painting, artistic",
            "oil-painting": "oil painting style, classic art",
            "pixel-art": "pixel art, 8-bit style",
            "realistic": "photorealistic, high quality",
            "cinematic": "cinematic lighting, movie quality",
        }

        description = f"same subject, {style_prompts.get(request.style, request.style)}"

        asset_id = str(uuid.uuid4())
        output_dir = str(project_root / "outputs" / asset_id)
        os.makedirs(output_dir, exist_ok=True)

        img_path = base64_to_temp_file(request.image, ".png")

        result = generate_character_multiview(
            character_description=description,
            token=token,
            output_dir=output_dir,
            auto_cut=False,
            model="gemini-3-pro-image-preview",
            reference_image_path=img_path,
            use_image_reference_prompt=True,
        )

        os.unlink(img_path)

        output_path = Path(output_dir)
        styled_image = None

        for ext in [".png", ".jpg", ".jpeg"]:
            files = list(output_path.glob(f"*{ext}"))
            if files:
                styled_image = image_to_base64(str(files[0]))
                break

        if not styled_image:
            raise HTTPException(status_code=500, detail="风格转换失败")

        return ChangeStyleResponse(
            assetId=asset_id,
            status="success",
            originalImage=request.image,
            styledImage=styled_image,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history():
    return []


@router.get("/download/{asset_id}")
async def download_asset(asset_id: str):
    output_dir = str(project_root / "outputs" / asset_id)
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="素材不存在")
    return {"asset_id": asset_id, "path": output_dir}
