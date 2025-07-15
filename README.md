# Realtime Voice Proof of Concept

This project showcases a small speech‑to‑speech assistant using the Azure OpenAI Realtime API. It records audio with Voice Activity Detection (VAD), sends it to the model and returns both text and audio responses. The repository includes a FastAPI backend and a web frontend.

## Features

- **Voice Activity Detection** – Recording automatically starts and stops based on speech.
- **Real‑time WebSocket communication** – Streams audio and text responses while recording.
- **Web interface** – Simple HTML/JavaScript frontend located under `web_vad/static`.
- **Text formatting** – Helper utilities for formatting AI responses into HTML.

## Directory structure

```
.
├── main.py              # FastAPI application entry point
├── src_v1/              # Core recording and API logic
│   ├── audio.py         # Audio recorder with VAD support
│   ├── backend.py       # Client for Azure OpenAI realtime WebSocket
│   ├── text_format.py   # Utility to format text responses
│   └── vad_client.py    # Example VAD client usage
└── web_vad/
    ├── README.md        # Web UI documentation (Thai)
    ├── requirements.txt # Python dependencies
    └── static/
        └── index.html   # Browser interface
```

## Installation

1. Create a virtual environment and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r web_vad/requirements.txt
```

2. Configure environment variables by creating a `.env` file in the project root:

```ini
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

These values must correspond to your Azure OpenAI deployment.

## Running the application

From the repository root, run the FastAPI server:

```bash
python main.py
```

Alternatively use Uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open a browser and navigate to `http://localhost:8000` to interact with the demo interface.

### API endpoints

- `GET /` – Returns the HTML interface.
- `GET /health` – Basic health check.
- `WebSocket /ws/{client_id}` – Streaming audio/text chat.

WebSocket messages support commands such as `start_recording`, `stop_recording` and `send_text`. See `web_vad/README.md` for a detailed message format reference.

## License

This proof‑of‑concept is provided under the MIT License.
