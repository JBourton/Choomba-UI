"""
Choomba Audio Activation Service (Daemon)
Coordinates local audio monitoring, double-clap transient detection, and WebSocket transport.
Designed for offline execution on Linux (PipeWire / PortAudio) with minimal resource usage.
"""

import asyncio
import json
import os
import signal
import sys
import time
from typing import Dict, Any, Optional

from .config import (
    HOST,
    PORT,
    SAMPLE_RATE,
    CHUNK_SIZE,
    DEFAULT_SENSITIVITY,
    MIN_CLAP_INTERVAL_MS,
    MAX_CLAP_INTERVAL_MS,
    MAX_TRANSIENT_DURATION_MS,
    COOLDOWN_MS,
    AUDIO_DEVICE_INDEX,
)
from .detector import DoubleClapDetector, PyAudioStream, MockAudioStream, ActivationEvent
from .server import LocalWebSocketServer


class ActivationService:
    """
    Core activation daemon for Choomba assistant.
    Monitors microphone audio stream locally, detects double-claps,
    and broadcasts activation events over local loopback WebSocket.
    """

    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        use_mock_audio: bool = False,
        sensitivity: float = DEFAULT_SENSITIVITY,
    ):
        self.host = host
        self.port = port
        self.use_mock_audio = use_mock_audio
        self.sensitivity = sensitivity

        # Initialize WebSocket server
        self.server = LocalWebSocketServer(
            host=self.host,
            port=self.port,
            on_command=self._handle_client_command,
        )

        # Initialize detector
        self.detector = DoubleClapDetector(
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE,
            sensitivity=self.sensitivity,
            min_clap_interval_ms=MIN_CLAP_INTERVAL_MS,
            max_clap_interval_ms=MAX_CLAP_INTERVAL_MS,
            max_transient_duration_ms=MAX_TRANSIENT_DURATION_MS,
            cooldown_ms=COOLDOWN_MS,
            on_activation=self._on_activation_detected,
            on_debug=self._on_detector_debug,
        )

        # Initialize audio stream
        if self.use_mock_audio:
            self.stream = MockAudioStream(sample_rate=SAMPLE_RATE, chunk_size=CHUNK_SIZE)
        else:
            self.stream = PyAudioStream(
                device_index=AUDIO_DEVICE_INDEX,
                requested_sample_rate=SAMPLE_RATE,
                chunk_size=CHUNK_SIZE,
            )

        self._is_running = False
        self._is_paused = False
        self._loop_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _on_detector_debug(self, msg: str) -> None:
        """Log transient detection details for user troubleshooting."""
        print(f"[ActivationService] {msg}")

    def _on_activation_detected(self, event: ActivationEvent) -> None:
        """Callback invoked by detector when a verified double clap occurs."""
        print(
            f"[ActivationService] >>> Double-clap DETECTED! "
            f"Interval: {event.metadata.get('interval_ms')}ms, "
            f"Noise Floor: {event.metadata.get('noise_floor')}, "
            f"Confidence: {event.metadata.get('confidence')}"
        )

        if self._loop and self.server.is_running:
            asyncio.run_coroutine_threadsafe(
                self.server.broadcast(event.to_dict()),
                self._loop,
            )

    async def _handle_client_command(
        self, command: Dict[str, Any], writer: asyncio.StreamWriter
    ) -> None:
        """Handle control messages from connected frontend clients."""
        action = command.get("action")

        if action == "ping":
            await self.server.send_to_client(writer, {"type": "pong"})

        elif action == "get_status":
            await self.server.send_to_client(writer, self.get_status())

        elif action == "set_sensitivity":
            new_sens = command.get("value")
            if new_sens is not None:
                self.sensitivity = float(new_sens)
                self.detector.set_sensitivity(self.sensitivity)
                print(f"[ActivationService] Sensitivity adjusted to: {self.sensitivity}")
                await self.server.broadcast(self.get_status())

        elif action == "pause":
            self._is_paused = True
            print("[ActivationService] Audio monitoring paused by frontend.")
            await self.server.broadcast(self.get_status())

        elif action == "resume":
            self._is_paused = False
            self.detector.reset_state()
            print("[ActivationService] Audio monitoring resumed by frontend.")
            await self.server.broadcast(self.get_status())

        elif action == "simulate_clap":
            # Testing helper triggered by dev controls
            event = ActivationEvent(
                type="activation.detected",
                method="double_clap",
                metadata={"interval_ms": 320.0, "simulated": True, "confidence": 1.0},
            )
            print("[ActivationService] Simulated double-clap triggered by client.")
            await self.server.broadcast(event.to_dict())

    def get_status(self) -> Dict[str, Any]:
        """Current operational status of the service."""
        dev_info = self.stream.get_device_info()
        return {
            "type": "status",
            "state": "paused" if self._is_paused else ("monitoring" if self._is_running else "stopped"),
            "method": "double_clap",
            "sensitivity": self.sensitivity,
            "connected_clients": self.server.client_count,
            "audio_device": dev_info.get("name", "None"),
            "sample_rate": self.stream.get_sample_rate(),
            "noise_floor": round(self.detector.noise_floor, 1),
        }

    async def _audio_processing_loop(self) -> None:
        """Asynchronous audio capture and processing loop."""
        chunk_size = CHUNK_SIZE
        loop = asyncio.get_running_loop()
        frame_counter = 0
        zero_frames = 0
        zero_warned = False
        # Audio-timeline clock: the detector measures burst durations and
        # inter-clap intervals from these timestamps, so they must follow the
        # captured audio rather than the (jittery) wall clock.
        audio_time = time.monotonic()

        while self._is_running:
            if self._is_paused:
                await asyncio.sleep(0.1)
                continue

            try:
                # Read PCM chunk from stream
                raw_bytes = await loop.run_in_executor(None, self.stream.read, chunk_size)
                if not raw_bytes:
                    await asyncio.sleep(0.01)
                    continue

                frame_counter += 1

                # Check if microphone is producing silent zeros
                if all(b == 0 for b in raw_bytes[:64]):
                    zero_frames += 1
                    if zero_frames >= 150 and not zero_warned:
                        zero_warned = True
                        print(
                            "[ActivationService] ⚠️ WARNING: Microphone is receiving all ZEROS. "
                            "Please check your input settings in Fedora (GNOME Settings -> Sound -> Input) "
                            "to ensure the correct microphone is selected and unmuted."
                        )
                else:
                    if zero_warned:
                        zero_warned = False
                        print("[ActivationService] Audio signal detected! Microphone is now receiving sound.")
                    zero_frames = 0

                # Process frame in transient detector
                self.detector.process_frame(raw_bytes, audio_time)
                audio_time += self.detector.chunk_duration_sec

                # Periodic acoustic heartbeat (every ~8 seconds)
                if frame_counter % 700 == 0:
                    thresh = self.detector.current_detection_threshold()
                    nf = self.detector.noise_floor
                    print(
                        f"[ActivationService] Ambient: {nf:.1f} RMS "
                        f"(peak {self.detector.background_peak:.1f}) | "
                        f"Trigger threshold: {thresh:.1f} | "
                        f"Clients: {self.server.client_count}"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ActivationService] Audio processing error: {e}")
                await asyncio.sleep(0.2)

    async def start(self) -> None:
        """Start both the WebSocket server and audio processing stream."""
        self._loop = asyncio.get_running_loop()
        self._is_running = True

        # Open audio stream
        try:
            self.stream.open()
            # Sync sample rate if hardware forced a specific rate (e.g. 48000).
            # set_sample_rate() also recomputes the high-pass coefficients and
            # the analysis-window geometry for the new rate.
            effective_rate = self.stream.get_sample_rate()
            self.detector.set_sample_rate(effective_rate)

            print(
                f"[ActivationService] Audio stream opened: {self.stream.get_device_info().get('name')} "
                f"at {effective_rate}Hz"
            )
        except Exception as e:
            print(f"[ActivationService] Warning: Could not open audio hardware ({e}). Falling back to mock stream.")
            self.stream = MockAudioStream(sample_rate=SAMPLE_RATE, chunk_size=CHUNK_SIZE)
            self.stream.open()

        # Start detector
        self.detector.start()

        # Start WebSocket transport
        await self.server.start()

        # Start background audio loop
        self._loop_task = asyncio.create_task(self._audio_processing_loop())
        print(f"[ActivationService] Ready and listening for double claps (sensitivity={self.sensitivity})...")

    async def stop(self) -> None:
        """Clean shutdown and release of audio hardware."""
        print("[ActivationService] Stopping service...")
        self._is_running = False

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

        self.detector.stop()
        self.stream.close()
        await self.server.stop()
        print("[ActivationService] Clean shutdown complete.")


def run_main():
    """CLI entry point for running the service directly or via systemd."""
    use_mock = "--mock" in sys.argv
    port_arg = PORT
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port_arg = int(sys.argv[i + 1])

    service = ActivationService(port=port_arg, use_mock_audio=use_mock)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler():
        print("\n[ActivationService] Interrupted by signal, shutting down...")
        asyncio.create_task(service.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Handle systems without loop.add_signal_handler support
            pass

    async def runner():
        await service.start()
        while service._is_running:
            await asyncio.sleep(0.5)

    try:
        loop.run_until_complete(runner())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.run_until_complete(service.stop())
        loop.close()


if __name__ == "__main__":
    run_main()
