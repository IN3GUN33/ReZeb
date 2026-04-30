from fastapi import APIRouter, Depends, File, UploadFile
from app.core import aitunnel
from app.core.config import get_settings

router = APIRouter(prefix="/test", tags=["test"])
settings = get_settings()

@router.post("/llm")
async def test_llm(text: str):
    messages = [{"role": "user", "content": text}]
    content, usage = await aitunnel.chat_completion(
        model=settings.model_vision,
        messages=messages
    )
    return {"response": content, "usage": usage.__dict__}

@router.post("/vision")
async def test_vision(file: UploadFile = File(...)):
    data = await file.read()
    content, usage = await aitunnel.vision_completion(
        model=settings.model_vision,
        text_prompt="Describe what you see in this construction photo. Focus on structural elements and potential defects.",
        image_bytes=data
    )
    return {"response": content, "usage": usage.__dict__}
