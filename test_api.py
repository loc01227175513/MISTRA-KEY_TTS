#!/usr/bin/env python3
"""
Script để test Mistral TTS API
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("=" * 50)
    print("Test Health Check")
    print("=" * 50)
    response = requests.get(f"{API_BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_tts():
    """Test TTS endpoint"""
    print("=" * 50)
    print("Test TTS Endpoint")
    print("=" * 50)
    
    data = {
        "text": "Xin chào, đây là test Mistral TTS API. Tôi đang kiểm tra chức năng text to speech.",
        "model": "mistral-small-latest",
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    response = requests.post(f"{API_BASE_URL}/api/v1/tts", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_chat():
    """Test Chat endpoint"""
    print("=" * 50)
    print("Test Chat Endpoint")
    print("=" * 50)
    
    data = {
        "message": "Hãy giới thiệu về Mistral AI",
        "model": "mistral-small-latest"
    }
    
    response = requests.post(f"{API_BASE_URL}/api/v1/chat", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_models():
    """Test Models endpoint"""
    print("=" * 50)
    print("Test Models Endpoint")
    print("=" * 50)
    response = requests.get(f"{API_BASE_URL}/api/v1/models")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Total models: {result.get('count', 0)}")
    print(f"First 5 models:")
    for model in result.get('models', [])[:5]:
        print(f"  - {model['id']}")
    print()

def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("MISTRAL TTS API TEST SUITE")
    print("=" * 50 + "\n")
    
    try:
        test_health()
        test_tts()
        test_chat()
        test_models()
        
        print("=" * 50)
        print("Tất cả tests đã hoàn thành!")
        print("=" * 50)
    except requests.exceptions.ConnectionError:
        print("✗ Lỗi: Không thể kết nối đến API server.")
        print("  Vui lòng đảm bảo server đang chạy trên http://localhost:8000")
        print("  Chạy: python api.py hoặc uvicorn api:app --reload")
    except Exception as e:
        print(f"✗ Lỗi: {e}")

if __name__ == "__main__":
    main()

