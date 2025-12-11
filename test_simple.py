#!/usr/bin/env python3
"""Test đơn giản gTTS"""

from gtts import gTTS
import tempfile
import os

print("Testing gTTS...")
try:
    tts = gTTS(text="Hello test", lang="en", slow=False)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()
    print(f"Saving to {temp_file.name}...")
    tts.save(temp_file.name)
    print(f"✓ Success! File size: {os.path.getsize(temp_file.name)} bytes")
    os.unlink(temp_file.name)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
