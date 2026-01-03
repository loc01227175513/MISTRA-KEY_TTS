# TTS API với kokoro-tts

Dự án này cung cấp REST API để tạo audio từ text bằng `kokoro-tts`. Có hỗ trợ điều chỉnh cao độ (pitch) bằng tham số `pitch_factor`.

## Cài đặt

1. **Tạo virtual environment (khuyến nghị):**
```bash
python3 -m venv venv
source venv/bin/activate  # Trên macOS/Linux
# hoặc
venv\Scripts\activate  # Trên Windows
```

2. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```



## Sử dụng

### Chạy API Server:

**Khởi động server:**
```bash
# Cách 1: Sử dụng Python
python api.py

# Cách 2: Sử dụng uvicorn (khuyến nghị)
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy tại: `http://localhost:8000`

**API Documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Test API:** dùng `curl` hoặc gọi trực tiếp các endpoint bên dưới.

### API Endpoints

**1. Tạo audio và trả về JSON (tuỳ chọn tạo file audio):**
```bash
POST http://localhost:8000/api/v1/tts
Content-Type: application/json

{
  "text": "Hello, this is a test",
  "return_audio": true,
  "lang": "en",
  "pitch_factor": 1.0
}
```

**1b. Tạo audio trực tiếp (chỉ trả về file audio):**
```bash
POST http://localhost:8000/api/v1/tts/audio
Content-Type: application/json

{
  "text": "Hello, this is a test",
  "lang": "en",
  "pitch_factor": 1.0
}
```

**2. List Languages:**
```bash
GET http://localhost:8000/api/v1/languages
```

**3. Lấy file audio đã tạo:**
```bash
GET http://localhost:8000/api/v1/audio/{filename}
```

## Pitch

Bạn có thể chỉ định `pitch_factor` (ví dụ `1.05`) để tăng pitch hoặc `0.95` để giảm pitch. Nếu không truyền, hệ thống dùng `1.0`.

## Ví dụ sử dụng với cURL

```bash
# Tạo audio và lấy JSON kết quả
curl -X POST "http://localhost:8000/api/v1/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test",
    "return_audio": true,
    "lang": "en",
    "pitch_factor": 1.0
  }'

# Tạo audio trực tiếp (download file)
curl -X POST "http://localhost:8000/api/v1/tts/audio" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test", "lang": "en", "pitch_factor": 1.0}' \
  --output output.mp3
```

## Ví dụ sử dụng với Python

```python
import requests

# Tạo audio và lấy JSON kết quả
response = requests.post(
    "http://localhost:8000/api/v1/tts",
    json={
        "text": "Hello, this is a test",
        "return_audio": True,
    "lang": "en",
    "pitch_factor": 1.0
    }
)
result = response.json()
print(f"Processed text: {result['processed_text']}")
print(f"Pitch factor: {result['pitch_factor']}")
print(f"Audio URL: {result['audio_url']}")

# Tải file audio
if result['audio_url']:
    audio_response = requests.get(f"http://localhost:8000{result['audio_url']}")
    with open("output.mp3", "wb") as f:
        f.write(audio_response.content)
    print("Audio saved to output.mp3")

# Tạo audio trực tiếp
response = requests.post(
    "http://localhost:8000/api/v1/tts/audio",
    json={
        "text": "What is artificial intelligence?",
    "lang": "en",
    "pitch_factor": 1.05
    }
)
with open("ai_question.mp3", "wb") as f:
    f.write(response.content)
print("Audio saved to ai_question.mp3")
```

## Các tham số API

### TTSRequest

- `text` (required): Text cần chuyển đổi
- `lang` (optional, default: "en"): Ngôn ngữ (en, vi, fr, de, v.v.)
- `return_audio` (optional, default: false): Trả về thông tin audio trong JSON response
- `pitch_factor` (optional, default: None): Hệ số pitch (1.0 là bình thường)

## Tài liệu tham khảo

- [kokoro-tts GitHub](https://github.com/nazdridoy/kokoro-tts)
- [pydub Documentation](https://github.com/jiaaro/pydub)
