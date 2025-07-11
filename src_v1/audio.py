
import sounddevice as sd
import base64
import struct
import numpy as np
import webrtcvad
import time
import threading
from scipy import signal
import io, wave

class AudioRecorder:
    def __init__(self, fs=24000, channels=1):  # กลับไปใช้ 24kHz
        self.fs = fs
        self.channels = channels
        self.audio_data = None
        self.vad = webrtcvad.Vad(2)
        self.frame_duration_ms = 30
        self.frame_size = int(fs * self.frame_duration_ms / 1000)
        self.is_recording = False

    def resample_audio(self, audio_data, original_fs, target_fs):
        """
        Resample audio จาก original_fs เป็น target_fs
        """
        if original_fs == target_fs:
            return audio_data
            
        # Calculate resampling ratio
        ratio = target_fs / original_fs
        new_length = int(len(audio_data) * ratio)
        
        # Resample using scipy
        resampled = signal.resample(audio_data, new_length)
        return resampled

    def record_with_vad_auto_send(self, client, prompt="", max_duration=30, silence_threshold=1.0):
        """
        อัดเสียงด้วย VAD และส่งไปยัง server อัตโนมัติเมื่อหยุดพูด
        """
        print(f"🎤 เริ่มฟังเสียง (พูดได้เลย - จะส่งอัตโนมัติเมื่อหยุดพูด {silence_threshold}s)...")
        
        audio_buffer = b''
        last_speech_time = time.time()
        self.is_recording = True
        
        def audio_callback(indata, frames, time_info, status):
            nonlocal audio_buffer, last_speech_time
            
            if not self.is_recording:
                return False
                
            if status:
                print(f"Audio status: {status}")
            
            # Convert to 16-bit PCM bytes
            audio_bytes = (indata * 32767).astype(np.int16).tobytes()
            
            # Process each frame
            for i in range(0, len(audio_bytes), self.frame_size * 2):
                frame = audio_bytes[i:i + self.frame_size * 2]
                if len(frame) == self.frame_size * 2:
                    try:
                        # Resample frame to 16kHz for VAD
                        frame_np = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32767.0
                        frame_16k = self.resample_audio(frame_np, self.fs, 16000)
                        frame_16k_bytes = (frame_16k * 32767).astype(np.int16).tobytes()
                        
                        # Use 16kHz for VAD detection
                        is_speech = self.vad.is_speech(frame_16k_bytes, 16000)
                        
                        if is_speech:
                            audio_buffer += frame  # Store original 24kHz audio
                            last_speech_time = time.time()
                            print("🔊 กำลังฟัง...", end="\r")
                        elif time.time() - last_speech_time > silence_threshold and len(audio_buffer) > 0:
                            print(f"\n🔇 หยุดฟัง - ส่งเสียงไปยัง AI...")
                            self.is_recording = False
                            
                            # Send audio to server in a separate thread
                            def send_audio():
                                try:
                                    # Convert audio buffer to base64 (24kHz)
                                    audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32767.0
                                    audio_content = self.base64_encode_audio(audio_np)
                                    
                                    # Send to server
                                    client.response_done_event.clear()
                                    client.send_prompt_with_voice(
                                        base64_string=audio_content,
                                        prompt=prompt,
                                    )
                                    
                                    # Wait for response
                                    while not client.response_done_event.is_set():
                                        time.sleep(0.05)
                                        
                                    print("✅ ได้รับการตอบกลับแล้ว")
                                    
                                except Exception as e:
                                    print(f"❌ เกิดข้อผิดพลาด: {e}")
                            
                            # Run in separate thread to avoid blocking
                            threading.Thread(target=send_audio, daemon=True).start()
                            return False
                            
                    except Exception as e:
                        continue
        
        try:
            with sd.InputStream(
                callback=audio_callback,
                channels=self.channels,
                samplerate=self.fs,  # ใช้ 24kHz
                dtype=np.float32,
                blocksize=self.frame_size
            ):
                start_time = time.time()
                while self.is_recording and (time.time() - start_time) < max_duration:
                    time.sleep(0.1)
                    
                if self.is_recording:
                    print(f"\n⏰ หมดเวลา ({max_duration}s)")
                    
        except Exception as e:
            print(f"Error during recording: {e}")
            
        self.is_recording = False

    def record_with_vad(self, max_duration=30, silence_threshold=1.0):
        """
        อัดเสียงด้วย VAD - หยุดอัตโนมัติเมื่อไม่มีการพูด
        """
        print(f"🎤 เริ่มฟังเสียง (หยุดอัตโนมัติเมื่อเงียบ {silence_threshold}s)...")
        
        audio_buffer = b''
        last_speech_time = time.time()
        
        def audio_callback(indata, frames, time_info, status):
            nonlocal audio_buffer, last_speech_time
            
            if status:
                print(f"Audio status: {status}")
            
            # Convert to 16-bit PCM bytes
            audio_bytes = (indata * 32767).astype(np.int16).tobytes()
            
            # Process each frame
            for i in range(0, len(audio_bytes), self.frame_size * 2):
                frame = audio_bytes[i:i + self.frame_size * 2]
                if len(frame) == self.frame_size * 2:
                    try:
                        # Resample frame to 16kHz for VAD
                        frame_np = np.frombuffer(frame, dtype=np.int16).astype(np.float32) / 32767.0
                        frame_16k = self.resample_audio(frame_np, self.fs, 16000)
                        frame_16k_bytes = (frame_16k * 32767).astype(np.int16).tobytes()
                        
                        # Use 16kHz for VAD detection
                        is_speech = self.vad.is_speech(frame_16k_bytes, 16000)
                        
                        if is_speech:
                            audio_buffer += frame  # Store original 24kHz audio
                            last_speech_time = time.time()
                            print("🔊 กำลังฟัง...", end="\r")
                        elif time.time() - last_speech_time > silence_threshold:
                            print(f"\n🔇 หยุดฟัง (เงียบ {silence_threshold}s)")
                            return False
                    except Exception as e:
                        continue
        
        try:
            with sd.InputStream(
                callback=audio_callback,
                channels=self.channels,
                samplerate=self.fs,  # ใช้ 24kHz
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
            # Convert back to numpy array
            audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32767.0
            self.audio_data = audio_np
            print(f"✅ อัดเสียงเสร็จแล้ว (ความยาว: {len(audio_np)/self.fs:.1f} วินาที)")
        else:
            print("❌ ไม่พบเสียงพูด")
            self.audio_data = None
            
        return self.audio_data

    def record(self, duration=5):
        """
        อัดเสียงสดและเก็บใน self.audio_data (numpy array float32)
        """
        print(f"เริ่มอัดเสียง {duration} วินาที...")
        audio = sd.rec(int(duration * self.fs), samplerate=self.fs, channels=self.channels, dtype='float32')
        sd.wait()
        print("อัดเสียงเสร็จแล้ว")
        self.audio_data = audio.flatten()
        return self.audio_data

    @staticmethod
    def float_to_16bit_pcm(float32_array):
        clipped = [max(-1.0, min(1.0, x)) for x in float32_array]
        pcm16 = b''.join(struct.pack('<h', int(x * 32767)) for x in clipped)
        return pcm16

    @staticmethod
    def base64_encode_audio(float32_array):
        pcm_bytes = AudioRecorder.float_to_16bit_pcm(float32_array)
        encoded = base64.b64encode(pcm_bytes).decode('ascii')
        return encoded

    @staticmethod
    def pcm_base64_to_wav_base64(pcm_base64, sample_rate=24000):
        pcm_bytes = base64.b64decode(pcm_base64)
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit PCM
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_bytes)
            wav_bytes = wav_io.getvalue()
        return base64.b64encode(wav_bytes).decode('ascii')

    def get_base64_audio(self):
        if self.audio_data is None:
            raise ValueError("ยังไม่มีข้อมูลเสียง กรุณาอัดเสียงก่อน")
        return self.base64_encode_audio(self.audio_data)
