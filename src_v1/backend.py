
import os
import json
import time
import asyncio
import websocket
import threading
from typing import Optional

class RealtimeOpenAIClient:
    """
    Client for Azure OpenAI Realtime API (text/audio chat).
    Handles WebSocket connection, sending prompts, and receiving responses.
    """
    def __init__(self, api_key: str, api_version: str, deployment_name: str, text_callback=None, audio_callback=None, audio_done_callback=None):
        # --- API and connection config ---
        self.api_key = api_key
        self.api_version = api_version
        self.deployment_name = deployment_name
        self.uri = (
            f'wss://pegasus-001-resource.cognitiveservices.azure.com/openai/realtime?'
            f'api-version={self.api_version}&deployment={self.deployment_name}&api-key={self.api_key}'
        )
        self.headers = [
            f"Authorization: Bearer {self.api_key}",
            "OpenAI-Beta: realtime=v1"
        ]

        # --- Internal state ---
        self._ws = None
        self._thread = None
        self._is_connected = False
        self._total_audio_data = ''  # Accumulates base64 audio deltas

        # --- Callbacks for external handling of responses ---
        self.text_callback = text_callback
        self.audio_callback = audio_callback
        self.response_done_event = asyncio.Event()
        self.audio_done_callback = audio_done_callback

    def _on_open(self, ws):
        """WebSocket open event handler."""
        print("Connected to server.")
        self._is_connected = True

    def _on_message(self, ws, message):
        """WebSocket message event handler. Handles all server events."""
        server_event = json.loads(message)
        try:
            event_type = server_event.get('type')

            if event_type == 'response.audio_transcript.done':
                # --- Text response received ---
                text = server_event.get('transcript')
                print(f'\nAnswer(Text): {text}')
                if self.text_callback:
                    self.text_callback(text)

            elif event_type == 'response.audio.delta':
                # --- Audio chunk received ---
                delta_audio = server_event.get('delta')
                if delta_audio:
                    self._total_audio_data += delta_audio
                    if self.audio_callback:
                        self.audio_callback(delta_audio)

            elif event_type == 'response.audio.done':
                # --- Audio response finished ---
                print('Audio response completed')
                if self.audio_done_callback:
                    self.audio_done_callback()
                # แสดงความยาวของ audio data ที่สะสมไว้
                self.print_audio_data_length()
                # set response_done_event ที่นี่!
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(self.response_done_event.set)
                except RuntimeError:
                    self.response_done_event.set()

        except Exception as e:
            print(f'Error processing WebSocket message: {e}')

    def _on_error(self, ws, error):
        """WebSocket error event handler."""
        print(f'WebSocket error: {error}')
        self._is_connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket close event handler."""
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
        self._is_connected = False

    def connect(self, timeout: int = 5):
        """
        Establish WebSocket connection to Azure OpenAI Realtime API.
        Raises ConnectionError if connection fails.
        """
        if self._ws:
            print("WebSocket already initialized. Closing existing connection.")
            self.close()

        self._ws = websocket.WebSocketApp(
            self.uri,
            header=self.headers,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        self._thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._thread.start()

        start_time = time.time()
        # Wait for connection to be established
        while not self._is_connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if not self._is_connected:
            print("Failed to connect to WebSocket server within the timeout.")
            raise ConnectionError("WebSocket connection failed.")
        print("WebSocket connection established.")

    def send_prompt_with_voice(self, prompt: str, base64_string: str, modalities: Optional[list] = None):
        """
        Send a prompt with both text and audio (base64) to the model.
        """
        if not self._is_connected or self._ws is None:
            print("Not connected to WebSocket. Please call connect() first.")
            return
        if modalities is None:
            modalities = ['text', 'audio']
        self._total_audio_data = ''  # Reset audio buffer
        # Build and send message event
        event_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_audio", "audio": base64_string}
                ]
            }
        }
        self._ws.send(json.dumps(event_message))

        # Request response with specified modalities
        event_response = {
            "type": "response.create",
            "response": {
                "modalities": modalities,
                # "max_output_tokens": 'inf'
                         }
        }
        self._ws.send(json.dumps(event_response))
        print("Prompt sent. Waiting for response...")

    def send_prompt_only_text(self, prompt: str, modalities: Optional[list] = None):
        """
        Send a text-only prompt to the model.
        """
        if not self._is_connected or self._ws is None:
            print("Not connected to WebSocket. Please call connect() first.")
            return
        if modalities is None:
            modalities = ['text', 'audio']
        self._total_audio_data = ''  # Reset audio buffer
        # Build and send message event
        event_message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt}
                ]
            }
        }
        self._ws.send(json.dumps(event_message))

        # Request response with specified modalities
        event_response = {
            "type": "response.create",
            "response": {"modalities": modalities}
        }
        self._ws.send(json.dumps(event_response))
        print("Prompt sent. Waiting for response...")

    def close(self):
        """
        Close the WebSocket connection.
        """
        if self._ws:
            self._ws.close()
            self._ws = None
            self._is_connected = False
            print("WebSocket connection closed by client.")

    def get_accumulated_audio(self) -> str:
        """
        Get all accumulated audio data (base64) from the last response.
        """
        return self._total_audio_data

    def print_audio_data_length(self):
        """
        แสดงความยาวของ base64 audio data ที่สะสมไว้
        """
        print(f"[DEBUG] total_audio_data length: {len(self._total_audio_data)} characters")
        # print(f"example: {self._total_audio_data}")