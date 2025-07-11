import asyncio
import webrtcvad
import sounddevice as sd
import numpy as np
import base64
import time
from src_v1.backend import RealtimeOpenAIClient

class VADRealtimeClient(RealtimeOpenAIClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vad = webrtcvad.Vad(2)  # Medium aggressiveness
        self.fs = 24000
        self.frame_duration_ms = 30
        self.frame_size = int(self.fs * self.frame_duration_ms / 1000)
        self.is_listening = False
        
    def record_with_vad(self, max_duration=30):
        """
        Record audio with VAD - stops automatically when no speech detected
        """
        print("�� เริ่มฟังเสียง (พูดได้เลย)...")
        
        audio_buffer = b''
        last_speech_time = time.time()
        
        def audio_callback(indata, frames, time_info, status):
            nonlocal audio_buffer, last_speech_time
            
            if status:
                print(f"Audio status: {status}")
            
            # Convert to bytes for VAD
            audio_bytes = (indata * 32767).astype(np.int16).tobytes()
            
            # Process each frame
            for i in range(0, len(audio_bytes), self.frame_size * 2):
                frame = audio_bytes[i:i + self.frame_size * 2]
                if len(frame) == self.frame_size * 2:
                    is_speech = self.vad.is_speech(frame, self.fs)
                    
                    if is_speech:
                        audio_buffer += frame
                        last_speech_time = time.time()
                        print("🔊 กำลังฟัง...", end="\r")
                    elif time.time() - last_speech_time > 1.0:  # 1 second silence
                        print("\n🔇 หยุดฟัง (ไม่พบเสียงพูด)")
                        return False  # Stop recording
        
        try:
            with sd.InputStream(
                callback=audio_callback,
                channels=1,
                samplerate=self.fs,
                dtype=np.float32,
                blocksize=self.frame_size
            ):
                start_time = time.time()
                while (time.time() - start_time) < max_duration:
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"Error during recording: {e}")
            return None
            
        if audio_buffer:
            print(f"✅ อัดเสียงเสร็จแล้ว ({len(audio_buffer)/self.fs/2:.1f}s)")
            return audio_buffer
        else:
            print("❌ ไม่พบเสียงพูด")
            return None
    
    def send_voice_with_vad(self, prompt=""):
        """
        Send voice input with VAD detection
        """
        audio_data = self.record_with_vad()
        
        if audio_data:
            # Convert to base64
            base64_audio = base64.b64encode(audio_data).decode('utf-8')
            
            # Send to AI
            self.response_done_event.clear()
            self.send_prompt(
                prompt=prompt,
                audio_base64=base64_audio
            )
            
            # Wait for response
            while not self.response_done_event.is_set():
                time.sleep(0.05)
                
            return True
        return False
