# Mistral AI API

Dự án này cung cấp REST API để sử dụng Mistral AI để xử lý text.

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

3. **Cấu hình API Key:**
API key đã được cấu hình sẵn trong code. Nếu muốn sử dụng biến môi trường, tạo file `.env`:
```
MISTRAL_API_KEY=O3EI2wp2X2MekBLookmnOanLA9UohV9Z
```

Hoặc export biến môi trường:
```bash
export MISTRAL_API_KEY=O3EI2wp2X2MekBLookmnOanLA9UohV9Z
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

**1. Xử lý text với Mistral:**
```bash
POST http://localhost:8000/api/v1/tts
Content-Type: application/json

{
  "text": "Hello, this is a test",
  "use_mistral": true,
  "model": "mistral-small-latest",
  "temperature": 0.7,
  "max_tokens": 1000
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

## Ví dụ sử dụng với cURL

```bash
# Xử lý text
curl -X POST "http://localhost:8000/api/v1/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test", "use_mistral": true}'

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

# Xử lý text với Mistral
response = requests.post(
    "http://localhost:8000/api/v1/tts",
    json={
        "text": "Hello, this is a test",
        "use_mistral": True,
        "model": "mistral-small-latest"
    }
)
print(response.json())

# Chat với Mistral
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "message": "Tell me about Mistral AI"
    }
)
print(response.json())
```

## Tài liệu tham khảo

- [Mistral AI Documentation](https://docs.mistral.ai/)
- [Mistral AI Python SDK](https://github.com/mistralai/mistral-sdk-python)
