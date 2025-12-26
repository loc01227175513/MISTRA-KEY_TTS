# Mistral TTS API với kokoro-tts và Pitch Optimization

Dự án này cung cấp REST API để sử dụng Mistral AI để xử lý text và tạo audio với kokoro-tts, với khả năng điều chỉnh cao độ (pitch) tự động dựa trên phân tích của Mistral AI để đạt phát âm tốt nhất.

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

**Test API:**
```bash
# Chạy script test
python test_api.py
```

### API Endpoints

**1. Xử lý text với Mistral và tạo audio (với pitch optimization):**
```bash
POST http://localhost:8000/api/v1/tts
Content-Type: application/json

{
  "text": "Hello, this is a test",
  "use_mistral": true,
  "return_audio": true,
  "optimize_pitch": true,
  "lang": "en",
  "model": "mistral-small-latest",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**1b. Tạo audio trực tiếp (chỉ trả về file audio):**
```bash
POST http://localhost:8000/api/v1/tts/audio
Content-Type: application/json

{
  "text": "Hello, this is a test",
  "use_mistral": true,
  "optimize_pitch": true,
  "lang": "en"
}
```

**2. Endpoint Mistral chuyên dụng:**
```bash
POST http://localhost:8000/api/v1/tts/mistral
Content-Type: application/json

{
  "text": "Tell me about artificial intelligence",
  "model": "mistral-small-latest"
}
```

**3. Chat với Mistral:**
```bash
POST http://localhost:8000/api/v1/chat
Content-Type: application/json

{
  "message": "Hãy giới thiệu về bạn",
  "model": "mistral-small-latest"
}
```

**4. List Models:**
```bash
GET http://localhost:8000/api/v1/models
```

**5. List Languages:**
```bash
GET http://localhost:8000/api/v1/languages
```

**6. Lấy file audio đã tạo:**
```bash
GET http://localhost:8000/api/v1/audio/{filename}
```

## Tính năng Pitch Optimization

API sử dụng Mistral AI để phân tích text và tự động điều chỉnh cao độ (pitch) cho phù hợp:
- **Câu hỏi**: Pitch cao hơn một chút (1.05x)
- **Câu cảm thán**: Pitch cao hơn (1.1x)
- **Text dài**: Pitch thấp hơn một chút (0.95x)
- **Text bình thường**: Pitch chuẩn (1.0x)

Bạn có thể tắt tính năng này bằng cách set `optimize_pitch: false` hoặc chỉ định `pitch_factor` cụ thể.

## Ví dụ sử dụng với cURL

```bash
# Xử lý text và tạo audio với pitch optimization
curl -X POST "http://localhost:8000/api/v1/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test",
    "use_mistral": true,
    "return_audio": true,
    "optimize_pitch": true,
    "lang": "en"
  }'

# Tạo audio trực tiếp (download file)
curl -X POST "http://localhost:8000/api/v1/tts/audio" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test", "lang": "en"}' \
  --output output.mp3

# Chat
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Mistral AI"}'

# List models
curl http://localhost:8000/api/v1/models
```

## Ví dụ sử dụng với Python

```python
import requests

# Xử lý text với Mistral và tạo audio với pitch optimization
response = requests.post(
    "http://localhost:8000/api/v1/tts",
    json={
        "text": "Hello, this is a test",
        "use_mistral": True,
        "return_audio": True,
        "optimize_pitch": True,
        "lang": "en",
        "model": "mistral-small-latest"
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
        "optimize_pitch": True
    }
)
with open("ai_question.mp3", "wb") as f:
    f.write(response.content)
print("Audio saved to ai_question.mp3")

# Chat với Mistral
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "Tell me about Mistral AI"
    }
)
print(response.json())
```

## Các tham số API

### TTSRequest

- `text` (required): Text cần chuyển đổi
- `lang` (optional, default: "en"): Ngôn ngữ (en, vi, fr, de, v.v.)
- `use_mistral` (optional, default: true): Sử dụng Mistral để xử lý text trước khi TTS
- `return_audio` (optional, default: false): Trả về thông tin audio trong JSON response
- `optimize_pitch` (optional, default: true): Sử dụng Mistral để tối ưu hóa pitch
- `pitch_factor` (optional, default: None): Hệ số pitch cụ thể (0.7-1.3), nếu None sẽ dùng Mistral để tính
- `model` (optional, default: "mistral-small-latest"): Model Mistral để sử dụng
- `temperature` (optional, default: 0.7): Temperature cho Mistral
- `max_tokens` (optional, default: 1000): Max tokens cho Mistral

## Tài liệu tham khảo

- [Mistral AI Documentation](https://docs.mistral.ai/)
- [Mistral AI Python SDK](https://github.com/mistralai/mistral-sdk-python)
- [kokoro-tts GitHub](https://github.com/nazdridoy/kokoro-tts)
- [pydub Documentation](https://github.com/jiaaro/pydub)
