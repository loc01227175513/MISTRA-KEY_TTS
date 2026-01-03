#!/usr/bin/env python3
"""
TTS API Server
REST API để tạo audio với kokoro-tts
"""

import os
import uuid
import subprocess
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
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

# Tạo thư mục để lưu file âm thanh
AUDIO_DIR = Path("audio_files")
AUDIO_DIR.mkdir(exist_ok=True)

# Khởi tạo FastAPI app
app = FastAPI(
    title="Kokoro TTS API",
    description="API để tạo audio từ text với kokoro-tts",
    version="1.0.0"
)


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
    pitch_factor: Optional[float] = None
) -> tuple[str, Optional[float]]:
    """
    Tạo audio từ text sử dụng kokoro-tts và (tuỳ chọn) điều chỉnh pitch.
    
    Args:
        text: Text gốc cần chuyển đổi (luôn dùng text này cho kokoro-tts)
        lang: Ngôn ngữ (kokoro-tts hỗ trợ nhiều ngôn ngữ)
        pitch_factor: Hệ số pitch (nếu None sẽ dùng mặc định 1.0)
    
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
        
        # Điều chỉnh pitch nếu cần
        print(f"DEBUG: pitch_factor={pitch_factor}")
        if pitch_factor is None:
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
    lang: Optional[str] = "en"  # Ngôn ngữ (en = tiếng Anh)
    return_audio: Optional[bool] = False  # Trả về file âm thanh hay JSON (mặc định: false)
    pitch_factor: Optional[float] = None  # Hệ số điều chỉnh pitch (mặc định 1.0 nếu None)


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Kokoro TTS API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "tts": "/api/v1/tts",
            "tts_audio": "/api/v1/tts/audio",
            "languages": "/api/v1/languages",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}




@app.post("/api/v1/tts")
async def text_to_speech(request: TTSRequest):
    """
    Tạo audio từ text với kokoro-tts.
    
    Args:
        request: TTSRequest chứa text và các tham số
    
    Returns:
        JSON response và audio file (nếu return_audio=True)
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text không được để trống")
    
    print(f"DEBUG: request.return_audio = {request.return_audio}, type = {type(request.return_audio)}")
    
    try:
        audio_filename = None
        pitch_factor_used = None
        
        # Tạo audio nếu được yêu cầu
        audio_filename = None
        pitch_factor_used = None
        if request.return_audio:
            print(f"DEBUG: Creating audio for original text: {request.text[:50]}...")
            try:
                audio_filename, pitch_factor_used = await create_audio_with_optimized_pitch(
                    text=request.text,  # Luôn dùng text gốc, không dùng processed_text
                    lang=request.lang,
                    pitch_factor=request.pitch_factor
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
            "processed_text": request.text,
            "lang": request.lang,
            "usage": None,
            "audio_file": audio_filename if request.return_audio and audio_filename else None,
            "audio_url": f"/api/v1/audio/{audio_filename}" if audio_filename else None,
            "pitch_factor": pitch_factor_used
        }
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý: {str(e)}")


@app.post("/api/v1/tts/audio")
async def text_to_speech_audio(request: TTSRequest):
    """
    Tạo audio từ text với kokoro-tts và trả về file audio trực tiếp.
    
    Args:
        request: TTSRequest chứa text và các tham số
    
    Returns:
        File audio MP3
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text không được để trống")
    
    try:
        # Tạo audio
        audio_filename, pitch_factor_used = await create_audio_with_optimized_pitch(
            text=request.text,  # Luôn dùng text gốc, không dùng processed_text
            lang=request.lang,
            pitch_factor=request.pitch_factor
        )
        
        audio_path = AUDIO_DIR / audio_filename
        
        # Trả về file audio hoặc JSON tùy vào query parameter
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            headers={
                "X-Original-Text": request.text,
                "X-Processed-Text": request.text,
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
        {"code": "en", "name": "English", "engines": ["kokoro-tts"]},
    ]
    
    return {
        "success": True,
        "count": len(languages),
        "languages": languages
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

