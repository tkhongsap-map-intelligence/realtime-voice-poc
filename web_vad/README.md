# VAD Speech-to-Speech Web System

ระบบ Speech-to-Speech ที่ใช้ Voice Activity Detection (VAD) บนเว็บ

## คุณสมบัติ

- 🎤 **VAD Recording**: บันทึกเสียงอัตโนมัติเมื่อพูด หยุดเมื่อเงียบ
- 🌐 **Web Interface**: ใช้งานผ่านเว็บเบราว์เซอร์
- 💬 **Real-time Chat**: สนทนากับ AI แบบ real-time
- 🔊 **Audio Playback**: เล่นเสียงตอบกลับจาก AI
- 📝 **Text Input**: ส่งข้อความแบบพิมพ์
- 🔄 **Auto-send**: ส่งเสียงอัตโนมัติเมื่อหยุดพูด

## การติดตั้ง

### 1. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` ในโฟลเดอร์หลัก:

```env
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

### 3. รัน Server

```bash
cd web_vad
python main.py
```

หรือใช้ uvicorn:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. เปิดเว็บเบราว์เซอร์

ไปที่: `http://localhost:8000`

## การใช้งาน

### Voice Mode (VAD)
1. กดปุ่ม "เริ่มพูด"
2. พูดได้เลย - ระบบจะฟังเสียงอัตโนมัติ
3. หยุดพูด 1 วินาที - ระบบจะส่งเสียงไปยัง AI
4. ฟังการตอบกลับจาก AI

### Text Mode
1. พิมพ์ข้อความในช่อง text
2. กดปุ่ม "ส่งข้อความ" หรือ Enter
3. รับการตอบกลับจาก AI

## โครงสร้างไฟล์

```
web_vad/
├── main.py              # FastAPI backend
├── static/
│   └── index.html       # Frontend UI
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## API Endpoints

- `GET /` - Main HTML page
- `GET /health` - Health check
- `WebSocket /ws/{client_id}` - Real-time communication

## WebSocket Messages

### Client to Server
```json
{
  "type": "start_recording"
}
```

```json
{
  "type": "stop_recording"
}
```

```json
{
  "type": "send_text",
  "text": "Hello AI"
}
```

### Server to Client
```json
{
  "type": "connection_status",
  "status": "connected",
  "message": "Connected to Azure OpenAI"
}
```

```json
{
  "type": "text_response",
  "text": "Hello! How can I help you?"
}
```

```json
{
  "type": "audio_chunk",
  "audio": "base64_audio_data"
}
```

## การแก้ไขปัญหา

### ปัญหาที่พบบ่อย

1. **VAD ไม่ทำงาน**
   - ตรวจสอบว่า `webrtcvad-wheels` ติดตั้งแล้ว
   - ตรวจสอบ microphone permissions

2. **เสียงไม่ชัด**
   - ตรวจสอบ sample rate (24kHz)
   - ตรวจสอบ audio format (PCM 16-bit)

3. **WebSocket connection failed**
   - ตรวจสอบ Azure OpenAI credentials
   - ตรวจสอบ network connection

### Debug Mode

เพิ่ม logging ใน `main.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## การพัฒนาเพิ่มเติม

### เพิ่ม Features
- Multiple voice options
- Conversation history
- File upload support
- Custom VAD settings

### Performance Optimization
- Audio compression
- Connection pooling
- Caching responses

## License

MIT License 