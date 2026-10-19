"""
Choomba Activation Detector Base Interface
Defines the abstract interface for modular activation detection engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any


@dataclass
class ActivationEvent:
    """Explicit event contract emitted upon successful activation."""
    type: str = "activation.detected"
    method: str = "double_clap"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "method": self.method,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


ActivationCallback = Callable[[ActivationEvent], None]


class BaseDetector(ABC):
    """
    Abstract base class for all activation detectors.
    Allows easy swapping between double-clap, wake-word, or other trigger mechanisms.
    """

    def __init__(self, on_activation: Optional[ActivationCallback] = None):
        self._on_activation: Optional[ActivationCallback] = on_activation
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        """Return whether the detector is currently monitoring."""
        return self._is_running

    def set_callback(self, callback: ActivationCallback) -> None:
        """Register or update the activation callback."""
        self._on_activation = callback

    def _emit_activation(self, event: ActivationEvent) -> None:
        """Internal helper to dispatch the activation event to the registered listener."""
        if self._on_activation:
            try:
                self._on_activation(event)
            except Exception as e:
                print(f"[Detector] Error in activation callback: {e}")

    @abstractmethod
    def start(self) -> None:
        """Start monitoring audio input."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop monitoring audio input and release resources."""
        pass

    @abstractmethod
    def process_frame(self, raw_bytes: bytes) -> Optional[ActivationEvent]:
        """
        Process a single chunk of PCM audio data.
        Returns an ActivationEvent if an activation is triggered by this frame, else None.
        """
        pass

    @abstractmethod
    def set_sensitivity(self, sensitivity: float) -> None:
        """Configure detector sensitivity (0.1 - 1.0)."""
        pass
