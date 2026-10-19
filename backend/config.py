"""
Choomba Audio Activation Configuration
Centralized configuration parameters with environment variable overrides.
"""

import os
from typing import Any, Dict, Optional

# =============================================================================
#  APP SETTINGS
#  -----------------------------------------------------------------------------
#  This is the one place to tweak the activation daemon.  Every value can be
#  overridden with an environment variable of the same name, prefixed with
#  CHOOMBA_ (for example CHOOMBA_CLAP_SENSITIVITY=0.5).
#
#  The three settings marked [UI] are also editable in the app, in
#  Settings Drawer -> "3. Voice Activation".  The rest are for when you want
#  to go deeper.
# =============================================================================
APP_SETTINGS: Dict[str, Any] = {
    # --- voice activation ---------------------------------------------------
    # [UI] How sensitive the double-clap detector is, 0.1 (strict) - 1.0
    # (sensitive).  It only moves the amplitude margin between the two
    # "clap_ratio_*" values below.
    "clap_sensitivity": 0.8,
    # [UI] How far above the ambient a clap has to be, expressed as a multiple
    # of the ambient peak level.  The lower number is used at maximum
    # sensitivity, the higher one at minimum sensitivity.  Raising these is
    # the bluntest way to stop the detector reacting to speech and typing.
    "clap_ratio_sensitive": 1.5,
    "clap_ratio_strict": 2.8,
    # [UI] How much of a burst has to come from the low band (60-300 Hz) for
    # it to count as the thud of a slap rather than a click or a speech sound.
    # 0 disables the test, 0.4 is a sensible default, 0.6 is strict.
    "clap_min_low_band_share": 0.40,
    # [UI] How much of a burst has to come from the crack band (1.2-12 kHz).
    # A clap has a broadband crack, a voice hardly has any.
    "clap_min_crack_band_share": 0.20,
    # [UI] How far apart the two strikes may be, in milliseconds.  A normal
    # double clap is 150-450 ms apart.
    "clap_min_interval_ms": 150.0,
    "clap_max_interval_ms": 450.0,
    # How long a matched pair is held before it is confirmed.  A third burst
    # of comparable level inside this window cancels the pair, which is what
    # stops a train of key presses from being reported as a double clap.
    "clap_pair_confirmation_ms": 450.0,
    # A burst that stays loud for longer than this is continuous sound.
    "clap_max_transient_duration_ms": 60.0,
    # How long the detector stays quiet after an activation.
    "clap_cooldown_ms": 1500.0,
    # [UI] Absolute floor for a transient, in 16-bit linear units (peak scale).
    # A hand clap is loud in absolute terms, so this is what stops the
    # detector from reacting to speech or key presses in a quiet room, where a
    # relative threshold alone cannot tell them apart.
    "clap_min_peak_threshold": 6000.0,
    # --- audio capture ------------------------------------------------------
    "audio_device": None,
    "sample_rate": 44100,
    "chunk_size": 512,
    # --- network ------------------------------------------------------------
    "host": "127.0.0.1",
    "port": 8765,
    # --- web socket ---------------------------------------------------------
    "allowed_origins": [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    "session_timeout_ms": 8000,
}

#: Settings the UI is allowed to change at runtime.
UI_EDITABLE_SETTINGS = (
    "clap_sensitivity",
    "clap_min_low_band_share",
    "clap_min_crack_band_share",
    "clap_max_interval_ms",
    "clap_min_interval_ms",
    "clap_pair_confirmation_ms",
    "clap_min_peak_threshold",
)


def _env(name: str, default: Any, cast=None) -> Any:
    """Read a setting from the environment, falling back to the default."""
    raw = os.environ.get(f"CHOOMBA_{name.upper()}")
    if raw is None:
        return default
    try:
        return cast(raw) if cast else raw
    except (TypeError, ValueError):
        return default


# Apply the environment overrides to APP_SETTINGS.
APP_SETTINGS["clap_sensitivity"] = _env(
    "clap_sensitivity", APP_SETTINGS["clap_sensitivity"], float)
APP_SETTINGS["clap_ratio_sensitive"] = _env(
    "clap_ratio_sensitive", APP_SETTINGS["clap_ratio_sensitive"], float)
APP_SETTINGS["clap_ratio_strict"] = _env(
    "clap_ratio_strict", APP_SETTINGS["clap_ratio_strict"], float)
APP_SETTINGS["clap_min_low_band_share"] = _env(
    "clap_min_low_band_share", APP_SETTINGS["clap_min_low_band_share"], float)
APP_SETTINGS["clap_min_crack_band_share"] = _env(
    "clap_min_crack_band_share", APP_SETTINGS["clap_min_crack_band_share"], float)
APP_SETTINGS["clap_min_interval_ms"] = _env(
    "clap_min_interval_ms", APP_SETTINGS["clap_min_interval_ms"], float)
APP_SETTINGS["clap_max_interval_ms"] = _env(
    "clap_max_interval_ms", APP_SETTINGS["clap_max_interval_ms"], float)
APP_SETTINGS["clap_pair_confirmation_ms"] = _env(
    "clap_pair_confirmation_ms", APP_SETTINGS["clap_pair_confirmation_ms"], float)
APP_SETTINGS["clap_max_transient_duration_ms"] = _env(
    "clap_max_transient_duration_ms",
    APP_SETTINGS["clap_max_transient_duration_ms"], float)
APP_SETTINGS["clap_cooldown_ms"] = _env(
    "clap_cooldown_ms", APP_SETTINGS["clap_cooldown_ms"], float)
APP_SETTINGS["clap_min_peak_threshold"] = _env(
    "clap_min_peak_threshold", APP_SETTINGS["clap_min_peak_threshold"], float)
APP_SETTINGS["audio_device"] = _env(
    "audio_device", APP_SETTINGS["audio_device"], int)
APP_SETTINGS["sample_rate"] = _env(
    "sample_rate", APP_SETTINGS["sample_rate"], int)
APP_SETTINGS["chunk_size"] = _env(
    "chunk_size", APP_SETTINGS["chunk_size"], int)
APP_SETTINGS["host"] = _env("host", APP_SETTINGS["host"])
APP_SETTINGS["port"] = _env("port", APP_SETTINGS["port"], int)
APP_SETTINGS["session_timeout_ms"] = _env(
    "session_timeout_ms", APP_SETTINGS["session_timeout_ms"], int)

# --- Backwards compatible module level names --------------------------------
# The rest of the code base and the service file still use these.

HOST = APP_SETTINGS["host"]
PORT = APP_SETTINGS["port"]
ALLOWED_ORIGINS = set(APP_SETTINGS["allowed_origins"])

AUDIO_DEVICE_INDEX: Optional[int] = APP_SETTINGS["audio_device"]
SAMPLE_RATE = APP_SETTINGS["sample_rate"]
CHUNK_SIZE = APP_SETTINGS["chunk_size"]
CHANNELS = 1

DEFAULT_SENSITIVITY = APP_SETTINGS["clap_sensitivity"]
MIN_CLAP_INTERVAL_MS = APP_SETTINGS["clap_min_interval_ms"]
MAX_CLAP_INTERVAL_MS = APP_SETTINGS["clap_max_interval_ms"]
MAX_TRANSIENT_DURATION_MS = APP_SETTINGS["clap_max_transient_duration_ms"]
COOLDOWN_MS = APP_SETTINGS["clap_cooldown_ms"]
PAIR_CONFIRMATION_MS = APP_SETTINGS["clap_pair_confirmation_ms"]
MIN_LOW_BAND_SHARE = APP_SETTINGS["clap_min_low_band_share"]
MIN_CRACK_BAND_SHARE = APP_SETTINGS["clap_min_crack_band_share"]
RATIO_SENSITIVE = APP_SETTINGS["clap_ratio_sensitive"]
RATIO_STRICT = APP_SETTINGS["clap_ratio_strict"]
MIN_PEAK_THRESHOLD = APP_SETTINGS["clap_min_peak_threshold"]

FRONTEND_ACTIVATION_TIMEOUT_MS = APP_SETTINGS["session_timeout_ms"]
