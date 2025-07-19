"""
FastAPI backend for VAD-enabled Speech-to-Speech system
"""

import os
from dotenv import load_dotenv
import asyncio
import json
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src_v1.backend import RealtimeOpenAIClient
from src_v1.audio import AudioRecorder
from src_v1.text_format import format_text

import threading
import time
from typing import cast

app = FastAPI(title="Speech-to-Speech AI Assistant")

# Allow CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web_vad/static"), name="static")

# Load config from env
load_dotenv()
AZURE_API_KEY = cast(str, os.getenv('AZURE_OPENAI_API_KEY'))
AZURE_API_VERSION = cast(str, os.getenv('AZURE_API_VERSION'))
AZURE_OPENAI_DEPLOYMENT = cast(str, os.getenv('AZURE_OPENAI_DEPLOYMENT'))

# Ensure required env vars are set
assert AZURE_API_KEY is not None, 'AZURE_OPENAI_API_KEY is not set'
assert AZURE_API_VERSION is not None, 'AZURE_API_VERSION is not set'
assert AZURE_OPENAI_DEPLOYMENT is not None, 'AZURE_OPENAI_DEPLOYMENT is not set'

# Global client for WebSocket sessions
clients = {}

class VADWebSocketManager:
    def __init__(self):
        self.active_connections = {}
        self.audio_recorders = {}
        self.loop = None
        self.accumulated_pcm_base64 = {}  # client_id -> str
    
    def set_loop(self, loop):
        """Set the event loop for async operations"""
        self.loop = loop
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Create RealtimeOpenAIClient for this session
        client = RealtimeOpenAIClient(
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION,
            deployment_name=AZURE_OPENAI_DEPLOYMENT,
            text_callback=lambda text: self._schedule_text_response(client_id, text),
            audio_callback=lambda audio: self._schedule_audio_response(client_id, audio),
            audio_done_callback=lambda: self._schedule_audio_done(client_id)
        )
        
        try:
            client.connect()
            clients[client_id] = client
            await websocket.send_json({
                "type": "connection_status",
                "status": "connected",
                "message": "Connected to Azure OpenAI"
            })
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Connection failed: {str(e)}"
            })
    
    def _schedule_text_response(self, client_id: str, text: str):
        """Schedule text response to be sent in the main event loop"""
        if self.loop:
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.handle_text_response(client_id, text))
            )
    
    def _schedule_audio_response(self, client_id: str, audio_chunk: str):
        """Schedule audio response to be sent in the main event loop"""
        if self.loop:
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.handle_audio_response(client_id, audio_chunk))
            )
        # Accumulate PCM base64 for this client
        if client_id not in self.accumulated_pcm_base64:
            self.accumulated_pcm_base64[client_id] = ''
        self.accumulated_pcm_base64[client_id] += audio_chunk
    
    def _schedule_audio_done(self, client_id: str):
        if self.loop:
            self.loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.handle_audio_done(client_id))
            )

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in clients:
            clients[client_id].close()
            del clients[client_id]
        if client_id in self.audio_recorders:
            del self.audio_recorders[client_id]
    
    async def handle_text_response(self, client_id: str, text: str):
        if client_id in self.active_connections:
            formatted = format_text(text)
            await self.active_connections[client_id].send_json({
                "type": "text_response",
                "text": formatted
            })
    
    async def handle_audio_response(self, client_id: str, audio_chunk: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "type": "audio_chunk",
                "audio": audio_chunk
            })
    
    async def handle_audio_done(self, client_id: str):
        if client_id in self.active_connections:
            # เมื่อจบ audio ให้แปลง PCM base64 ที่สะสมเป็น WAV base64 แล้วส่งกลับ client
            pcm_base64 = self.accumulated_pcm_base64.get(client_id, '')
            if pcm_base64:
                wav_base64 = AudioRecorder.pcm_base64_to_wav_base64(pcm_base64, sample_rate=24000)
                await self.active_connections[client_id].send_json({
                    "type": "audio_chunk",
                    "audio": wav_base64
                })
            # reset buffer
            self.accumulated_pcm_base64[client_id] = ''
            await self.active_connections[client_id].send_json({
                "type": "audio_response_done"
            })
    
    async def send_message(self, client_id: str, message_type: str, data: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "type": message_type,
                **data
            })

manager = VADWebSocketManager()

@app.on_event("startup")
async def startup_event():
    """Set the event loop for the manager"""
    manager.set_loop(asyncio.get_running_loop())

@app.get("/")
async def get_index():
    """Serve the main HTML page"""
    with open("web_vad/static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(client_id, data)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)

async def handle_websocket_message(client_id: str, data: dict):
    """Handle incoming WebSocket messages"""
    message_type = data.get("type")
    
    if message_type == "start_recording":
        # Start VAD recording
        await start_vad_recording(client_id)
    
    elif message_type == "stop_recording":
        # Stop VAD recording
        await stop_vad_recording(client_id)

async def start_vad_recording(client_id: str):
    """Start VAD recording for a client"""
    if client_id not in clients:
        await manager.send_message(client_id, "error", {"message": "Client not connected"})
        return
    
    try:
        # Create audio recorder for this client
        recorder = AudioRecorder(fs=24000)
        manager.audio_recorders[client_id] = recorder
        
        # Start recording in a separate thread
        def record_audio():
            try:
                recorder.record_with_vad_auto_send(
                    client=clients[client_id],
                    prompt="",
                    max_duration=30,
                    silence_threshold=1.0
                )
            except Exception as e:
                print(f"Recording error: {e}")
        
        recording_thread = threading.Thread(target=record_audio, daemon=True)
        recording_thread.start()
        
        await manager.send_message(client_id, "recording_status", {
            "status": "started",
            "message": "Recording started with VAD"
        })
        
    except Exception as e:
        await manager.send_message(client_id, "error", {"message": f"Failed to start recording: {str(e)}"})

async def stop_vad_recording(client_id: str):
    """Stop VAD recording for a client"""
    if client_id in manager.audio_recorders:
        recorder = manager.audio_recorders[client_id]
        recorder.is_recording = False
        del manager.audio_recorders[client_id]
        
        await manager.send_message(client_id, "recording_status", {
            "status": "stopped",
            "message": "Recording stopped"
        })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "active_connections": len(manager.active_connections)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
