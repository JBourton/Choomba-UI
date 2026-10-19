"""
Choomba Audio Stream Abstraction
Provides hardware capture via PyAudio/PortAudio/PipeWire and mock stream support for tests.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import sys
import time


class AudioStreamInterface(ABC):
    """Abstract interface for audio capture streams."""

    @abstractmethod
    def open(self) -> bool:
        """Initialize and open the audio stream."""
        pass

    @abstractmethod
    def read(self, num_frames: int) -> bytes:
        """Read num_frames from the audio input."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the audio stream and release resources."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check if the stream is currently open and active."""
        pass

    @abstractmethod
    def get_sample_rate(self) -> int:
        """Return the effective sample rate in Hz."""
        pass

    @abstractmethod
    def get_device_info(self) -> Dict[str, Any]:
        """Return metadata about the current input device."""
        pass


class PyAudioStream(AudioStreamInterface):
    """
    Hardware audio capture stream using PyAudio / PortAudio.
    Seamlessly integrates with PipeWire on Fedora Linux.
    """

    def __init__(
        self,
        device_index: Optional[int] = None,
        requested_sample_rate: int = 44100,
        chunk_size: int = 512,
        channels: int = 1,
    ):
        self.device_index = device_index
        self.requested_sample_rate = requested_sample_rate
        self.chunk_size = chunk_size
        self.channels = channels

        self._pyaudio_instance = None
        self._stream = None
        self._effective_sample_rate = requested_sample_rate
        self._device_info: Dict[str, Any] = {}
        self._is_open = False

    def open(self) -> bool:
        """Initialize PortAudio and open input stream."""
        try:
            import pyaudio
        except ImportError:
            raise RuntimeError(
                "PyAudio is not installed. Install python3-pyaudio on Fedora: 'sudo dnf install python3-pyaudio'"
            )

        # Suppress ALSA C-level device probe logs (dsnoop, dmix, surround) on Linux
        try:
            import ctypes
            ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(
                None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p
            )
            def py_error_handler(filename, line, function, err, fmt):
                pass
            self._c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
            asound = ctypes.cdll.LoadLibrary("libasound.so.2")
            asound.snd_lib_error_set_handler(self._c_error_handler)
        except Exception:
            pass

        self._pyaudio_instance = pyaudio.PyAudio()

        # Find input device
        try:
            if self.device_index is not None:
                dev_info = self._pyaudio_instance.get_device_info_by_index(self.device_index)
                native_rate = int(dev_info.get("defaultSampleRate", 44100))
            else:
                try:
                    dev_info = self._pyaudio_instance.get_default_input_device_info()
                    native_rate = int(dev_info.get("defaultSampleRate", 44100))
                except Exception:
                    dev_info = {"name": "Default Audio Input"}
                    native_rate = 44100
            
            self._device_info = dev_info
        except Exception as e:
            self.close()
            raise RuntimeError(f"No suitable audio input device found: {e}")

        # Hardware ALSA / PipeWire devices on Linux often require their native sample rate (e.g. 44100 or 48000)
        candidate_rates = [native_rate, self.requested_sample_rate, 44100, 48000, 16000]
        # Remove duplicates while preserving order
        candidate_rates = list(dict.fromkeys(candidate_rates))

        last_error = None
        for rate in candidate_rates:
            try:
                open_kwargs = {
                    "format": pyaudio.paInt16,
                    "channels": self.channels,
                    "rate": rate,
                    "input": True,
                    "frames_per_buffer": self.chunk_size,
                }
                if self.device_index is not None:
                    open_kwargs["input_device_index"] = self.device_index

                self._stream = self._pyaudio_instance.open(**open_kwargs)
                self._effective_sample_rate = rate
                self._is_open = True
                return True
            except Exception as e:
                last_error = e
                continue

        self.close()
        raise RuntimeError(f"Failed to open audio stream on device {self.device_index}: {last_error}")

    def read(self, num_frames: int) -> bytes:
        if not self._is_open or not self._stream:
            return b""
        try:
            return self._stream.read(num_frames, exception_on_overflow=False)
        except Exception as e:
            # Handle audio underrun or temporary glitch
            return b"\x00" * (num_frames * 2 * self.channels)

    def close(self) -> None:
        self._is_open = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pyaudio_instance:
            try:
                self._pyaudio_instance.terminate()
            except Exception:
                pass
            self._pyaudio_instance = None

    def is_active(self) -> bool:
        return self._is_open and (self._stream is not None)

    def get_sample_rate(self) -> int:
        return self._effective_sample_rate

    def get_device_info(self) -> Dict[str, Any]:
        return {
            "index": self.device_index,
            "name": self._device_info.get("name", "Unknown Audio Device"),
            "sample_rate": self._effective_sample_rate,
            "channels": self.channels,
        }


class MockAudioStream(AudioStreamInterface):
    """
    Mock audio capture stream for automated unit testing.
    Feeds pre-programmed audio chunks into the detector.

    When the queue is empty the stream returns silence *paced at the real
    capture rate*, so a mock session has the same timing behaviour as real
    hardware.  Without that pacing a mock session would deliver frames faster
    than real time and any timing-sensitive logic (inter-clap intervals,
    transient durations) would be measured against a fictitious clock.
    """

    def __init__(self, sample_rate: int = 44100, chunk_size: int = 512):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self._queue: List[bytes] = []
        self._is_open = False

    def enqueue_chunk(self, raw_bytes: bytes) -> None:
        self._queue.append(raw_bytes)

    def enqueue_silence(self, num_chunks: int = 1) -> None:
        silence = b"\x00" * (self.chunk_size * 2)
        for _ in range(num_chunks):
            self._queue.append(silence)

    def open(self) -> bool:
        self._is_open = True
        return True

    def read(self, num_frames: int) -> bytes:
        if self._queue:
            return self._queue.pop(0)
        # No data queued: behave like a real capture device and deliver one
        # chunk worth of silence every chunk_duration.
        time.sleep(num_frames / self.sample_rate)
        return b"\x00" * (num_frames * 2)

    def close(self) -> None:
        self._is_open = False
        self._queue.clear()

    def is_active(self) -> bool:
        return self._is_open

    def get_sample_rate(self) -> int:
        return self.sample_rate

    def get_device_info(self) -> Dict[str, Any]:
        return {
            "index": -1,
            "name": "Mock Synthetic Stream",
            "sample_rate": self.sample_rate,
            "channels": 1,
        }
