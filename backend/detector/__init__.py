"""
Choomba Audio Activation Detector Package
"""

from .base import BaseDetector, ActivationEvent, ActivationCallback
from .clap_detector import DoubleClapDetector
from .audio_stream import AudioStreamInterface, PyAudioStream, MockAudioStream

__all__ = [
    "BaseDetector",
    "ActivationEvent",
    "ActivationCallback",
    "DoubleClapDetector",
    "AudioStreamInterface",
    "PyAudioStream",
    "MockAudioStream",
]
