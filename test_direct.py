#!/usr/bin/env python3
"""Test trực tiếp hàm tạo audio"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from api import create_audio_with_optimized_pitch

async def test():
    print("Testing create_audio_with_optimized_pitch...")
    print("Test 1: Without Mistral, pitch_factor=1.0")
    try:
        filename, pitch = await create_audio_with_optimized_pitch(
            text="Hello, this is a test!",
            lang="en",
            use_mistral=False,
            pitch_factor=1.0
        )
        print(f"✓ Success! File: {filename}, Pitch: {pitch}")
        print(f"  File exists: {os.path.exists(os.path.join('audio_files', filename))}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest 2: With Mistral pitch optimization")
    try:
        filename, pitch = await create_audio_with_optimized_pitch(
            text="Hello, how are you?",
            lang="en",
            use_mistral=True,
            pitch_factor=None
        )
        print(f"✓ Success! File: {filename}, Pitch: {pitch}")
        print(f"  File exists: {os.path.exists(os.path.join('audio_files', filename))}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
