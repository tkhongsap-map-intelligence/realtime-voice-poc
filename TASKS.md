# Improvement Tasks for Realtime Voice POC

This document lists potential enhancements for the repository based on a quick code review.

## Documentation
- **Add root README** summarizing project usage and link to the web_vad README. Currently only `web_vad/README.md` exists.
- Provide an example `.env` file documenting required environment variables.

## Configuration
- **Make the WebSocket URI configurable**. In `src_v1/backend.py` lines 16-23 the Azure service URI is hardcoded which couples the code to a specific deployment.

## Backend Features
- Handle "send_text" messages in `main.py` for text-only chat, as mentioned in the README but not implemented.
- Replace threading in `record_with_vad_auto_send` with async tasks for better integration with FastAPI's event loop.
- Use structured logging instead of `print` statements throughout the backend.

## Frontend Improvements
- Split the large inline JavaScript from `web_vad/static/index.html` into separate JS files for readability.

## Quality and Testing
- Add unit tests (e.g., using `pytest`) for audio processing utilities and WebSocket logic.
- Introduce formatting and linting tools (like `black` and `ruff`).

## Packaging
- Consolidate Python dependencies in a single `requirements.txt` or switch to `pyproject.toml` for project management.
- Provide a `Dockerfile` to simplify deployment.

