#!/usr/bin/env python3
"""
Script test API với kokoro-tts
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Test Health Check")
    print("=" * 60)
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False

def test_tts_basic():
    """Test TTS cơ bản"""
    print("=" * 60)
    print("Test TTS Cơ Bản (kokoro-tts)")
    print("=" * 60)
    
    data = {
        "text": "Hello, this is a test with kokoro-tts",
        "return_audio": True,
        "optimize_pitch": False,
        "use_mistral": False,
        "lang": "en"
    }
    
    print(f"\nRequest: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print("\nĐang gửi request (kokoro-tts có thể mất 10-30 giây)...")
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/api/v1/tts", json=data, timeout=120)
        elapsed = time.time() - start_time
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Thời gian xử lý: {elapsed:.2f} giây")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("audio_file"):
                print(f"\n✓ Audio file: {result['audio_file']}")
                print(f"✓ Audio URL: {result['audio_url']}")
                print(f"✓ Pitch factor: {result.get('pitch_factor', 'N/A')}")
                return True
            else:
                print("\n✗ Không có audio file trong response")
                return False
        else:
            print(f"\n✗ Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n✗ Timeout: kokoro-tts mất quá nhiều thời gian")
        return False
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        return False

def test_tts_with_pitch():
    """Test TTS với pitch optimization"""
    print("\n" + "=" * 60)
    print("Test TTS với Pitch Optimization (Mistral phân tích pitch)")
    print("=" * 60)
    
    data = {
        "text": "What is your name?",
        "return_audio": True,
        "optimize_pitch": True,
        "use_mistral": False,
        "lang": "en"
    }
    
    print(f"\nRequest: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print("\nĐang gửi request...")
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/api/v1/tts", json=data, timeout=120)
        elapsed = time.time() - start_time
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Thời gian xử lý: {elapsed:.2f} giây")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("audio_file"):
                print(f"\n✓ Audio file: {result['audio_file']}")
                print(f"✓ Pitch factor: {result.get('pitch_factor', 'N/A')}")
                return True
        else:
            print(f"\n✗ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        return False

def test_tts_audio_endpoint():
    """Test endpoint trả về file audio trực tiếp"""
    print("\n" + "=" * 60)
    print("Test TTS Audio Endpoint (trả về file trực tiếp)")
    print("=" * 60)
    
    data = {
        "text": "This is amazing!",
        "optimize_pitch": True,
        "use_mistral": False,
        "lang": "en"
    }
    
    print(f"\nRequest: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print("\nĐang gửi request...")
    
    try:
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/api/v1/tts/audio", json=data, timeout=120)
        elapsed = time.time() - start_time
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Thời gian xử lý: {elapsed:.2f} giây")
        
        if response.status_code == 200:
            # Lấy thông tin từ headers
            print(f"\nHeaders:")
            for key, value in response.headers.items():
                if key.startswith("X-"):
                    print(f"  {key}: {value}")
            
            # Lưu file audio
            with open("test_kokoro_audio.mp3", "wb") as f:
                f.write(response.content)
            print(f"\n✓ Audio đã được lưu vào test_kokoro_audio.mp3")
            print(f"✓ File size: {len(response.content)} bytes")
            return True
        else:
            print(f"\n✗ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TEST API VỚI KOKORO-TTS")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test health
    results.append(("Health Check", test_health()))
    
    # Test TTS basic
    results.append(("TTS Cơ Bản", test_tts_basic()))
    
    # Test TTS with pitch
    results.append(("TTS với Pitch Optimization", test_tts_with_pitch()))
    
    # Test audio endpoint
    results.append(("TTS Audio Endpoint", test_tts_audio_endpoint()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TỔNG KẾT")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    print(f"\nTổng: {passed}/{total} tests passed")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest bị hủy bởi người dùng")
    except requests.exceptions.ConnectionError:
        print("\n✗ Lỗi: Không thể kết nối đến API server.")
        print("  Vui lòng đảm bảo server đang chạy trên http://localhost:8000")
        print("  Chạy: python api.py hoặc uvicorn api:app --reload")
