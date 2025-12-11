#!/usr/bin/env python3
"""
Mistral TTS API Server
REST API để sử dụng Mistral AI TTS
"""

import os
import asyncio
import uuid
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from mistralai import Mistral
import io

# Load environment variables
load_dotenv()

# Lấy API keys
API_KEY = os.getenv("MISTRAL_API_KEY") or "O3EI2wp2X2MekBLookmnOanLA9UohV9Z"

# Tạo thư mục để lưu file âm thanh
AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)

# Khởi tạo FastAPI app
app = FastAPI(
    title="Mistral TTS API",
    description="API để sử dụng Mistral AI Text-to-Speech với file âm thanh",
    version="1.0.0"
)

# Khởi tạo Mistral client
try:
    mistral_client = Mistral(api_key=API_KEY)
except Exception as e:
    print(f"Lỗi khi khởi tạo Mistral client: {e}")
    mistral_client = None



# Request models
class TTSRequest(BaseModel):
    text: str
    model: Optional[str] = "mistral-small-latest"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    lang: Optional[str] = "en"  # Ngôn ngữ (en = tiếng Anh)
    use_mistral: Optional[bool] = True  # Sử dụng Mistral để xử lý text (mặc định: true)
    return_audio: Optional[bool] = False  # Trả về file âm thanh hay JSON (mặc định: false vì không có TTS engine)


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "mistral-small-latest"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Mistral TTS API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "tts": "/api/v1/tts",
            "tts_mistral": "/api/v1/tts/mistral",
            "chat": "/api/v1/chat",
            "models": "/api/v1/models",
            "languages": "/api/v1/languages",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if mistral_client is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Mistral client không được khởi tạo"}
        )
    return {"status": "healthy", "api_key_configured": bool(API_KEY)}




@app.post("/api/v1/tts")
async def text_to_speech(request: TTSRequest):
    """
    Sử dụng Mistral AI để xử lý text
    
    Args:
        request: TTSRequest chứa text và các tham số
    
    Returns:
        JSON response với text đã xử lý
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text không được để trống")
    
    if mistral_client is None:
        raise HTTPException(status_code=503, detail="Mistral client chưa được khởi tạo")
    
    try:
        text_to_convert = request.text
        mistral_usage = None
        
        # Sử dụng Mistral để xử lý text
        if request.use_mistral:
            # Gọi Mistral API để xử lý text
            response = mistral_client.chat.complete(
                model=request.model,
                messages=[
                    {"role": "user", "content": request.text}
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            # Lấy text từ response
            text_to_convert = response.choices[0].message.content
            mistral_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        # Trả về JSON response
        result = {
            "success": True,
            "text": request.text,
            "processed_text": text_to_convert if request.use_mistral else request.text,
            "lang": request.lang,
            "usage": mistral_usage
        }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý: {str(e)}")


@app.post("/api/v1/tts/mistral")
async def text_to_speech_mistral(request: TTSRequest):
    """
    Sử dụng Mistral AI để xử lý text
    Endpoint đơn giản để sử dụng Mistral
    
    Args:
        request: TTSRequest chứa text và các tham số
    
    Returns:
        JSON response với text đã xử lý
    """
    if mistral_client is None:
        raise HTTPException(status_code=503, detail="Mistral client chưa được khởi tạo")
    
    if not request.text:
        raise HTTPException(status_code=400, detail="Text không được để trống")
    
    try:
        # Gọi Mistral API để xử lý text
        response = mistral_client.chat.complete(
            model=request.model,
            messages=[
                {"role": "user", "content": request.text}
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Lấy text từ response
        processed_text = response.choices[0].message.content
        
        # Trả về JSON với thông tin đầy đủ
        return {
            "success": True,
            "model": response.model,
            "original_text": request.text,
            "processed_text": processed_text,
            "lang": request.lang,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý: {str(e)}")




@app.get("/api/v1/audio/{filename}")
async def get_audio_file(filename: str):
    """Lấy file âm thanh đã tạo"""
    audio_path = AUDIO_DIR / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    return FileResponse(audio_path, media_type="audio/mpeg")


@app.get("/api/v1/languages")
async def list_languages():
    """
    Liệt kê các ngôn ngữ được hỗ trợ
    
    Returns:
        Danh sách ngôn ngữ
    """
    languages = [
        {"code": "en", "name": "English", "engines": ["mistral"]},
    ]
    
    return {
        "success": True,
        "count": len(languages),
        "languages": languages
    }






@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """
    Chat với Mistral AI
    
    Args:
        request: ChatRequest chứa message và các tham số
    
    Returns:
        Response từ Mistral API
    """
    if mistral_client is None:
        raise HTTPException(status_code=503, detail="Mistral client chưa được khởi tạo")
    
    if not request.message:
        raise HTTPException(status_code=400, detail="Message không được để trống")
    
    try:
        response = mistral_client.chat.complete(
            model=request.model,
            messages=[
                {"role": "user", "content": request.message}
            ],
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return {
            "success": True,
            "model": response.model,
            "message": request.message,
            "response": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gọi Mistral API: {str(e)}")


@app.get("/api/v1/models")
async def list_models():
    """
    Liệt kê các models có sẵn
    
    Returns:
        Danh sách models
    """
    if mistral_client is None:
        raise HTTPException(status_code=503, detail="Mistral client chưa được khởi tạo")
    
    try:
        models = mistral_client.models.list()
        return {
            "success": True,
            "count": len(models.data),
            "models": [{"id": model.id, "object": model.object} for model in models.data]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lấy danh sách models: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

