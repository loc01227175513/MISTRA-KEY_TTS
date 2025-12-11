#!/usr/bin/env python3
"""
Script test gTTS với pitch optimization
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_tts_with_audio():
    """Test TTS endpoint với audio"""
    print("=" * 60)
    print("Test TTS với Audio và Pitch Optimization")
    print("=" * 60)
    
    data = {
        "text": "Hello, how are you today?",
        "return_audio": True,
        "optimize_pitch": True,
        "lang": "en",
        "use_mistral": False  # Tắt Mistral text processing để test nhanh hơn
    }
    
    print(f"\nRequest: {json.dumps(data, indent=2)}")
    print("\nĐang gửi request...")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/tts", json=data, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result.get("audio_file"):
                print(f"\n✓ Audio file: {result['audio_file']}")
                print(f"✓ Audio URL: {result['audio_url']}")
                print(f"✓ Pitch factor: {result.get('pitch_factor', 'N/A')}")
                
                # Tải file audio
                if result.get("audio_url"):
                    audio_response = requests.get(f"{API_BASE_URL}{result['audio_url']}")
                    if audio_response.status_code == 200:
                        with open("test_output.mp3", "wb") as f:
                            f.write(audio_response.content)
                        print(f"\n✓ Audio đã được lưu vào test_output.mp3")
            else:
                print("\n✗ Không có audio file trong response")
        else:
            print(f"\n✗ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Lỗi: Không thể kết nối đến API server.")
        print("  Vui lòng đảm bảo server đang chạy trên http://localhost:8000")
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")


def test_tts_audio_endpoint():
    """Test endpoint /api/v1/tts/audio"""
    print("\n" + "=" * 60)
    print("Test TTS Audio Endpoint (trả về file trực tiếp)")
    print("=" * 60)
    
    data = {
        "text": "This is a test with exclamation!",
        "lang": "en",
        "optimize_pitch": True,
        "use_mistral": False
    }
    
    print(f"\nRequest: {json.dumps(data, indent=2)}")
    print("\nĐang gửi request...")
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/tts/audio", json=data, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            # Lấy thông tin từ headers
            print(f"\nHeaders:")
            for key, value in response.headers.items():
                if key.startswith("X-"):
                    print(f"  {key}: {value}")
            
            # Lưu file audio
            with open("test_audio_direct.mp3", "wb") as f:
                f.write(response.content)
            print(f"\n✓ Audio đã được lưu vào test_audio_direct.mp3")
            print(f"✓ File size: {len(response.content)} bytes")
        else:
            print(f"\n✗ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Lỗi: Không thể kết nối đến API server.")
    except Exception as e:
        print(f"\n✗ Lỗi: {e}")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TEST GTTS VỚI PITCH OPTIMIZATION")
    print("=" * 60 + "\n")
    
    # Đợi server sẵn sàng
    print("Đang kiểm tra server...")
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print("✓ Server đang chạy\n")
        else:
            print("✗ Server không phản hồi đúng\n")
            return
    except:
        print("✗ Không thể kết nối đến server\n")
        return
    
    # Chạy tests
    test_tts_with_audio()
    time.sleep(2)
    test_tts_audio_endpoint()
    
    print("\n" + "=" * 60)
    print("Tất cả tests đã hoàn thành!")
    print("=" * 60)


if __name__ == "__main__":
    main()
