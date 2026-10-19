"""
Choomba Double-Clap Detector
A lightweight, offline transient energy detector that identifies two consecutive claps.
Features DC-offset removal, 350Hz high-pass filtering (eliminates electrical hum and fan rumble),
crest-factor gating (impulsive transient verification), and adaptive noise floor tracking.
"""

import math
import struct
import time
from typing import Optional, Dict, Any, Callable, Tuple
from .base import BaseDetector, ActivationEvent, ActivationCallback

DebugCallback = Callable[[str], None]


class DoubleClapDetector(BaseDetector):
    """
    Detects two short, high-energy acoustic transients within a configurable window.
    Features:
    - Zero-centering (DC bias removal) & 350Hz single-pole IIR high-pass filter
    - Crest-factor analysis (rejects low-crest humming, speech vowels, and fan noise)
    - Adaptive background noise floor tracking (exponential moving average)
    - Minimum and maximum inter-clap interval enforcement
    - Maximum transient duration gating (rejects sustained sound)
    - Post-activation cooldown period to prevent duplicate triggers
    - Virtual time support for deterministic offline testing
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        chunk_size: int = 512,
        sensitivity: float = 0.8,
        min_clap_interval_ms: float = 140.0,
        max_clap_interval_ms: float = 850.0,
        max_transient_duration_ms: float = 220.0,
        cooldown_ms: float = 1500.0,
        on_activation: Optional[ActivationCallback] = None,
        on_debug: Optional[DebugCallback] = None,
    ):
        super().__init__(on_activation=on_activation)
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.min_clap_interval_ms = min_clap_interval_ms
        self.max_clap_interval_ms = max_clap_interval_ms
        self.max_transient_duration_ms = max_transient_duration_ms
        self.cooldown_ms = cooldown_ms
        self._on_debug = on_debug

        self.chunk_duration_sec = self.chunk_size / self.sample_rate
        self.chunk_duration_ms = self.chunk_duration_sec * 1000.0

        # High-pass filter coefficients (fc = 350 Hz to strip DC & 50/60Hz hum)
        fc = 350.0
        dt = 1.0 / self.sample_rate
        rc = 1.0 / (2.0 * math.pi * fc)
        self._hp_alpha = rc / (rc + dt)
        self._prev_x = 0.0
        self._prev_y = 0.0

        # Sensitivity tuning
        self._sensitivity = 0.8
        self._threshold_ratio = 2.0
        self._min_energy_threshold = 120.0
        self._min_crest_factor = 2.8
        self.set_sensitivity(sensitivity)

        # Dynamic state & adaptive noise floor
        self._noise_floor = 30.0
        self._noise_alpha = 0.05
        self._calibration_frames = 0
        self._calibration_target = 25

        # Transient burst tracking
        self._in_transient = False
        self._transient_start_time = 0.0
        self._transient_peak_rms = 0.0
        self._transient_is_invalid = False

        # Clap state machine: 'IDLE' -> 'WAITING_FOR_SECOND' -> 'COOLDOWN'
        self._state = "IDLE"
        self._first_clap_time = 0.0
        self._first_clap_peak = 0.0
        self._cooldown_until = 0.0

        # Virtual time tracking for testing
        self._virtual_time: float = 0.0
        self._use_virtual_time: bool = False

    def set_debug_callback(self, callback: Optional[DebugCallback]) -> None:
        self._on_debug = callback

    def _log_debug(self, msg: str) -> None:
        if self._on_debug:
            try:
                self._on_debug(msg)
            except Exception:
                pass

    def set_sensitivity(self, sensitivity: float) -> None:
        """
        Configure detector sensitivity between 0.1 (strict) and 1.0 (sensitive).
        Default is 0.8.
        """
        s = max(0.1, min(1.0, float(sensitivity)))
        self._sensitivity = s
        # Ratio above rolling noise floor:
        # At 0.1: 3.4x, At 0.8: 2.0x, At 1.0: 1.6x
        self._threshold_ratio = 3.6 - (s * 2.0)
        # Minimum absolute filtered RMS floor:
        # At 0.1: 350.0, At 0.8: 120.0, At 1.0: 60.0
        self._min_energy_threshold = 380.0 - (s * 320.0)
        # Minimum crest factor (peak/RMS):
        # Claps have crest 5-15. Hum/speech have crest 1.4-2.5.
        self._min_crest_factor = 3.4 - (s * 0.8)

    @property
    def sensitivity(self) -> float:
        return self._sensitivity

    @property
    def state(self) -> str:
        return self._state

    @property
    def noise_floor(self) -> float:
        return self._noise_floor

    def current_detection_threshold(self) -> float:
        """Compute effective RMS threshold based on sensitivity and ambient noise."""
        return max(self._min_energy_threshold, self._noise_floor * self._threshold_ratio)

    def set_virtual_time_mode(self, enabled: bool, start_time: float = 0.0) -> None:
        """Enable virtual time for deterministic unit testing without delays."""
        self._use_virtual_time = enabled
        self._virtual_time = start_time
        if enabled:
            self._calibration_frames = self._calibration_target

    def reset_state(self) -> None:
        """Reset internal detection state to IDLE."""
        self._state = "IDLE"
        self._in_transient = False
        self._first_clap_time = 0.0
        self._first_clap_peak = 0.0
        self._cooldown_until = 0.0
        self._transient_is_invalid = False
        self._prev_x = 0.0
        self._prev_y = 0.0

    def start(self) -> None:
        self.reset_state()
        if not self._use_virtual_time:
            self._calibration_frames = 0
        else:
            self._calibration_frames = self._calibration_target
        self._is_running = True

    def stop(self) -> None:
        self._is_running = False
        self.reset_state()

    def _get_current_time(self, frame_timestamp: Optional[float] = None) -> float:
        if frame_timestamp is not None:
            return frame_timestamp
        if self._use_virtual_time:
            t = self._virtual_time
            self._virtual_time += self.chunk_duration_sec
            return t
        return time.monotonic()

    def preprocess_chunk(self, raw_bytes: bytes) -> Tuple[float, float, float]:
        """
        Unpack 16-bit PCM, subtract mean (removes DC bias), and apply 350Hz high-pass filter.
        Returns: (rms, peak, crest_factor).
        """
        if not raw_bytes:
            return 0.0, 0.0, 1.0
        num_samples = len(raw_bytes) // 2
        if num_samples == 0:
            return 0.0, 0.0, 1.0

        try:
            samples = struct.unpack(f"{num_samples}h", raw_bytes)
        except struct.error:
            num_samples = len(raw_bytes) // 2
            samples = struct.unpack(f"{num_samples}h", raw_bytes[:num_samples * 2])

        # 1. Zero-center (instant DC bias removal)
        mean_offset = sum(samples) / num_samples

        # 2. 350Hz single-pole IIR high-pass filter
        filtered = []
        py, px = self._prev_y, self._prev_x
        alpha = self._hp_alpha
        for s in samples:
            x = s - mean_offset
            y = alpha * (py + x - px)
            filtered.append(y)
            py = y
            px = x
        self._prev_y = py
        self._prev_x = px

        # 3. Compute filtered metrics
        sum_sq = sum(v * v for v in filtered)
        rms = math.sqrt(sum_sq / num_samples)
        peak = max(abs(v) for v in filtered)
        crest = peak / max(1.0, rms)

        return rms, peak, crest

    def calculate_rms(self, raw_bytes: bytes) -> float:
        """Backwards-compatible helper returning filtered RMS."""
        rms, _, _ = self.preprocess_chunk(raw_bytes)
        return rms

    def process_frame(
        self, raw_bytes: bytes, frame_timestamp: Optional[float] = None
    ) -> Optional[ActivationEvent]:
        """
        Process a single PCM frame through DSP filter and evaluate transient energy & crest factor.
        Returns ActivationEvent on a detected double-clap sequence.
        """
        current_time = self._get_current_time(frame_timestamp)
        rms, peak, crest = self.preprocess_chunk(raw_bytes)

        # Rapid initial noise floor calibration during startup
        if self._calibration_frames < self._calibration_target:
            self._calibration_frames += 1
            sample_val = max(10.0, rms)
            self._noise_floor = ((self._noise_floor * (self._calibration_frames - 1)) + sample_val) / self._calibration_frames
            return None

        # Check cooldown state
        if self._state == "COOLDOWN":
            if current_time >= self._cooldown_until:
                self._state = "IDLE"
                self._log_debug("Cooldown period complete. State returned to IDLE.")
            else:
                self._noise_floor = (1.0 - self._noise_alpha) * self._noise_floor + self._noise_alpha * min(rms, self._noise_floor * 1.5)
                return None

        # Check timeout for waiting for second clap
        if self._state == "WAITING_FOR_SECOND":
            elapsed_ms = (current_time - self._first_clap_time) * 1000.0
            if elapsed_ms > self.max_clap_interval_ms:
                self._log_debug(f"Waiting for 2nd clap timed out ({elapsed_ms:.0f}ms > {self.max_clap_interval_ms:.0f}ms). Resetting to IDLE.")
                self._state = "IDLE"

        # A clap transient must meet BOTH:
        # 1. Energy jump above noise floor (rms >= detection_threshold)
        # 2. Impulsive crest factor (crest >= min_crest_factor, rejecting hum, fan noise, and continuous voice)
        detection_threshold = self.current_detection_threshold()
        is_transient = (rms >= detection_threshold) and (crest >= self._min_crest_factor)

        event_to_emit: Optional[ActivationEvent] = None

        if is_transient:
            if not self._in_transient:
                # Start of a new energy burst
                self._in_transient = True
                self._transient_start_time = current_time
                self._transient_peak_rms = rms
                self._transient_is_invalid = False
            else:
                # Continuing an existing burst
                burst_duration_ms = (current_time - self._transient_start_time) * 1000.0
                if rms > self._transient_peak_rms:
                    self._transient_peak_rms = rms

                # If energy stays high for too long, reject as sustained noise/speech/typing
                if burst_duration_ms > self.max_transient_duration_ms:
                    if not self._transient_is_invalid:
                        self._transient_is_invalid = True
                        self._log_debug(f"Sound rejected: sustained energy for {burst_duration_ms:.0f}ms > {self.max_transient_duration_ms:.0f}ms (speech or noise).")
        else:
            # Energy has fallen below threshold
            if self._in_transient:
                burst_duration_ms = (current_time - self._transient_start_time) * 1000.0
                was_valid_clap = (
                    not self._transient_is_invalid
                    and burst_duration_ms <= self.max_transient_duration_ms
                    and self._transient_peak_rms >= detection_threshold
                )

                self._in_transient = False

                if was_valid_clap:
                    event_to_emit = self._handle_valid_clap(self._transient_start_time, self._transient_peak_rms)

            # Update ambient noise floor when audio is calm
            self._noise_floor = (1.0 - self._noise_alpha) * self._noise_floor + self._noise_alpha * rms
            self._noise_floor = max(10.0, min(self._noise_floor, 3500.0))

        if event_to_emit:
            self._emit_activation(event_to_emit)
            return event_to_emit

        return None

    def _handle_valid_clap(self, clap_time: float, peak_rms: float) -> Optional[ActivationEvent]:
        """State transition handler when a short, sharp transient clap is confirmed."""
        if self._state == "IDLE":
            # First clap registered
            self._state = "WAITING_FOR_SECOND"
            self._first_clap_time = clap_time
            self._first_clap_peak = peak_rms
            self._log_debug(f"👏 Clap 1 registered! Peak RMS: {peak_rms:.1f} (Threshold: {self.current_detection_threshold():.1f}). Waiting for 2nd clap...")
            return None

        elif self._state == "WAITING_FOR_SECOND":
            delta_ms = (clap_time - self._first_clap_time) * 1000.0

            if delta_ms < self.min_clap_interval_ms:
                self._log_debug(f"Transient ignored: too fast ({delta_ms:.1f}ms < {self.min_clap_interval_ms:.1f}ms, echo/rebound).")
                return None

            if self.min_clap_interval_ms <= delta_ms <= self.max_clap_interval_ms:
                # Valid double-clap!
                self._state = "COOLDOWN"
                self._cooldown_until = clap_time + (self.cooldown_ms / 1000.0)

                confidence = min(0.99, round(peak_rms / max(self._noise_floor * 2.0, 1.0), 2))
                self._log_debug(f"👏 Clap 2 registered! Interval: {delta_ms:.1f}ms. >>> DOUBLE-CLAP ACTIVATION CONFIRMED!")

                event = ActivationEvent(
                    type="activation.detected",
                    method="double_clap",
                    metadata={
                        "interval_ms": round(delta_ms, 1),
                        "first_clap_rms": round(self._first_clap_peak, 1),
                        "second_clap_rms": round(peak_rms, 1),
                        "noise_floor": round(self._noise_floor, 1),
                        "confidence": confidence,
                    },
                )
                return event
            else:
                # Outside window - treat this new clap as potential first clap
                self._log_debug(f"Interval {delta_ms:.1f}ms exceeded window ({self.max_clap_interval_ms:.1f}ms). Treating as new Clap 1.")
                self._first_clap_time = clap_time
                self._first_clap_peak = peak_rms
                return None

        return None
