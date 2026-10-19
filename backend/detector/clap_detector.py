"""
Choomba Double-Clap Detector
A lightweight, offline transient energy detector that identifies two consecutive claps.

Signal-processing model
-----------------------
A hand clap is a *short, high-amplitude impulse*.  Detecting one in a noisy
room needs three independent properties, and this detector measures each of
them explicitly:

1. **Amplitude - the frame peak.**
   The transient amplitude is the largest sample of the high-passed frame.
   A peak is not diluted by the length of the capture window, so a 1-3 ms
   clap keeps its full amplitude, and it is measured with a low variance
   (~4 % run to run) compared with an energy statistic (~15 %).  An earlier
   revision compared the *chunk RMS* against the threshold; that diluted a
   clap by roughly 8x while leaving sustained background noise untouched, so
   the detector actually ranked loud background noise above real claps.

2. **Concentration - how much of the frame is loud.**
   The frame is split into overlapping analysis windows.  A clap puts its
   energy into one or two of them, while continuous sound (speech, music, a
   fan, a passing car) fills every window.  The windows are compared against
   the tracked ambient *loudness*, so the test does not depend on how loud
   the room itself is.

3. **Duration - how long the transient lasts.**
   Measured across frames: a burst that stays loud for longer than
   ``max_transient_duration_ms`` is continuous sound, not a clap.

A fourth rule rejects single-sample glitches: the transient has to exceed
the ambient peak level for more than one sample.

The ambient level is tracked with an exponential moving average of the same
statistic that is tested (the frame peak for the amplitude test, the
short-window RMS for the concentration test), so every comparison stays in
one consistent scale.  The estimator is updated on every frame - never
frozen while loud frames are classified as transients - and deliberately has
no absolute ceiling, so a loud room raises the threshold instead of pinning
it.
"""

import math
import struct
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, Tuple, List

from .base import BaseDetector, ActivationEvent, ActivationCallback

DebugCallback = Callable[[str], None]

# ---------------------------------------------------------------------------
# Tunable signal-processing constants
# ---------------------------------------------------------------------------

#: Length of the sliding analysis window used to measure how *concentrated* a
#: transient is.  1.45 ms is fine enough to separate a 3 ms clap from a
#: 12 ms burst, and long enough to give a stable per-window peak.
ANALYSIS_WINDOW_MS = 1.45

#: A transient has to exceed the tracked background peak for at least this
#: many samples.  A single-sample glitch (USB/ALSA artefact) is rejected by
#: this test, a real clap exceeds the room's peak level for several samples.
MIN_BURST_SAMPLES = 4

#: Maximum fraction of the analysis windows that may be loud for a frame to
#: still count as impulsive.  A clap lights up one or two windows
#: (~0.05-0.2), continuous sound lights up all of them (1.0).
MAX_LOUD_WINDOW_FRACTION = 0.45

#: A window counts as "loud" when its level exceeds the ambient level by at
#: least this fraction of the loudest window in the same frame.
SUSTAIN_EXCESS_FRACTION = 0.5

#: Upper bound of the reported confidence.
CONFIDENCE_MAX = 0.99

#: The energy component of the confidence saturates once a clap reaches this
#: multiple of the detection threshold.
CONFIDENCE_ENERGY_FULL_MARGIN = 2.0

#: Lower bound of the tracked background peak (16-bit linear units).  This is
#: the only floor the noise estimator has - deliberately *not* an upper one.
MIN_BACKGROUND_PEAK = 1.0

#: Time constant of the background estimator, expressed as the fraction of the
#: error corrected per analysed frame (11.6 ms).  It is deliberately slow
#: compared with the release of a normal AGC: an impulsive event may lift the
#: estimate a little, but a steady level change is followed within ~0.4 s.
FLOOR_ALPHA = 0.03

#: Smoothing factor of the DC-offset tracker.  A *slow* tracker is used on
#: purpose: a per-chunk mean would subtract the transient's own energy from
#: every sample (attenuating the clap) and would step the filter input at
#: every chunk boundary (ringing the high-pass and inflating the peak).
DC_TRACKER_ALPHA = 0.05


def _median(values: List[float]) -> float:
    """Median of a list of floats (robust against a single outlier)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


@dataclass(frozen=True)
class FrameAnalysis:
    """Acoustic statistics of a single analysed frame.

    All amplitude values are in 16-bit linear units of the 350 Hz high-passed
    signal (full scale = 32768), so every value here is directly comparable
    with the other values here and with the matching detection threshold.
    """

    rms: float
    """RMS over the whole capture chunk (reporting / legacy API)."""

    peak: float
    """Largest absolute sample value in the chunk - the transient amplitude."""

    crest: float
    """peak / rms crest factor of the chunk (reporting / legacy API)."""

    level: float
    """Largest short-window RMS in the chunk."""

    window_levels: Tuple[float, ...]
    """RMS of each sliding analysis window (concentration test)."""

    loud_samples: int
    """Number of samples at or above the tracked background peak."""


class DoubleClapDetector(BaseDetector):
    """
    Detects two short, high-energy acoustic transients within a configurable window.
    Features:
    - Zero-centering (DC bias removal) & 350Hz single-pole IIR high-pass filter
    - Peak based transient amplitude measurement (brief impulses are preserved)
    - Window concentration gating (rejects speech, music, fan and other
      continuous sound regardless of the absolute room level)
    - Minimum burst width gating (rejects single-sample glitches)
    - Adaptive background tracking (EMA, no absolute ceiling)
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
        max_transient_duration_ms: float = 60.0,
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

        # Derived DSP parameters (filter coefficients, window geometry, frame
        # timing).  Recomputed by set_sample_rate() when the hardware forces a
        # different rate than the one the daemon was configured with.
        self._configure_derived(sample_rate)

        # Sensitivity tuning
        self._sensitivity = 0.8
        self._threshold_ratio = 2.0
        self._min_peak_threshold = 1200.0
        self._max_loud_window_fraction = MAX_LOUD_WINDOW_FRACTION
        self.set_sensitivity(sensitivity)

        # Dynamic state & adaptive background level.  Two statistics are
        # tracked, each one measured with the same statistic that the
        # corresponding test uses:
        #   _background_peak  - the ambient *peak* level (peak scale), used by
        #                       the amplitude test and the burst width test
        #   _background_level - the ambient *loudness* (RMS scale), used by the
        #                       concentration test and reported to the client
        self._background_peak = 1000.0
        self._background_level = 500.0
        self._calibration_frames = 0
        self._calibration_target = 25
        self._calibration_peaks: List[float] = []
        self._calibration_levels: List[float] = []

        # DC offset tracker (slow, see DC_TRACKER_ALPHA)
        self._dc_offset = 0.0

        # Transient burst tracking
        self._in_transient = False
        self._transient_start_time = 0.0
        self._transient_peak = 0.0
        self._transient_level = 0.0
        self._transient_threshold = 0.0
        self._transient_is_invalid = False

        # Clap state machine: 'IDLE' -> 'WAITING_FOR_SECOND' -> 'COOLDOWN'
        self._state = "IDLE"
        self._first_clap_time = 0.0
        self._first_clap_peak = 0.0
        self._first_clap_level = 0.0
        self._cooldown_until = 0.0

        # Virtual time tracking for testing
        self._virtual_time: float = 0.0
        self._use_virtual_time: bool = False

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _configure_derived(self, sample_rate: int) -> None:
        """(Re)compute every parameter that depends on the sample rate."""
        self.sample_rate = sample_rate
        self.chunk_duration_sec = self.chunk_size / sample_rate
        self.chunk_duration_ms = self.chunk_duration_sec * 1000.0

        # High-pass filter coefficients (fc = 350 Hz to strip DC & 50/60Hz hum)
        fc = 350.0
        dt = 1.0 / sample_rate
        rc = 1.0 / (2.0 * math.pi * fc)
        self._hp_alpha = rc / (rc + dt)

        # Sliding analysis window geometry (50% overlap)
        window = int(round(sample_rate * ANALYSIS_WINDOW_MS / 1000.0))
        self._window_size = max(16, min(self.chunk_size, window))
        self._window_hop = max(1, self._window_size // 2)

    def set_sample_rate(self, sample_rate: int) -> None:
        """Update the effective sample rate (hardware may force a different rate)."""
        if sample_rate <= 0 or sample_rate == self.sample_rate:
            return
        self._configure_derived(sample_rate)

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

        The sensitivity scales how far above the tracked background a
        transient must stand.  It deliberately does *not* relax the
        concentration or burst width tests: continuous background sound and
        single-sample glitches are rejected on shape, not on level, so
        lowering the sensitivity can never turn a fan or a passing car into a
        clap.
        """
        s = max(0.1, min(1.0, float(sensitivity)))
        self._sensitivity = s
        # How far above the background peak a transient must stand:
        # At 0.1: 1.94x (5.8 dB), At 0.8: 1.52x (3.6 dB), At 1.0: 1.40x (2.9 dB)
        self._threshold_ratio = 2.0 - (s * 0.6)
        # Minimum absolute peak floor (16-bit linear units).  A real hand clap
        # peaks between -20 dBFS and full scale, so the floor is set well
        # above the level of an ordinary impulsive artefact:
        # At 0.1: 4600.0, At 0.8: 1800.0, At 1.0: 1000.0
        self._min_peak_threshold = 5000.0 - (s * 4000.0)
        # Maximum fraction of analysis windows allowed to be loud in one frame.
        self._max_loud_window_fraction = MAX_LOUD_WINDOW_FRACTION

    @property
    def sensitivity(self) -> float:
        return self._sensitivity

    @property
    def state(self) -> str:
        return self._state

    @property
    def noise_floor(self) -> float:
        """Tracked ambient loudness (16-bit linear units, RMS scale)."""
        return self._background_level

    @property
    def background_peak(self) -> float:
        """Tracked ambient peak level (16-bit linear units, peak scale)."""
        return self._background_peak

    def current_detection_threshold(self) -> float:
        """Effective transient amplitude threshold (peak scale, as measured)."""
        return max(self._min_peak_threshold, self._background_peak * self._threshold_ratio)

    def set_virtual_time_mode(self, enabled: bool, start_time: float = 0.0) -> None:
        """Enable virtual time for deterministic unit testing without delays."""
        self._use_virtual_time = enabled
        self._virtual_time = start_time

    def reset_state(self) -> None:
        """Reset internal detection state to IDLE."""
        self._state = "IDLE"
        self._in_transient = False
        self._first_clap_time = 0.0
        self._first_clap_peak = 0.0
        self._first_clap_level = 0.0
        self._cooldown_until = 0.0
        self._transient_is_invalid = False
        self._prev_x = 0.0
        self._prev_y = 0.0

    def start(self) -> None:
        self.reset_state()
        self._calibration_frames = 0
        self._calibration_peaks = []
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

    # ------------------------------------------------------------------
    # Signal processing
    # ------------------------------------------------------------------

    def _window_levels(self, filtered: List[float]) -> List[float]:
        """RMS of each sliding analysis window (50% overlap)."""
        n = len(filtered)
        w = self._window_size
        if n < w:
            return [math.sqrt(sum(v * v for v in filtered) / n) if n else 0.0]
        starts = list(range(0, n - w + 1, self._window_hop))
        if starts[-1] != n - w:
            starts.append(n - w)
        return [
            math.sqrt(sum(v * v for v in filtered[s:s + w]) / w)
            for s in starts
        ]

    def analyze_frame(self, raw_bytes: bytes) -> FrameAnalysis:
        """
        Unpack 16-bit PCM, remove DC bias, apply the 350Hz high-pass filter and
        measure the frame statistics.
        """
        if not raw_bytes:
            return FrameAnalysis(0.0, 0.0, 1.0, 0.0, (), 0)
        num_samples = len(raw_bytes) // 2
        if num_samples == 0:
            return FrameAnalysis(0.0, 0.0, 1.0, 0.0, (), 0)

        try:
            samples = struct.unpack(f"{num_samples}h", raw_bytes)
        except struct.error:
            num_samples = len(raw_bytes) // 2
            samples = struct.unpack(f"{num_samples}h", raw_bytes[:num_samples * 2])

        # 1. DC removal via a slow running estimate of the input offset.
        mean_offset = sum(samples) / num_samples
        self._dc_offset = ((1.0 - DC_TRACKER_ALPHA) * self._dc_offset
                           + DC_TRACKER_ALPHA * mean_offset)
        dc = self._dc_offset

        # 2. 350Hz single-pole IIR high-pass filter
        filtered = []
        py, px = self._prev_y, self._prev_x
        alpha = self._hp_alpha
        for s in samples:
            x = s - dc
            y = alpha * (py + x - px)
            filtered.append(y)
            py = y
            px = x
        self._prev_y = py
        self._prev_x = px

        # 3. Whole-chunk statistics
        sum_sq = sum(v * v for v in filtered)
        rms = math.sqrt(sum_sq / num_samples)
        peak = max(abs(v) for v in filtered)
        crest = peak / max(1.0, rms)
        windows = tuple(self._window_levels(filtered))
        level = max(windows) if windows else rms

        # 4. How many samples are genuinely above the room's usual peak?  A
        #    single-sample glitch produces one, a real clap produces several.
        background = self._background_peak
        loud_samples = 0
        if background > 0.0:
            for v in filtered:
                if abs(v) >= background:
                    loud_samples += 1

        return FrameAnalysis(
            rms, peak, crest, level, windows, loud_samples
        )

    def preprocess_chunk(self, raw_bytes: bytes) -> Tuple[float, float, float]:
        """
        Backwards-compatible helper: (rms, peak, crest_factor) of the chunk.
        Prefer analyze_frame() which also exposes the peak based statistics.
        """
        analysis = self.analyze_frame(raw_bytes)
        return analysis.rms, analysis.peak, analysis.crest

    def calculate_rms(self, raw_bytes: bytes) -> float:
        """Backwards-compatible helper returning filtered RMS."""
        rms, _, _ = self.preprocess_chunk(raw_bytes)
        return rms

    def _loud_window_fraction(self, window_levels: Tuple[float, ...]) -> float:
        """
        Fraction of analysis windows that carry energy above the ambient level.

        Each window's *excess* over the tracked ambient loudness is computed
        (in power, so the excess is a level again), and a window counts as
        loud when it holds at least half of the frame's loudest excess.  A
        clap concentrates its energy into one or two windows (a small
        fraction); continuous sound fills every window (a fraction of 1.0).

        Because the excess is measured against the ambient level, the result
        does not depend on how loud the room itself is.
        """
        if not window_levels:
            return 1.0
        background = self._background_level
        excesses = []
        for level in window_levels:
            excess_sq = level * level - background * background
            excesses.append(math.sqrt(excess_sq) if excess_sq > 0.0 else 0.0)
        max_excess = max(excesses)
        if max_excess <= 0.0:
            # Nothing stands above the ambient level -> not an impulse.
            return 1.0
        cutoff = SUSTAIN_EXCESS_FRACTION * max_excess
        loud = sum(1 for e in excesses if e >= cutoff)
        return loud / len(excesses)

    def _update_background(self, peak: float, level: float) -> None:
        """
        Exponential moving averages of the ambient peak level and loudness.

        The time constant is long enough that an impulsive event barely moves
        the estimates, and short enough to follow a real change of the room
        level within a few hundred milliseconds.  They are updated on *every*
        frame - including frames that were classified as transients - so a
        burst of loud sound can never freeze the estimator the way the
        previous implementation did.  There is deliberately no upper bound:
        the threshold has to keep rising in a loud room instead of being
        pinned at a fixed ceiling.
        """
        self._background_peak += FLOOR_ALPHA * (peak - self._background_peak)
        self._background_level += FLOOR_ALPHA * (level - self._background_level)
        if self._background_peak < MIN_BACKGROUND_PEAK:
            self._background_peak = MIN_BACKGROUND_PEAK
        if self._background_level < MIN_BACKGROUND_PEAK:
            self._background_level = MIN_BACKGROUND_PEAK

    def _calibrate(self, peak: float, level: float) -> None:
        """Startup calibration: median of the first frames' statistics."""
        self._calibration_frames += 1
        self._calibration_peaks.append(peak)
        self._calibration_levels.append(level)
        if self._calibration_frames >= self._calibration_target:
            self._background_peak = max(
                MIN_BACKGROUND_PEAK, _median(self._calibration_peaks)
            )
            self._background_level = max(
                MIN_BACKGROUND_PEAK, _median(self._calibration_levels)
            )
            # The median is robust: a single clap during startup does not
            # inflate the floor the way a mean would.
            self._log_debug(
                f"Calibration complete: ambient level {self._background_level:.1f} "
                f"(peak {self._background_peak:.1f}, threshold "
                f"{self.current_detection_threshold():.1f})."
            )

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def process_frame(
        self, raw_bytes: bytes, frame_timestamp: Optional[float] = None
    ) -> Optional[ActivationEvent]:
        """
        Process a single PCM frame through the DSP chain and evaluate the
        transient amplitude, concentration, width and duration tests.
        Returns ActivationEvent on a detected double-clap sequence.
        """
        current_time = self._get_current_time(frame_timestamp)
        analysis = self.analyze_frame(raw_bytes)
        peak = analysis.peak

        # Rapid initial background calibration during startup
        if self._calibration_frames < self._calibration_target:
            self._calibrate(peak, analysis.level)
            return None

        # Keep the background estimates current on every frame
        self._update_background(peak, analysis.level)

        # Check cooldown state
        if self._state == "COOLDOWN":
            if current_time >= self._cooldown_until:
                self._state = "IDLE"
                self._log_debug("Cooldown period complete. State returned to IDLE.")
            else:
                return None

        # Expire a stale first-clap anchor.  This must not run while a burst is
        # in progress, otherwise a legitimate second clap that *ends* just
        # after the window would be discarded.
        if self._state == "WAITING_FOR_SECOND" and not self._in_transient:
            elapsed_ms = (current_time - self._first_clap_time) * 1000.0
            if elapsed_ms > self.max_clap_interval_ms:
                self._log_debug(
                    f"Waiting for 2nd clap timed out ({elapsed_ms:.0f}ms > "
                    f"{self.max_clap_interval_ms:.0f}ms). Resetting to IDLE."
                )
                self._state = "IDLE"

        # A transient must meet ALL of:
        # 1. Amplitude: it stands clearly above the tracked background peak
        # 2. Concentration: only a few analysis windows are loud, which
        #    rejects speech, music, fan noise and other continuous sound
        # 3. Width: it exceeds the room's peak level for more than one
        #    sample, which rejects single-sample glitches
        detection_threshold = self.current_detection_threshold()
        loud_fraction = self._loud_window_fraction(analysis.window_levels)
        is_transient = (
            peak >= detection_threshold
            and loud_fraction > 0.0
            and loud_fraction <= self._max_loud_window_fraction
            and analysis.loud_samples >= MIN_BURST_SAMPLES
        )

        event_to_emit: Optional[ActivationEvent] = None

        if is_transient:
            if not self._in_transient:
                # Start of a new energy burst
                self._in_transient = True
                self._transient_start_time = current_time
                self._transient_peak = peak
                self._transient_level = analysis.level
                self._transient_threshold = detection_threshold
                self._transient_is_invalid = False
            else:
                # Continuing an existing burst
                burst_duration_ms = (current_time - self._transient_start_time) * 1000.0
                if peak > self._transient_peak:
                    self._transient_peak = peak
                if analysis.level > self._transient_level:
                    self._transient_level = analysis.level

                # If energy stays high for too long, reject as sustained noise/speech/typing
                if burst_duration_ms > self.max_transient_duration_ms:
                    if not self._transient_is_invalid:
                        self._transient_is_invalid = True
                        self._log_debug(
                            f"Sound rejected: sustained energy for {burst_duration_ms:.0f}ms > "
                            f"{self.max_transient_duration_ms:.0f}ms (speech or noise)."
                        )
        else:
            # Energy has fallen below threshold
            if self._in_transient:
                burst_duration_ms = (current_time - self._transient_start_time) * 1000.0
                was_valid_clap = (
                    not self._transient_is_invalid
                    and burst_duration_ms <= self.max_transient_duration_ms
                    and self._transient_peak >= self._transient_threshold
                )

                self._in_transient = False

                if was_valid_clap:
                    event_to_emit = self._handle_valid_clap(
                        self._transient_start_time, self._transient_peak, self._transient_level
                    )

        if event_to_emit:
            self._emit_activation(event_to_emit)
            return event_to_emit

        return None

    def _handle_valid_clap(self, clap_time: float, peak: float, level: float) -> Optional[ActivationEvent]:
        """State transition handler when a short, sharp transient clap is confirmed."""
        if self._state == "WAITING_FOR_SECOND":
            delta_ms = (clap_time - self._first_clap_time) * 1000.0

            if delta_ms < self.min_clap_interval_ms:
                # Echo / rebound of the first clap.  The transient is discarded
                # completely: it neither becomes a new anchor nor is allowed to
                # pair with a later sound, so only a genuine second clap inside
                # the tempo window can complete the pair.
                self._log_debug(
                    f"Transient ignored: too fast ({delta_ms:.1f}ms < "
                    f"{self.min_clap_interval_ms:.1f}ms, echo/rebound)."
                )
                return None

            if delta_ms <= self.max_clap_interval_ms:
                # Valid double-clap!
                self._state = "COOLDOWN"
                self._cooldown_until = clap_time + (self.cooldown_ms / 1000.0)

                confidence = self._compute_confidence(peak, delta_ms)
                self._log_debug(
                    f"👏 Clap 2 registered! Interval: {delta_ms:.1f}ms. "
                    f">>> DOUBLE-CLAP ACTIVATION CONFIRMED!"
                )

                event = ActivationEvent(
                    type="activation.detected",
                    method="double_clap",
                    metadata={
                        "interval_ms": round(delta_ms, 1),
                        # Level statistics (RMS scale) - the historic field names
                        "first_clap_rms": round(self._first_clap_level, 1),
                        "second_clap_rms": round(level, 1),
                        "noise_floor": round(self._background_level, 1),
                        # Amplitude statistics (peak scale) - the values the
                        # detection itself is based on
                        "first_clap_peak": round(self._first_clap_peak, 1),
                        "second_clap_peak": round(peak, 1),
                        "confidence": confidence,
                    },
                )
                return event

            # Outside the window - the anchor has expired, so this transient
            # becomes the new first clap.
            self._log_debug(
                f"Interval {delta_ms:.1f}ms exceeded window "
                f"({self.max_clap_interval_ms:.1f}ms). Treating as new Clap 1."
            )
            self._state = "IDLE"

        # Register the transient as the first clap of a new pair
        self._state = "WAITING_FOR_SECOND"
        self._first_clap_time = clap_time
        self._first_clap_peak = peak
        self._first_clap_level = level
        self._log_debug(
            f"👏 Clap 1 registered! Peak: {peak:.1f} "
            f"(Threshold: {self.current_detection_threshold():.1f}). Waiting for 2nd clap..."
        )
        return None

    def _compute_confidence(self, peak: float, interval_ms: float) -> float:
        """
        Bounded confidence for a confirmed double-clap.

        Two independent pieces of evidence are combined:
        - energy: how far the second clap stands above the detection threshold
        - tempo:  how centred the inter-clap interval is inside the allowed
          window (an interval hard against the limit is less convincing)

        Unlike a plain "clap level / noise floor" ratio this cannot saturate on
        every event, so the reported value actually carries information.
        """
        threshold = self.current_detection_threshold()
        snr = (peak / threshold) if threshold > 0.0 else 1.0
        energy = max(0.0, min(1.0, (snr - 1.0) / (CONFIDENCE_ENERGY_FULL_MARGIN - 1.0)))

        centre = (self.min_clap_interval_ms + self.max_clap_interval_ms) / 2.0
        half_window = max(1e-6, (self.max_clap_interval_ms - self.min_clap_interval_ms) / 2.0)
        # The tempo score falls off towards the edges of the allowed window but
        # never drops below 0.5 - an interval at the limit is still a plausible
        # double-clap, just a less convincing one.
        tempo = max(0.0, min(1.0, 1.0 - 0.5 * abs(interval_ms - centre) / half_window))

        return round(CONFIDENCE_MAX * (0.5 * energy + 0.5 * tempo), 2)
