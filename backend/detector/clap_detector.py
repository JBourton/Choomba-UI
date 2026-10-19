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

On top of that, the *structure* of a double clap is checked: the two strikes
have to be of comparable level, they have to fall inside the tempo window,
and a third comparable burst following the pair cancels it - a double clap
is exactly two strikes, a mechanical keyboard produces a whole train of them.

The ambient level is tracked as the median of the last 32 frames, using the
same statistic that is tested (the frame peak for the amplitude test, the
short-window RMS for the concentration test), so every comparison stays in
one consistent scale.  The estimator is updated on every frame - never
frozen while loud frames are classified as transients - and deliberately has
no absolute ceiling, so a loud room raises the threshold instead of pinning
it.
"""

import math
import struct
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, Tuple, List, Deque

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

# ---------------------------------------------------------------------------
# The low band: what makes a clap a *slap*
# ---------------------------------------------------------------------------
#: Centre of the low band that carries the thud of two hands meeting
#: (60-300 Hz).  A hand clap is a collision: besides the broadband "crack"
#: it produces a strong low frequency pressure wave.  A mechanical key click
#: and a speech plosive are almost entirely high frequency.  The detector's
#: 350 Hz high-pass throws that information away, so it is measured in a
#: parallel low-pass path.
LOW_BAND_HP_HZ = 60.0
LOW_BAND_LP_HZ = 300.0

#: The "crack" band (1.2-12 kHz) of the impact itself.  A clap has a low
#: frequency thud *and* a broadband crack; a voiced sound only has the low
#: band, a key click only the crack.  Requiring both is what tells a clap
#: apart from speech.
CRACK_BAND_HP_HZ = 1200.0
CRACK_BAND_LP_HZ = 12000.0

#: Minimum share of an event's amplitude that has to come from the low band
#: for the event to be considered a slap.  Measured on synthetic events:
#: a hand clap scores 0.72-0.75, a speech plosive 0.06-0.19 and a keyboard
#: click 0.05-0.12.  Set CHOOMBA_MIN_LOW_BAND_SHARE=0 to disable the test.
MIN_LOW_BAND_SHARE = 0.35

#: Minimum share of an event's amplitude that has to come from the crack
#: band.  Measured: a hand clap 0.26-0.32, a voiced sound 0.08-0.14.
#: Set CHOOMBA_MIN_CRACK_BAND_SHARE=0 to disable the test.
MIN_CRACK_BAND_SHARE = 0.18

# ---------------------------------------------------------------------------
# Structure of a double clap
# ---------------------------------------------------------------------------
# A double clap is not "two loud sounds", it is *two comparable strikes
# followed by silence*.  These constants express that structure, so that a
# single clap plus some unrelated background noise, or a train of mechanical
# keyboard clicks, cannot be mistaken for one.

#: The two strikes of a double clap come from two similar movements, so their
#: amplitudes have to stay within a factor of each other.  A single loud clap
#: followed by a much quieter noise therefore never forms a pair.
PAIR_RATIO_MIN = 0.4
PAIR_RATIO_MAX = 2.5

#: A third burst of comparable level right after a matched pair means the
#: pair was part of a *train* of sounds (typing, a rattling object, a
#: metronome) rather than a double clap.  Such a pair is cancelled.  The band
#: is wider than the pair band because key presses vary a lot in level.
VETO_RATIO_MIN = 0.25
VETO_RATIO_MAX = 4.0

#: A third burst must also stand clearly above the ambient peak level, so
#: that the ordinary fluctuations of the room do not cancel a real double
#: clap.
VETO_AMBIENT_MARGIN = 1.5

#: How long a matched pair is held before it is confirmed as a double clap.
#: This is the window in which a third burst can still cancel the pair.  It
#: is tied to the upper tempo bound: a train of sounds that continues at
#: double-clap tempo is a train, not a double clap.  The cost is that the
#: activation is reported this long after the second strike.
PAIR_CONFIRMATION_MS = 450.0

#: A double clap is a *deliberate* pair of strikes, so the first strike may
#: not be preceded by a comparable transient within the tempo window.  This
#: is what keeps the second and third key press of a typing burst from ever
#: forming a pair.  The window is tied to the upper tempo bound, so any two
#: comparable strikes that are close enough to be a pair are treated as such
#: instead of one of them becoming the anchor of a new pair.
PREDECESSOR_GUARD_MS = 450.0

#: Number of frames the background estimators look at.  A *median* over this
#: window is used instead of an average, so a burst of impulsive events (key
#: presses, a clapping hand) cannot inflate the ambient estimate and raise
#: the threshold underneath itself.  32 frames are about 0.37 s.
BACKGROUND_WINDOW_FRAMES = 32

#: Upper bound of the reported confidence.
CONFIDENCE_MAX = 0.99

#: The energy component of the confidence saturates once a clap reaches this
#: multiple of the detection threshold.
CONFIDENCE_ENERGY_FULL_MARGIN = 2.0

#: Lower bound of the tracked background peak (16-bit linear units).  This is
#: the only floor the noise estimator has - deliberately *not* an upper one.
MIN_BACKGROUND_PEAK = 1.0

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


def _butterworth_coefficients(fc: float, fs: int, highpass: bool = False):
    """
    2nd order Butterworth biquad coefficients (RBJ cookbook).

    The quality factor of a Butterworth response is 1/sqrt(2), and the
    cookbook defines alpha = sin(w0) / (2*Q).  Getting that wrong makes the
    filter under-damped and puts a +3 dB peak at the cut-off frequency.
    """
    q = 1.0 / math.sqrt(2.0)
    w0 = 2.0 * math.pi * fc / fs
    alpha = math.sin(w0) / (2.0 * q)
    cosw = math.cos(w0)
    if highpass:
        b0, b1, b2 = (1 + cosw) / 2, -(1 + cosw), (1 + cosw) / 2
    else:
        b0, b1, b2 = (1 - cosw) / 2, 1 - cosw, (1 - cosw) / 2
    a0, a1, a2 = 1 + alpha, -2 * cosw, 1 - alpha
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def _biquad(samples: List[float], coefficients) -> List[float]:
    """Apply a biquad filter to a signal."""
    b0, b1, b2, a1, a2 = coefficients
    x1 = x2 = y1 = y2 = 0.0
    out = []
    for v in samples:
        y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, v
        y2, y1 = y1, y
        out.append(y)
    return out


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

    total: float
    """RMS of the whole DC-removed frame (low band included)."""

    low_band_share: float
    """
    Share of the frame's amplitude that comes from the low band (60-300 Hz).

    A hand clap is a *slap*: the collision of two hands produces a strong
    low frequency pressure wave.  A key click or a speech plosive is almost
    entirely high frequency and scores far lower.  The detector's high-pass
    discards that information, so it is measured in a parallel path.
    """

    crack_band_share: float
    """
    Share of the frame's amplitude that comes from the crack band (1.2-12 kHz).

    A clap has a broadband crack as well as a low frequency thud; a voiced
    sound has the thud but hardly any crack.
    """

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
        min_clap_interval_ms: float = 150.0,
        max_clap_interval_ms: float = 450.0,
        max_transient_duration_ms: float = 60.0,
        cooldown_ms: float = 1500.0,
        pair_confirmation_ms: float = PAIR_CONFIRMATION_MS,
        min_low_band_share: float = MIN_LOW_BAND_SHARE,
        min_crack_band_share: float = MIN_CRACK_BAND_SHARE,
        min_peak_threshold: float = 6000.0,
        ratio_sensitive: float = 1.5,
        ratio_strict: float = 2.8,
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
        self.pair_confirmation_ms = pair_confirmation_ms
        self.min_low_band_share = min_low_band_share
        self.min_crack_band_share = min_crack_band_share
        self.min_peak_threshold = min_peak_threshold
        self.ratio_sensitive = ratio_sensitive
        self.ratio_strict = ratio_strict
        self._min_peak_threshold_base = min_peak_threshold
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
        self._peak_history: Deque[float] = deque(maxlen=BACKGROUND_WINDOW_FRAMES)
        self._level_history: Deque[float] = deque(maxlen=BACKGROUND_WINDOW_FRAMES)
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
        self._transient_total = 0.0
        self._transient_low_band_share = 0.0
        self._transient_crack_band_share = 0.0
        self._transient_is_invalid = False
        # (time, peak) of the recent bursts - used to recognise that a
        # candidate strike is just another link in a chain of sounds.
        self._recent_bursts: List[Tuple[float, float]] = []

        # Clap state machine:
        #   'IDLE' -> 'WAITING_FOR_SECOND' -> 'PENDING_CONFIRM' -> 'COOLDOWN'
        # A matched pair is held in 'PENDING_CONFIRM' for a short while so a
        # third burst of comparable level can cancel it: a double clap is
        # exactly two strikes, a mechanical keyboard produces a whole train.
        self._state = "IDLE"
        self._first_clap_time = 0.0
        self._first_clap_peak = 0.0
        self._first_clap_level = 0.0
        self._cooldown_until = 0.0

        # Pair awaiting confirmation
        self._pending_first_peak = 0.0
        self._pending_first_level = 0.0
        self._pending_second_time = 0.0
        self._pending_second_peak = 0.0
        self._pending_second_level = 0.0
        self._pending_interval_ms = 0.0
        self._pending_threshold = 0.0
        self._pending_veto_armed = False

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

        # Parallel low band path (60-300 Hz) used to tell a slap from a click
        self._low_band_coefficients = (
            _butterworth_coefficients(LOW_BAND_LP_HZ, sample_rate, highpass=False),
            _butterworth_coefficients(LOW_BAND_HP_HZ, sample_rate, highpass=True),
        )
        # Parallel crack band (1.2-12 kHz) used to tell a clap from a voice
        self._crack_band_coefficients = (
            _butterworth_coefficients(CRACK_BAND_LP_HZ, sample_rate, highpass=False),
            _butterworth_coefficients(CRACK_BAND_HP_HZ, sample_rate, highpass=True),
        )

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
        transient must stand, between ``ratio_strict`` and
        ``ratio_sensitive``.  It deliberately does *not* relax the
        concentration, low band or burst width tests: continuous background
        sound, key presses and speech are rejected on shape and spectrum, not
        on level, so lowering the sensitivity can never turn a fan or a
        passing car into a clap.
        """
        s = max(0.1, min(1.0, float(sensitivity)))
        self._sensitivity = s
        span = max(0.0, self.ratio_strict - self.ratio_sensitive)
        self._threshold_ratio = self.ratio_strict - (s * span)
        # The absolute floor is the "how loud must a clap be in absolute terms"
        # setting and is used as given.  In a quiet room it is the only thing
        # that can separate a clap from speech or key presses, because a
        # relative threshold has nothing to compare against.
        self._min_peak_threshold = self._min_peak_threshold_base
        # Maximum fraction of analysis windows allowed to be loud in one frame.
        self._max_loud_window_fraction = MAX_LOUD_WINDOW_FRACTION

    def apply_settings(self, settings: Dict[str, Any]) -> None:
        """
        Apply a settings patch at runtime.

        Only the keys the UI is allowed to change are honoured; everything
        else is fixed at construction time.  The values are validated here so
        that a bad patch cannot break the detector.
        """
        if "clap_sensitivity" in settings:
            self.set_sensitivity(float(settings["clap_sensitivity"]))
        if "clap_min_low_band_share" in settings:
            share = float(settings["clap_min_low_band_share"])
            self.min_low_band_share = max(0.0, min(0.9, share))
        if "clap_min_crack_band_share" in settings:
            share = float(settings["clap_min_crack_band_share"])
            self.min_crack_band_share = max(0.0, min(0.9, share))
        if "clap_min_peak_threshold" in settings:
            floor = float(settings["clap_min_peak_threshold"])
            self._min_peak_threshold_base = max(0.0, min(32000.0, floor))
            self.set_sensitivity(self._sensitivity)
        if "clap_pair_confirmation_ms" in settings:
            window = float(settings["clap_pair_confirmation_ms"])
            self.pair_confirmation_ms = max(100.0, min(2000.0, window))
        if "clap_max_interval_ms" in settings:
            interval = float(settings["clap_max_interval_ms"])
            self.max_clap_interval_ms = max(
                self.min_clap_interval_ms + 50.0, min(2000.0, interval)
            )
        if "clap_min_interval_ms" in settings:
            interval = float(settings["clap_min_interval_ms"])
            self.min_clap_interval_ms = max(50.0, min(interval, self.max_clap_interval_ms - 50.0))

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

    def current_detection_ratio(self) -> float:
        """The amplitude margin the detector is currently using."""
        return self._threshold_ratio

    def current_min_peak_threshold(self) -> float:
        """The absolute floor a transient has to clear."""
        return self._min_peak_threshold

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
        self._pending_second_time = 0.0
        self._pending_second_peak = 0.0
        self._pending_second_level = 0.0
        self._pending_interval_ms = 0.0
        self._pending_threshold = 0.0
        self._pending_veto_armed = False
        self._recent_bursts.clear()
        self._prev_x = 0.0
        self._prev_y = 0.0

    def start(self) -> None:
        self.reset_state()
        self._calibration_frames = 0
        self._calibration_peaks = []
        self._calibration_levels = []
        self._peak_history.clear()
        self._level_history.clear()
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
            return FrameAnalysis(0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, (), 0)
        num_samples = len(raw_bytes) // 2
        if num_samples == 0:
            return FrameAnalysis(0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, (), 0)

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
        zero_centred = [s - dc for s in samples]

        # 2. 350Hz single-pole IIR high-pass filter
        filtered = []
        py, px = self._prev_y, self._prev_x
        alpha = self._hp_alpha
        for s in zero_centred:
            x = s
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

        # 4. Band shares: how much of this frame is the low frequency "thud"
        #    of a slap and how much is the broadband "crack" of the impact.
        #    A clap has both; a voice has the thud but no crack; a key click
        #    has the crack but no thud.
        total_rms = math.sqrt(sum(v * v for v in zero_centred) / num_samples)
        low_rms = math.sqrt(
            sum(v * v for v in self._low_band(zero_centred)) / num_samples
        )
        crack_rms = math.sqrt(
            sum(v * v for v in self._crack_band(zero_centred)) / num_samples
        )
        low_band_share = low_rms / max(total_rms, 1e-9)
        crack_band_share = crack_rms / max(total_rms, 1e-9)

        # 5. How many samples are genuinely above the room's usual peak?  A
        #    single-sample glitch produces one, a real clap produces several.
        background = self._background_peak
        loud_samples = 0
        if background > 0.0:
            for v in filtered:
                if abs(v) >= background:
                    loud_samples += 1

        return FrameAnalysis(
            rms, peak, crest, level, total_rms, low_band_share, crack_band_share,
            windows, loud_samples
        )

    def _low_band(self, zero_centred: List[float]) -> List[float]:
        """The 60-300 Hz band of the frame (the thud of a slap)."""
        if self._low_band_coefficients is None:
            return zero_centred
        return _biquad(_biquad(zero_centred, self._low_band_coefficients[0]),
                       self._low_band_coefficients[1])

    def _crack_band(self, zero_centred: List[float]) -> List[float]:
        """The 1.2-12 kHz band of the frame (the crack of the impact)."""
        if self._crack_band_coefficients is None:
            return zero_centred
        return _biquad(_biquad(zero_centred, self._crack_band_coefficients[0]),
                       self._crack_band_coefficients[1])

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
        Track the ambient peak level and loudness.

        Both estimators are the *median* of the last
        ``BACKGROUND_WINDOW_FRAMES`` frames.  A median is used on purpose: an
        average would be dragged upwards by the impulsive events the detector
        is supposed to reject (a burst of key presses lifts the estimate and
        therefore lifts the threshold, so the very next key press falls below
        it again).  A median ignores them, and it still follows a genuine
        change of the room level within a fraction of a second.

        The estimators are updated on *every* frame - including frames that
        were classified as transients - so a burst of loud sound can never
        freeze them the way the previous implementation did.  There is
        deliberately no upper bound: the threshold has to keep rising in a
        loud room instead of being pinned at a fixed ceiling.
        """
        self._peak_history.append(peak)
        self._level_history.append(level)
        self._background_peak = max(MIN_BACKGROUND_PEAK, _median(self._peak_history))
        self._background_level = max(MIN_BACKGROUND_PEAK, _median(self._level_history))

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
        if self._state == "PENDING_CONFIRM":
            # While a matched pair is being confirmed the amplitude bar is
            # frozen at the value the pair had to clear.  Otherwise a rising
            # background (a burst of key presses lifts the ambient estimate)
            # would hide the very third burst that has to cancel the pair.
            detection_threshold = self._pending_threshold
        loud_fraction = self._loud_window_fraction(analysis.window_levels)
        is_transient = (
            peak >= detection_threshold
            and loud_fraction > 0.0
            and loud_fraction <= self._max_loud_window_fraction
            and analysis.loud_samples >= MIN_BURST_SAMPLES
        )

        event_to_emit: Optional[ActivationEvent] = None

        # The band shares are taken from the frame that carries most of the
        # energy of the burst.  A clap that straddles a frame boundary puts
        # its crack in one frame and its thud in the next, and both parts
        # describe the impact.
        if self._in_transient and analysis.total > self._transient_total:
            self._transient_total = analysis.total
            self._transient_low_band_share = analysis.low_band_share
            self._transient_crack_band_share = analysis.crack_band_share

        if self._state == "PENDING_CONFIRM" and self._check_for_third_burst(peak):
            # A third burst right after the pair means the pair was part of a
            # train of sounds (typing, a rattling object), not a double clap.
            self._log_debug(
                "Double-clap cancelled: a third burst of comparable level followed. "
                "This was a train of sounds (typing, rattling), not a double-clap."
            )
            self._state = "IDLE"

        if is_transient:
            if not self._in_transient:
                # Start of a new energy burst
                if self._state == "PENDING_CONFIRM":
                    # A third burst right after the pair means the pair was
                    # part of a train of sounds (typing, a rattling object),
                    # not a double clap.
                    if self._is_similar_level(peak, self._pending_second_peak,
                                              VETO_RATIO_MIN, VETO_RATIO_MAX):
                        self._log_debug(
                            "Double-clap cancelled: a third burst of comparable level "
                            "followed. This was a train of sounds (typing, rattling), "
                            "not a double-clap."
                        )
                        self._state = "IDLE"
                    else:
                        self._log_debug(
                            "Burst ignored while the double-clap was being confirmed."
                        )
                self._in_transient = True
                self._transient_start_time = current_time
                self._transient_peak = peak
                self._transient_level = analysis.level
                self._transient_threshold = detection_threshold
                self._transient_total = analysis.total
                self._transient_low_band_share = analysis.low_band_share
                self._transient_crack_band_share = analysis.crack_band_share
                self._transient_is_invalid = False
                self._recent_bursts.append((current_time, peak))
                if len(self._recent_bursts) > 8:
                    self._recent_bursts.pop(0)
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
                looks_like_a_clap = (
                    self._transient_low_band_share >= self.min_low_band_share
                    and self._transient_crack_band_share >= self.min_crack_band_share
                )
                was_valid_clap = (
                    not self._transient_is_invalid
                    and burst_duration_ms <= self.max_transient_duration_ms
                    and self._transient_peak >= self._transient_threshold
                    and looks_like_a_clap
                )

                self._in_transient = False

                if was_valid_clap:
                    event_to_emit = self._handle_valid_clap(
                        self._transient_start_time, self._transient_peak, self._transient_level
                    )
                elif (self._transient_peak >= self._transient_threshold
                        and not looks_like_a_clap):
                    self._log_debug(
                        f"Sound rejected: not a clap (low band "
                        f"{self._transient_low_band_share:.2f}, crack band "
                        f"{self._transient_crack_band_share:.2f}) - a click, a key press "
                        f"or a voice rather than two hands meeting."
                    )

        if event_to_emit:
            self._emit_activation(event_to_emit)
            return event_to_emit

        # A matched pair is only confirmed once no third burst has cancelled it
        # within the confirmation window.
        if (self._state == "PENDING_CONFIRM"
                and (current_time - self._pending_second_time) * 1000.0
                >= self.pair_confirmation_ms):
            event_to_emit = self._finalize_pending_clap()
            if event_to_emit:
                self._emit_activation(event_to_emit)
                return event_to_emit

        return None

    @staticmethod
    def _is_similar_level(peak: float, reference: float,
                          low: float, high: float) -> bool:
        """True when two amplitudes are within a factor of each other."""
        if reference <= 0.0:
            return False
        ratio = peak / reference
        return low <= ratio <= high

    def _handle_valid_clap(self, clap_time: float, peak: float, level: float) -> Optional[ActivationEvent]:
        """State transition handler when a short, sharp transient clap is confirmed."""
        if self._state == "PENDING_CONFIRM":
            # A burst that was started while the pair was pending and did not
            # match it is ignored - the pair keeps its chance to be confirmed.
            self._log_debug("Burst ignored while the double-clap was being confirmed.")
            return None

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
                # The two strikes of a double clap have a comparable amplitude.
                # A single loud clap followed by some unrelated (quieter) noise
                # must not form a pair.
                if not self._is_similar_level(peak, self._first_clap_peak,
                                              PAIR_RATIO_MIN, PAIR_RATIO_MAX):
                    ratio = peak / max(self._first_clap_peak, 1e-6)
                    if peak > self._first_clap_peak:
                        # A louder event is more likely to be the real strike:
                        # it becomes the new anchor.
                        self._first_clap_time = clap_time
                        self._first_clap_peak = peak
                        self._first_clap_level = level
                        self._log_debug(
                            f"Transient ignored: level {ratio:.2f}x does not match the "
                            f"first clap - the louder transient becomes the new anchor."
                        )
                    else:
                        self._log_debug(
                            f"Transient ignored: level {ratio:.2f}x does not match the "
                            f"first clap (not a matching strike)."
                        )
                    return None

                # Matched pair - hold it for a moment so that a third burst of
                # comparable level can still cancel it.
                self._state = "PENDING_CONFIRM"
                self._pending_first_peak = self._first_clap_peak
                self._pending_first_level = self._first_clap_level
                self._pending_second_time = clap_time
                self._pending_second_peak = peak
                self._pending_second_level = level
                self._pending_interval_ms = delta_ms
                self._pending_threshold = self._transient_threshold
                self._pending_veto_armed = False
                self._cooldown_until = clap_time + (self.cooldown_ms / 1000.0)
                self._log_debug(
                    f"👏 Clap 2 matched! Interval: {delta_ms:.1f}ms. "
                    f"Confirming that no third burst follows..."
                )
                return None

            # Outside the window - the anchor has expired, so this transient
            # becomes the new first clap.
            self._log_debug(
                f"Interval {delta_ms:.1f}ms exceeded window "
                f"({self.max_clap_interval_ms:.1f}ms). Treating as new Clap 1."
            )
            self._state = "IDLE"

        # Register the transient as the first clap of a new pair - but only if
        # it is not just the next link in a chain of comparable sounds.  A
        # strike that follows another comparable strike is part of a train
        # (typing, a rattling object) and must not anchor a pair.
        if self._has_recent_similar_burst(clap_time, peak):
            self._log_debug(
                "Transient ignored: it follows another comparable burst, so it is "
                "part of a train of sounds and not the start of a double-clap."
            )
            return None

        self._state = "WAITING_FOR_SECOND"
        self._first_clap_time = clap_time
        self._first_clap_peak = peak
        self._first_clap_level = level
        self._log_debug(
            f"👏 Clap 1 registered! Peak: {peak:.1f} "
            f"(Threshold: {self.current_detection_threshold():.1f}, "
            f"low band {self._transient_low_band_share:.2f}). Waiting for 2nd clap..."
        )
        return None

    def _check_for_third_burst(self, peak: float) -> bool:
        """
        Look for a third burst while a matched pair is being confirmed.

        This deliberately uses its own, much simpler detector than the clap
        test: it only asks "did a new burst of sound arrive?", not "is this
        burst shaped like a clap?".  A key press is very short and would
        sometimes fail the shape tests, and a veto that only fires
        occasionally would not stop the typing.

        The detector arms itself on the first quiet frame after the pair, so
        the decay tail of the pair's own second strike cannot trigger it.
        """
        bar = max(self._pending_second_peak * VETO_RATIO_MIN,
                  self._background_peak * VETO_AMBIENT_MARGIN)
        if peak < bar:
            self._pending_veto_armed = True
            return False
        if not self._pending_veto_armed:
            return False
        if peak > self._pending_second_peak * VETO_RATIO_MAX:
            # Far too loud to belong to the same train - a different event.
            return False
        return True

    def _has_recent_similar_burst(self, clap_time: float, peak: float) -> bool:
        """
        True when a comparable burst happened shortly before this one.

        Used to recognise a chain of sounds: a key press that follows another
        key press is not the beginning of a double clap.  The window is the
        upper tempo bound, so anything close enough to be part of a pair is
        treated as such.
        """
        guard_ms = min(PREDECESSOR_GUARD_MS, self.max_clap_interval_ms)
        for index in range(len(self._recent_bursts) - 1, -1, -1):
            time_ms, burst_peak = self._recent_bursts[index]
            gap_ms = (clap_time - time_ms) * 1000.0
            if gap_ms > guard_ms:
                break
            if gap_ms <= 0.0:
                continue
            if self._is_similar_level(peak, burst_peak, VETO_RATIO_MIN, VETO_RATIO_MAX):
                return True
        return False

    def _finalize_pending_clap(self) -> Optional[ActivationEvent]:
        """Confirm a held double-clap pair and build the activation event."""
        if self._state != "PENDING_CONFIRM":
            return None
        self._state = "COOLDOWN"
        confidence = self._compute_confidence(
            self._pending_second_peak, self._pending_interval_ms,
            self._pending_threshold,
        )
        self._log_debug(
            f">>> DOUBLE-CLAP ACTIVATION CONFIRMED! "
            f"Interval: {self._pending_interval_ms:.1f}ms."
        )
        return ActivationEvent(
            type="activation.detected",
            method="double_clap",
            metadata={
                "interval_ms": round(self._pending_interval_ms, 1),
                # Level statistics (RMS scale) - the historic field names
                "first_clap_rms": round(self._pending_first_level, 1),
                "second_clap_rms": round(self._pending_second_level, 1),
                "noise_floor": round(self._background_level, 1),
                # Amplitude statistics (peak scale) - the values the
                # detection itself is based on
                "first_clap_peak": round(self._pending_first_peak, 1),
                "second_clap_peak": round(self._pending_second_peak, 1),
                "confidence": confidence,
            },
        )

    def _compute_confidence(self, peak: float, interval_ms: float,
                            threshold: float) -> float:
        """
        Bounded confidence for a confirmed double-clap.

        Two independent pieces of evidence are combined:
        - energy: how far the second clap stands above the detection threshold
        - tempo:  how centred the inter-clap interval is inside the allowed
          window (an interval hard against the limit is less convincing)

        The threshold is the one the pair had to clear, not the current one:
        the background estimate may have moved on while the pair was waiting
        for its confirmation.

        Unlike a plain "clap level / noise floor" ratio this cannot saturate on
        every event, so the reported value actually carries information.
        """
        snr = (peak / threshold) if threshold > 0.0 else 1.0
        energy = max(0.0, min(1.0, (snr - 1.0) / (CONFIDENCE_ENERGY_FULL_MARGIN - 1.0)))

        centre = (self.min_clap_interval_ms + self.max_clap_interval_ms) / 2.0
        half_window = max(1e-6, (self.max_clap_interval_ms - self.min_clap_interval_ms) / 2.0)
        # The tempo score falls off towards the edges of the allowed window but
        # never drops below 0.5 - an interval at the limit is still a plausible
        # double-clap, just a less convincing one.
        tempo = max(0.0, min(1.0, 1.0 - 0.5 * abs(interval_ms - centre) / half_window))

        return round(CONFIDENCE_MAX * (0.5 * energy + 0.5 * tempo), 2)
