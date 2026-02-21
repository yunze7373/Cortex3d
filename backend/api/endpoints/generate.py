import os
import sys
import asyncio
import base64
import uuid
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add the project root to the path
# __file__ = /home/han/projects/cortex3d/backend/api/endpoints/generate.py
# parent = endpoints, parent.parent = api, parent.parent.parent = backend, parent.parent.parent.parent = project_root
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
    # 移除data URL前缀
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
    # 优先使用环境变量
    token = os.environ.get("AIPROXY_TOKEN")
    if not token:
        # 尝试从配置文件读取
        try:
            from config import get_aiproxy_token
            token = get_aiproxy_token()
        except:
            pass
    # 如果没有token，返回空字符串（用于本地测试）
    return token or ""


# ============ API 端点 ============

@router.post("/generate/multiview")
async def generate_multiview(request: GenerateRequest):
    """Generate multi-view images from text description"""
    try:
        from aiproxy_client import generate_character_multiview
        from config import get_aiproxy_token

        token = get_api_token()
        # 如果没有token，尝试使用本地配置
        if not token:
            try:
                token = get_aiproxy_token()
            except:
                pass

        asset_id = str(uuid.uuid4())
        output_dir = f"outputs/{asset_id}"

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 调用生成函数
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
            raise HTTPException(status_code=500, detail="Generation failed")

        # 查找生成的图片
        images = {}
        output_path = Path(output_dir)

        # 视角映射
        view_mapping = {
            "single": ["front"],
            "4-view": ["front", "right", "back", "left"],
            "6-view": ["front", "frontRight", "right", "back", "left", "frontLeft"],
            "8-view": ["front", "frontRight", "right", "backRight", "back", "backLeft", "left", "frontLeft"],
            "custom": request.customViews or ["front"],
        }

        views = view_mapping.get(request.viewMode or "4-view", ["front", "right", "back", "left"])

        # 查找生成的文件
        for view in views:
            # 尝试多种文件格式
            for ext in [".png", ".jpg", ".jpeg"]:
                file_path = output_path / f"{view}{ext}"
                if file_path.exists():
                    images[view] = image_to_base64(str(file_path))
                    break

        # 添加master图
        if "front" in images:
            images["master"] = images["front"]

        if not images:
            raise HTTPException(status_code=500, detail="No images generated")

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
        raise HTTPException(status_code=400, detail="Reference image is required")

    # 复用multiview逻辑，只是强制使用图生图
    request.useImageReferencePrompt = True
    return await generate_multiview(request)


@router.post("/extract/clothes")
async def extract_clothes(request: ExtractClothesRequest):
    """Extract clothes from character image"""
    if not request.image:
        raise HTTPException(status_code=400, detail="Image is required")

    try:
        import shutil
        from image_processor import remove_background

        asset_id = str(uuid.uuid4())
        output_dir = f"outputs/{asset_id}"
        os.makedirs(output_dir, exist_ok=True)

        # 保存上传的图片
        input_path = base64_to_temp_file(request.image, ".png")

        # 去除背景
        import cv2
        img = cv2.imread(input_path)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")

        # 去除背景
        result_img = remove_background(img)

        # 保存结果
        output_path = f"{output_dir}/extracted_clothes.png"
        cv2.imwrite(output_path, result_img)

        # 清理临时文件
        os.unlink(input_path)

        return ExtractClothesResponse(
            assetId=asset_id,
            status="success",
            originalImage=request.image,
            extractedClothes=image_to_base64(output_path),
            extractedProps=["道具1", "道具2"] if request.extractProps else None,
        )

    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Missing dependency: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edit/change-clothes")
async def change_clothes(request: ChangeClothesRequest):
    """Change character's clothes"""
    if not request.characterImage:
        raise HTTPException(status_code=400, detail="Character image is required")

    # 服装替换也是通过生成多视角来实现
    # 复用multiview逻辑，但使用原图作为参考
    try:
        from aiproxy_client import generate_character_multiview

        token = get_api_token()
        if not token:
            try:
                token = get_aiproxy_token()
            except:
                pass

        asset_id = str(uuid.uuid4())
        output_dir = f"outputs/{asset_id}"
        os.makedirs(output_dir, exist_ok=True)

        # 保存角色图片为临时文件
        char_path = base64_to_temp_file(request.characterImage, ".png")

        # 构建描述
        description = request.clothesDescription or "character with new clothes"

        # 调用生成
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

        # 清理临时文件
        os.unlink(char_path)

        # 查找生成的图片
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
            raise HTTPException(status_code=500, detail="No images generated")

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
        raise HTTPException(status_code=400, detail="Image is required")

    try:
        # 风格转换也通过生成多视角API实现
        # 使用强化的风格描述
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

        from aiproxy_client import generate_character_multiview

        token = get_api_token()
        if not token:
            try:
                token = get_aiproxy_token()
            except:
                pass

        asset_id = str(uuid.uuid4())
        output_dir = f"outputs/{asset_id}"
        os.makedirs(output_dir, exist_ok=True)

        # 保存原图
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

        # 找生成的图
        output_path = Path(output_dir)
        styled_image = None

        for ext in [".png", ".jpg", ".jpeg"]:
            files = list(output_path.glob(f"*{ext}"))
            if files:
                styled_image = image_to_base64(str(files[0]))
                break

        if not styled_image:
            raise HTTPException(status_code=500, detail="No styled image generated")

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
    """Get generation history"""
    return []


@router.get("/download/{asset_id}")
async def download_asset(asset_id: str):
    """Download generated assets"""
    output_dir = f"outputs/{asset_id}"
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"asset_id": asset_id, "path": output_dir}
