"""
Choomba Audio Activation Configuration
Centralized configuration parameters with environment variable overrides.
"""

import os

# Server Network Configuration (STRICTLY LOOPBACK FOR LOCAL PRIVACY)
HOST = os.environ.get("CHOOMBA_HOST", "127.0.0.1")
PORT = int(os.environ.get("CHOOMBA_PORT", "8765"))

# Allowed Browser Origins for WebSocket Handshake (Security)
ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
}

# Audio Capture Parameters
AUDIO_DEVICE_INDEX = (
    int(os.environ["CHOOMBA_AUDIO_DEVICE"])
    if "CHOOMBA_AUDIO_DEVICE" in os.environ
    else None
)
SAMPLE_RATE = int(os.environ.get("CHOOMBA_SAMPLE_RATE", "44100"))
CHUNK_SIZE = int(os.environ.get("CHOOMBA_CHUNK_SIZE", "512"))
CHANNELS = 1

# Clap Detection Timing Parameters
DEFAULT_SENSITIVITY = float(os.environ.get("CHOOMBA_SENSITIVITY", "0.8"))
MIN_CLAP_INTERVAL_MS = float(os.environ.get("CHOOMBA_MIN_CLAP_INTERVAL_MS", "140.0"))
MAX_CLAP_INTERVAL_MS = float(os.environ.get("CHOOMBA_MAX_CLAP_INTERVAL_MS", "850.0"))
# A hand clap is 1-3 ms wide. The capture chunk is ~11.6 ms, so anything that
# stays loud for longer than a handful of chunks is continuous sound (speech,
# music, a passing car) and must not be treated as a clap.
MAX_TRANSIENT_DURATION_MS = float(os.environ.get("CHOOMBA_MAX_TRANSIENT_DURATION_MS", "60.0"))
COOLDOWN_MS = float(os.environ.get("CHOOMBA_COOLDOWN_MS", "1500.0"))

# Frontend Session Timeout (Auto-return to IDLE if no command follows activation)
FRONTEND_ACTIVATION_TIMEOUT_MS = int(os.environ.get("CHOOMBA_SESSION_TIMEOUT_MS", "8000"))
