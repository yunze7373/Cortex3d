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
    """将base64图片保存到临时文件，不打印base64内容"""
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
import json
import asyncio
from fastapi.responses import StreamingResponse

def get_api_token() -> str:
    """从环境变量获取API token"""
    return os.environ.get("AIPROXY_TOKEN", "")

# ============ 辅助函数 ============

def create_ndjson_event(event_type: str, data: dict = None, message: str = None, progress: int = None) -> str:
    """创建 NDJSON 的单行记录"""
    payload = {"type": event_type}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    if progress is not None:
        payload["progress"] = progress
    return json.dumps(payload, ensure_ascii=False) + "\n"

# ============ API 端点 ============

@router.post("/generate/multiview")
async def generate_multiview(request: GenerateRequest):
    """Generate multi-view images from text description (Streaming NDJSON)"""
    
    async def event_generator():
        try:
            from aiproxy_client import generate_character_multiview

            token = get_api_token()
            if not token:
                yield create_ndjson_event("error", message="请设置 AIPROXY_TOKEN 环境变量")
                return

            asset_id = str(uuid.uuid4())
            output_dir = str(project_root / "outputs" / asset_id)

            os.makedirs(output_dir, exist_ok=True)

            # 处理参考图片（如果是base64则保存到临时文件）
            reference_image_path = None
            if request.referenceImage:
                reference_image_path = base64_to_temp_file(request.referenceImage, ".png")

            print(f"[生成多视角] 开始生成, description={request.description[:50]}...")
            yield create_ndjson_event("progress", message="正在准备请求...", progress=1)

            # 建立一个队列用于同步非阻塞线程与异步生成器之间的进度信息
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            
            def progress_callback(msg: str, percent: int):
                # 从另一个线程安全地推送到异步队列
                loop.call_soon_threadsafe(queue.put_nowait, {"msg": msg, "percent": percent})
            
            # 清理自定义视图字符串，处理全角/半角逗号，将单字符串转为列表
            clean_custom_views = None
            if request.customViews:
                clean_custom_views = []
                for v in request.customViews:
                    # 替换全角逗号为半角逗号，并分割
                    parts = str(v).replace('，', ',').split(',')
                    for p in parts:
                        clean_p = p.strip().lower()
                        if clean_p:
                            clean_custom_views.append(clean_p)
                # 如果清理后为空，则设为None回退到默认
                if not clean_custom_views:
                    clean_custom_views = None

            # 使用 asyncio.to_thread 运行阻塞的生成函数
            def sync_generate():
                return generate_character_multiview(
                    character_description=request.description,
                    token=token,
                    output_dir=output_dir,
                    auto_cut=True,
                    model=request.model or "gemini-3-pro-image-preview",
                    style=request.style or "cinematic character",
                    asset_id=asset_id,
                    reference_image_path=reference_image_path,
                    use_image_reference_prompt=request.useImageReferencePrompt,
                    use_strict_mode=request.useStrictMode,
                    resolution=request.resolution or "2K",
                    view_mode=request.viewMode or "4-view",
                    custom_views=clean_custom_views,
                    use_negative_prompt=request.useNegativePrompt,
                    negative_categories=request.negativeCategories,
                    subject_only=request.subjectOnly,
                    with_props=request.withProps,
                    progress_callback=progress_callback
                )

            # 启动工作线程
            task = asyncio.create_task(asyncio.to_thread(sync_generate))
            
            # 持续监听队列更新，同时关注任务是否完成
            while not task.done():
                try:
                    # 等待队列消息，设置超时以便定期检查 task 状态
                    update = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield create_ndjson_event("progress", message=update["msg"], progress=update["percent"])
                except asyncio.TimeoutError:
                    yield "\n" # 发送空行作为 heartbeat 保持流连接活跃

            # 获取返回值或抛出异常
            result = task.result()
            
            # 清空剩余的队列内容
            while not queue.empty():
                update = queue.get_nowait()
                yield create_ndjson_event("progress", message=update["msg"], progress=update["percent"])

            # 清理临时参考图片
            if reference_image_path:
                try:
                    os.unlink(reference_image_path)
                except:
                    pass

            if not result:
                yield create_ndjson_event("error", message="图像生成失败")
                return

            # 查找生成的图片
            images = {}
            output_path = Path(output_dir)

            view_mapping = {
                "single": ["front"],
                "4-view": ["front", "right", "back", "left"],
                "6-view": ["front", "frontRight", "right", "back", "left", "frontLeft"],
                "8-view": ["front", "frontRight", "right", "backRight", "back", "backLeft", "left", "frontLeft"],
                "custom": clean_custom_views or ["front"],
            }

            views = view_mapping.get(request.viewMode or "4-view", ["front", "right", "back", "left"])

            yield create_ndjson_event("progress", message="正在构建响应数据...", progress=95)

            # 使用asset_id前缀来查找文件
            for i, view in enumerate(views):
                # 将 camelCase 转换为 snake_case 以匹配底层切割生成的文件名 (如 frontRight -> front_right)
                snake_view = view.replace("Right", "_right").replace("Left", "_left")

                # 尝试通用的命名方式 (assetId_view.png)
                potential_paths = [
                    output_path / f"{asset_id}_{view}.png",
                    output_path / f"{asset_id}_{view}.jpg",
                    output_path / f"{asset_id}_{view}.jpeg",
                    output_path / f"{view}.png",
                    output_path / f"{view}.jpg",
                    output_path / f"{view}.jpeg",
                    # 尝试 snake_case 版本 (例如 front_right.png)
                    output_path / f"{asset_id}_{snake_view}.png",
                    output_path / f"{asset_id}_{snake_view}.jpg",
                    output_path / f"{asset_id}_{snake_view}.jpeg",
                    output_path / f"{snake_view}.png",
                    output_path / f"{snake_view}.jpg",
                    output_path / f"{snake_view}.jpeg",
                ]
                
                # 如果是 custom mode 或者是其他非标准个数模式，底层切割算法可能输出为 _view_1, _view_2
                view_index = i + 1
                potential_paths.extend([
                    output_path / f"{asset_id}_view_{view_index}.png",
                    output_path / f"{asset_id}_view_{view_index}.jpg",
                    output_path / f"view_{view_index}.png",
                    output_path / f"view_{view_index}.jpg",
                ])

                for file_path in potential_paths:
                    if file_path.exists():
                        images[view] = image_to_base64(str(file_path))
                        break

            if "front" in images:
                images["master"] = images["front"]

            if not images:
                yield create_ndjson_event("error", message="未找到生成的图片")
                return

            print(f"[生成多视角] 成功, views={list(images.keys())}")
            
            # 返回最终完成的事件
            response_str = create_ndjson_event("result", data={
                "assetId": asset_id,
                "status": "success",
                "images": images,
                "metadata": {
                    "description": request.description,
                    "style": request.style,
                    "model": request.model,
                    "createdAt": "2024-01-01T00:00:00Z",
                },
            }, message="生成完毕", progress=100)
            
            # 分块发送避免单次巨量 payload 导致网络层或代理层截断
            chunk_size = 1024 * 1024  # 1MB
            for i in range(0, len(response_str), chunk_size):
                yield response_str[i:i + chunk_size]

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield create_ndjson_event("error", message=f"服务器内部异常: {str(e)}")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.post("/generate/from-image")
async def generate_from_image(request: GenerateRequest):
    """Generate multi-view images from reference image"""
    if not request.referenceImage:
        raise HTTPException(status_code=400, detail="需要上传参考图片")

    print(f"[图生多视角] 开始处理...")
    request.useImageReferencePrompt = True
    return await generate_multiview(request)


@router.post("/extract/clothes")
async def extract_clothes(request: ExtractClothesRequest):
    """Extract clothes from character image - 使用智能提取 (Streaming NDJSON)"""
    
    async def event_generator():
        try:
            if not request.image:
                yield create_ndjson_event("error", message="需要上传图片")
                return

            from gemini_generator import smart_extract_clothing

            token = get_api_token()
            if not token:
                yield create_ndjson_event("error", message="请设置 AIPROXY_TOKEN 环境变量")
                return

            asset_id = str(uuid.uuid4())
            output_dir = str(project_root / "outputs" / asset_id)
            os.makedirs(output_dir, exist_ok=True)

            print(f"[提取衣服] 开始处理 (智能提取)...")
            yield create_ndjson_event("progress", message="正在接收并保存上传的图像...", progress=1)

            # 保存上传的图片
            input_path = base64_to_temp_file(request.image, ".png")

            # 建立一个队列用于同步非阻塞线程与异步生成器之间的进度信息
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            
            def progress_callback(msg: str, percent: int):
                loop.call_soon_threadsafe(queue.put_nowait, {"msg": msg, "percent": percent})

            def sync_extract():
                # 使用智能提取函数（会自动分析图片内容并选择最佳处理方式）
                return smart_extract_clothing(
                    image_path=input_path,
                    api_key=token,
                    model_name="gemini-2.5-flash-image",
                    output_dir=output_dir,
                    mode="proxy",
                    extract_props=request.extractProps,
                    progress_callback=progress_callback
                )

            # 启动工作线程
            task = asyncio.create_task(asyncio.to_thread(sync_extract))
            
            # 持续监听队列更新，同时关注任务是否完成
            while not task.done():
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield create_ndjson_event("progress", message=update["msg"], progress=update["percent"])
                except asyncio.TimeoutError:
                    yield "\n" # 发送空行作为 heartbeat 保持流连接活跃

            # 获取返回值或抛出异常
            result = task.result()
            
            # 清空剩余的队列内容
            while not queue.empty():
                update = queue.get_nowait()
                yield create_ndjson_event("progress", message=update["msg"], progress=update["percent"])

            extracted_path = None
            extracted_props = None
            if result:
                 extracted_path, extracted_props = result

            # 清理临时输入文件
            try:
                os.unlink(input_path)
            except:
                pass

            if not extracted_path or not Path(extracted_path).exists():
                yield create_ndjson_event("error", message="衣服提取失败")
                return

            yield create_ndjson_event("progress", message="正在构建响应数据...", progress=95)

            print(f"[提取衣服] 成功: {extracted_path}, 道具: {extracted_props}")
            response_str = create_ndjson_event("result", data={
                "assetId": asset_id,
                "status": "success",
                "originalImage": request.image,
                "extractedClothes": image_to_base64(extracted_path),
                "extractedProps": extracted_props,
            }, message="提取完毕", progress=100)
            
            # 分块发送避免截断
            chunk_size = 1024 * 1024  # 1MB
            for i in range(0, len(response_str), chunk_size):
                yield response_str[i:i + chunk_size]

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield create_ndjson_event("error", message=f"服务器内部异常: {str(e)}")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.post("/edit/change-clothes")
async def change_clothes(request: ChangeClothesRequest):
    """Change character's clothes"""
    if not request.characterImage:
        raise HTTPException(status_code=400, detail="需要上传角色图片")

    try:
        from gemini_generator import composite_images

        token = get_api_token()
        if not token:
            raise HTTPException(status_code=400, detail="请设置 AIPROXY_TOKEN 环境变量")

        asset_id = str(uuid.uuid4())
        output_dir = str(project_root / "outputs" / asset_id)
        os.makedirs(output_dir, exist_ok=True)

        print(f"[换装] 开始单图换装处理...")

        # 保存角色图片
        char_path = base64_to_temp_file(request.characterImage, ".png")
        image_paths = [char_path]

        # 检查是否有衣服图片 (图生图换装)
        if request.clothesImage:
            clothes_path = base64_to_temp_file(request.clothesImage, ".png")
            image_paths.append(clothes_path)

        # 构建指令
        instruction = request.clothesDescription or ""
        if not instruction and len(image_paths) > 1:
            instruction = "为角色换上另一张图片里的衣服"
        elif not instruction:
            instruction = "character with new clothes"

        # 决定合成类型
        composite_type = "clothing" if len(image_paths) > 1 else "clothing_text"

        result = composite_images(
            image_paths=image_paths,
            instruction=instruction,
            api_key=token,
            model_name="gemini-3-pro-image-preview",
            output_dir=output_dir,
            output_name=f"{asset_id}.jpg",
            mode="proxy",
            composite_type=composite_type,
            resolution="2K"
        )

        for path in image_paths:
            try:
                os.unlink(path)
            except:
                pass

        if not result:
            raise HTTPException(status_code=500, detail="换装生成失败")

        # 将生成的单张图片作为主图返回，放在 front 和 master 键下
        output_base64 = image_to_base64(result)
        
        images = {
            "master": output_base64,
            "front": output_base64
        }

        print(f"[换装] 成功")
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

        print(f"[风格转换] 开始处理 style={request.style}")

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

        try:
            os.unlink(img_path)
        except:
            pass

        output_path = Path(output_dir)
        styled_image = None

        for ext in [".png", ".jpg", ".jpeg"]:
            files = list(output_path.glob(f"*{ext}"))
            if files:
                styled_image = image_to_base64(str(files[0]))
                break

        if not styled_image:
            raise HTTPException(status_code=500, detail="风格转换失败")

        print(f"[风格转换] 成功")
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
