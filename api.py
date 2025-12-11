#!/usr/bin/env python3
"""
Mistral TTS API Server
REST API để sử dụng Mistral AI TTS
"""

import os
import asyncio
import uuid
import subprocess
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from mistralai import Mistral
import io
import json
import tempfile

# Import pydub với fallback
try:
    from pydub import AudioSegment
    from pydub.effects import normalize
    PYDUB_AVAILABLE = True
except ImportError as e:
    print(f"Warning: pydub không khả dụng: {e}. Chức năng điều chỉnh pitch sẽ bị giới hạn.")
    PYDUB_AVAILABLE = False
    AudioSegment = None
    normalize = None

import numpy as np

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


# Hàm sử dụng Mistral để phân tích text và đề xuất pitch adjustment
async def analyze_pitch_with_mistral(text: str, lang: str = "en") -> float:
    """
    Sử dụng Mistral AI CHỈ để phân tích text và đề xuất hệ số điều chỉnh pitch tối ưu
    
    Hàm này CHỈ phân tích pitch, không xử lý hay thay đổi text.
    Text được dùng trực tiếp cho gTTS sau khi có pitch factor.
    
    Args:
        text: Text gốc cần phân tích pitch (text này sẽ được dùng cho kokoro-tts)
        lang: Ngôn ngữ của text
    
    Returns:
        Hệ số pitch (1.0 = bình thường, >1.0 = cao hơn, <1.0 = thấp hơn)
    """
    if mistral_client is None:
        return 1.0  # Trả về pitch mặc định nếu không có Mistral client
    
    try:
        prompt = f"""Phân tích đoạn text sau và đề xuất hệ số điều chỉnh cao độ (pitch) tối ưu cho phát âm:
Text: "{text}"
Ngôn ngữ: {lang}

Hãy phân tích:
1. Loại nội dung (câu hỏi, câu khẳng định, câu cảm thán, v.v.)
2. Cảm xúc (vui, buồn, nghiêm túc, v.v.)
3. Độ dài và độ phức tạp
4. Đề xuất hệ số pitch (từ 0.8 đến 1.2, với 1.0 là bình thường)

Trả về JSON với format:
{{
    "pitch_factor": <số thực từ 0.8 đến 1.2>,
    "reasoning": "<lý do>"
}}"""
        
        response = mistral_client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content
        
        # Cố gắng parse JSON từ response
        try:
            # Tìm JSON trong response
            if "{" in result_text and "}" in result_text:
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                json_str = result_text[json_start:json_end]
                result = json.loads(json_str)
                pitch_factor = float(result.get("pitch_factor", 1.0))
                # Giới hạn pitch factor trong khoảng hợp lý
                return max(0.7, min(1.3, pitch_factor))
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        
        # Nếu không parse được, sử dụng heuristic đơn giản
        # Câu hỏi thường cần pitch cao hơn một chút
        if "?" in text:
            return 1.05
        # Câu cảm thán cần pitch cao hơn
        elif "!" in text:
            return 1.1
        # Text dài có thể cần pitch thấp hơn một chút
        elif len(text) > 100:
            return 0.95
        else:
            return 1.0
            
    except Exception as e:
        print(f"Lỗi khi phân tích pitch với Mistral: {e}")
        return 1.0


# Hàm điều chỉnh pitch của audio
def adjust_audio_pitch(audio, pitch_factor: float):
    """
    Điều chỉnh pitch của audio segment
    
    Args:
        audio: AudioSegment cần điều chỉnh
        pitch_factor: Hệ số điều chỉnh (1.0 = không đổi, >1.0 = cao hơn, <1.0 = thấp hơn)
    
    Returns:
        AudioSegment đã được điều chỉnh pitch
    """
    if not PYDUB_AVAILABLE or pitch_factor == 1.0:
        return audio
    
    # Sử dụng speedup/slowdown để điều chỉnh pitch
    # Tăng tốc độ = tăng pitch, giảm tốc độ = giảm pitch
    # Nhưng cần điều chỉnh lại thời lượng để giữ nguyên độ dài
    new_sample_rate = int(audio.frame_rate * pitch_factor)
    
    # Tạo audio mới với sample rate mới
    audio_with_new_pitch = audio._spawn(
        audio.raw_data,
        overrides={"frame_rate": new_sample_rate}
    )
    
    # Điều chỉnh lại về frame rate ban đầu để giữ nguyên thời lượng
    audio_with_new_pitch = audio_with_new_pitch.set_frame_rate(audio.frame_rate)
    
    return audio_with_new_pitch


# Hàm tạo audio với kokoro-tts và điều chỉnh pitch
async def create_audio_with_optimized_pitch(
    text: str,
    lang: str = "en",
    pitch_factor: Optional[float] = None,
    use_mistral: bool = True
) -> tuple[str, Optional[float]]:
    """
    Tạo audio từ text sử dụng kokoro-tts và điều chỉnh pitch dựa trên Mistral
    
    Lưu ý: Mistral CHỈ dùng để phân tích pitch từ text gốc, không xử lý text.
    kokoro-tts luôn dùng text gốc để tạo audio.
    
    Args:
        text: Text gốc cần chuyển đổi (luôn dùng text này cho kokoro-tts)
        lang: Ngôn ngữ (kokoro-tts hỗ trợ nhiều ngôn ngữ)
        pitch_factor: Hệ số pitch (nếu None sẽ dùng Mistral để tính từ text gốc)
        use_mistral: Có sử dụng Mistral để phân tích pitch không
    
    Returns:
        Tuple (file_path, pitch_factor_used)
    """
    # Tạo file tạm cho audio gốc
    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_mp3.close()
    
    try:
        # Tạo audio với kokoro-tts bằng subprocess
        # kokoro-tts có thể nhận input từ stdin hoặc file
        # Tạo file tạm cho text input
        temp_txt = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8')
        temp_txt.write(text)
        temp_txt.close()
        
        try:
            # Gọi kokoro-tts command với input file và output file
            # Format: kokoro-tts <input_file> <output_file> [options]
            # Chỉ định đường dẫn model files nếu có
            
            # Convert lang code: kokoro-tts cần format như "en-us", "en-gb", không phải "en"
            lang_map = {
                "en": "en-us",
                "vi": "cmn",  # Vietnamese -> Chinese (closest available)
                "fr": "fr-fr",
                "it": "it",
                "ja": "ja"
            }
            kokoro_lang = lang_map.get(lang.lower(), "en-us") if lang else "en-us"
            
            cmd = [
                "kokoro-tts",
                temp_txt.name,
                temp_mp3.name,
                "--format", "wav",
                "--lang", kokoro_lang,
                "--voice", "af_sarah"  # Chọn voice mặc định để tránh prompt tương tác
            ]
            
            # Thêm đường dẫn model files nếu có trong thư mục hiện tại
            model_path = Path.cwd() / "kokoro-v1.0.onnx"
            voices_path = Path.cwd() / "voices-v1.0.bin"
            if model_path.exists() and voices_path.exists():
                cmd.extend(["--model", str(model_path), "--voices", str(voices_path)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=60,  # Tăng timeout vì kokoro-tts có thể mất thời gian
                cwd=str(Path.cwd())  # Chạy từ thư mục dự án để tìm model files
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else ""
            stdout_msg = e.stdout.decode('utf-8', errors='ignore') if e.stdout else ""
            full_error = f"kokoro-tts failed (exit code {e.returncode}): {error_msg}\nSTDOUT: {stdout_msg}"
            print(f"DEBUG kokoro-tts error: {full_error}")
            raise Exception(f"kokoro-tts failed: {full_error}")
        except FileNotFoundError:
            raise Exception("kokoro-tts không được tìm thấy. Vui lòng cài đặt: pip install kokoro-tts")
        except subprocess.TimeoutExpired:
            raise Exception("kokoro-tts timeout sau 30 giây")
        finally:
            # Xóa file text tạm
            if os.path.exists(temp_txt.name):
                os.unlink(temp_txt.name)
        
        # Điều chỉnh pitch nếu cần - Mistral CHỈ dùng để phân tích pitch từ text gốc
        print(f"DEBUG: pitch_factor={pitch_factor}, use_mistral={use_mistral}")
        if pitch_factor is None and use_mistral:
            print(f"DEBUG: Gọi Mistral để phân tích pitch cho text: {text[:50]}...")
            pitch_factor = await analyze_pitch_with_mistral(text, lang)
            print(f"DEBUG: Mistral trả về pitch_factor: {pitch_factor}")
        elif pitch_factor is None:
            print(f"DEBUG: Không gọi Mistral (use_mistral={use_mistral}), dùng pitch mặc định 1.0")
            pitch_factor = 1.0
        
        if pitch_factor is None:
            pitch_factor = 1.0
        
        # Thử load và xử lý audio với pydub nếu có
        if PYDUB_AVAILABLE:
            try:
                # kokoro-tts tạo file WAV, không phải MP3
                audio = AudioSegment.from_wav(temp_mp3.name)
                
                # Điều chỉnh pitch nếu cần và khác 1.0
                if pitch_factor != 1.0:
                    try:
                        audio = adjust_audio_pitch(audio, pitch_factor)
                    except Exception as e:
                        print(f"Warning: Không thể điều chỉnh pitch: {e}. Sử dụng audio gốc.")
                        # Fallback: sử dụng audio gốc nếu không thể điều chỉnh pitch
                
                # Normalize audio
                try:
                    if normalize:
                        audio = normalize(audio)
                except Exception as e:
                    print(f"Warning: Không thể normalize audio: {e}")
                
                # Lưu file cuối cùng (convert sang MP3)
                output_filename = f"{uuid.uuid4().hex}.mp3"
                output_path = AUDIO_DIR / output_filename
                audio.export(str(output_path), format="mp3")
            except Exception as e:
                # Nếu không thể xử lý với pydub, chỉ copy file gốc
                print(f"Warning: Không thể xử lý audio với pydub: {e}. Sử dụng audio gốc từ kokoro-tts.")
                output_filename = f"{uuid.uuid4().hex}.wav"
                output_path = AUDIO_DIR / output_filename
                import shutil
                shutil.copy2(temp_mp3.name, str(output_path))
        else:
            # Nếu không có pydub, chỉ copy file gốc
            output_filename = f"{uuid.uuid4().hex}.wav"
            output_path = AUDIO_DIR / output_filename
            import shutil
            shutil.copy2(temp_mp3.name, str(output_path))
        
        return output_filename, pitch_factor
        
    finally:
        # Xóa file tạm
        if os.path.exists(temp_mp3.name):
            os.unlink(temp_mp3.name)


# Request models
class TTSRequest(BaseModel):
    text: str
    model: Optional[str] = "mistral-small-latest"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    lang: Optional[str] = "en"  # Ngôn ngữ (en = tiếng Anh)
    use_mistral: Optional[bool] = False  # Sử dụng Mistral để xử lý text (mặc định: false - chỉ dùng cho pitch)
    return_audio: Optional[bool] = False  # Trả về file âm thanh hay JSON (mặc định: false)
    optimize_pitch: Optional[bool] = True  # Sử dụng Mistral để phân tích và tối ưu hóa pitch (mặc định: true)
    pitch_factor: Optional[float] = None  # Hệ số điều chỉnh pitch (nếu None sẽ dùng Mistral để tính từ text gốc)


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
            "tts_audio": "/api/v1/tts/audio",
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
    Tạo audio từ text với kokoro-tts, sử dụng Mistral AI CHỈ để phân tích và điều chỉnh pitch
    
    - kokoro-tts luôn dùng text gốc (request.text) để tạo audio
    - Mistral chỉ dùng để phân tích pitch từ text gốc (nếu optimize_pitch=True)
    - use_mistral chỉ dùng để xử lý text (không ảnh hưởng đến audio)
    
    Args:
        request: TTSRequest chứa text và các tham số
    
    Returns:
        JSON response với text đã xử lý (nếu use_mistral=True) và audio file (nếu return_audio=True)
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text không được để trống")
    
    print(f"DEBUG: request.return_audio = {request.return_audio}, type = {type(request.return_audio)}")
    
    try:
        text_to_convert = request.text
        mistral_usage = None
        audio_filename = None
        pitch_factor_used = None
        
        # Sử dụng Mistral để xử lý text
        if request.use_mistral:
            if mistral_client is None:
                raise HTTPException(status_code=503, detail="Mistral client chưa được khởi tạo")
            
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
        
        # Tạo audio nếu được yêu cầu
        # LUÔN dùng text gốc để tạo audio, Mistral chỉ dùng để phân tích pitch
        audio_filename = None
        pitch_factor_used = None
        if request.return_audio:
            print(f"DEBUG: Creating audio for original text: {request.text[:50]}...")
            try:
                audio_filename, pitch_factor_used = await create_audio_with_optimized_pitch(
                    text=request.text,  # Luôn dùng text gốc, không dùng processed_text
                    lang=request.lang,
                    pitch_factor=request.pitch_factor,
                    use_mistral=request.optimize_pitch  # Mistral chỉ dùng để phân tích pitch
                )
                print(f"DEBUG: Audio created successfully: {audio_filename}, pitch: {pitch_factor_used}")
            except Exception as e:
                print(f"ERROR creating audio: {e}")
                import traceback
                traceback.print_exc()
                # Vẫn trả về response nhưng không có audio
                audio_filename = None
                pitch_factor_used = None
        else:
            print("DEBUG: return_audio is False, skipping audio creation")
        
        # Trả về JSON response
        result = {
            "success": True,
            "text": request.text,
            "processed_text": text_to_convert if request.use_mistral else request.text,
            "lang": request.lang,
            "usage": mistral_usage,
            "audio_file": audio_filename if request.return_audio and audio_filename else None,
            "audio_url": f"/api/v1/audio/{audio_filename}" if audio_filename else None,
            "pitch_factor": pitch_factor_used
        }
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
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




@app.post("/api/v1/tts/audio")
async def text_to_speech_audio(request: TTSRequest):
    """
    Tạo audio từ text với gTTS, sử dụng Mistral AI CHỈ để phân tích và điều chỉnh pitch
    
    - gTTS luôn dùng text gốc (request.text) để tạo audio
    - Mistral chỉ dùng để phân tích pitch từ text gốc (nếu optimize_pitch=True)
    - Trả về file audio trực tiếp
    
    Args:
        request: TTSRequest chứa text và các tham số
    
    Returns:
        File audio MP3
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text không được để trống")
    
    try:
        text_to_convert = request.text
        mistral_usage = None
        
        # Sử dụng Mistral để xử lý text nếu được yêu cầu (chỉ cho text processing, không ảnh hưởng audio)
        if request.use_mistral:
            if mistral_client is None:
                raise HTTPException(status_code=503, detail="Mistral client chưa được khởi tạo")
            
            response = mistral_client.chat.complete(
                model=request.model,
                messages=[
                    {"role": "user", "content": request.text}
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            text_to_convert = response.choices[0].message.content
            mistral_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        
        # Tạo audio với pitch được tối ưu
        # LUÔN dùng text gốc để tạo audio, Mistral chỉ dùng để phân tích pitch
        audio_filename, pitch_factor_used = await create_audio_with_optimized_pitch(
            text=request.text,  # Luôn dùng text gốc, không dùng processed_text
            lang=request.lang,
            pitch_factor=request.pitch_factor,
            use_mistral=request.optimize_pitch  # Mistral chỉ dùng để phân tích pitch
        )
        
        audio_path = AUDIO_DIR / audio_filename
        
        # Trả về file audio hoặc JSON tùy vào query parameter
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            headers={
                "X-Original-Text": request.text,
                "X-Processed-Text": text_to_convert,
                "X-Pitch-Factor": str(pitch_factor_used),
                "X-Audio-Filename": audio_filename
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo audio: {str(e)}")


@app.get("/api/v1/audio/{filename}")
async def get_audio_file(filename: str):
    """Lấy file âm thanh đã tạo"""
    audio_path = AUDIO_DIR / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="File không tồn tại")
    
    # Xác định media type dựa trên extension
    if filename.endswith('.wav'):
        media_type = "audio/wav"
    elif filename.endswith('.mp3'):
        media_type = "audio/mpeg"
    else:
        media_type = "audio/mpeg"
    
    return FileResponse(audio_path, media_type=media_type)


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

