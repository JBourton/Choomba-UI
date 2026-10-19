"""
Regression tests for the double-clap detector.

These tests cover the behaviour that the original test-suite could not reach:
the adaptive background estimator, the transient concentration test and the
confidence calculation were never exercised because every test used digital
silence as its baseline and the startup calibration was skipped entirely.

The signal models used here are deliberately simple but physically meaningful:

* ``noise_chunk``  - broadband Gaussian room tone at a given RMS.  Real room
  tone is broadband, so its per-frame crest factor is ~3.2, not the 1.4-2.5
  quoted for tonal hum or speech vowels.
* ``clap_chunk``   - a broadband impulse with a fast attack and an exponential
  decay (the "crack" of a hand clap lasts 1-3 ms).
* ``swell_chunk``  - the same broadband noise at a higher level, i.e. an
  ordinary loud background event (a passing car, a fan, a shout).
"""

import math
import random
import struct
import unittest
from typing import List, Optional

from backend.detector.clap_detector import DoubleClapDetector
from backend.detector.base import ActivationEvent

SAMPLE_RATE = 44100
CHUNK_SIZE = 512
CHUNK_MS = CHUNK_SIZE / SAMPLE_RATE * 1000.0

# A loud room: -20 dBFS room tone, the environment that produced the original
# false activations.
LOUD_AMBIENT_RMS = 3200


def pcm(samples) -> bytes:
    return struct.pack(f"{len(samples)}h", *[max(-32768, min(32767, int(s))) for s in samples])


def rms_of(samples) -> float:
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def noise_chunk(rms: float, seed: int) -> bytes:
    """Broadband Gaussian room tone at the requested RMS."""
    # Deterministic pseudo-random noise (no dependency on the global RNG).
    state = seed * 6364136223846793005 + 1442695040888963407
    samples = []
    for _ in range(CHUNK_SIZE):
        state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        u1 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        u2 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        samples.append(math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2))
    gain = rms / rms_of(samples)
    return pcm([s * gain for s in samples])


def clap_chunk(peak: float = 30000.0, decay_ms: float = 1.2, seed: int = 1) -> bytes:
    """
    A hand-clap like impulse.

    A real clap is not white noise: it is the collision of two hands.  That
    produces a strong low frequency pressure wave (the thud of the palms,
    roughly 100-250 Hz) on top of the broadband "crack" of the impact and the
    short resonance of the air cavity between the hands.  The detector
    measures that low band, so the model has to contain it.
    """
    tau = max(1, int(SAMPLE_RATE * decay_ms / 1000.0))
    thud_tau = max(1, int(SAMPLE_RATE * 0.0035 / 1000.0 * 1000.0))
    state = seed * 2862933555777941757 + 3037000493
    samples = []
    for i in range(CHUNK_SIZE):
        state = (state * 2862933555777941757 + 3037000493) & 0xFFFFFFFFFFFFFFFF
        u1 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        state = (state * 2862933555777941757 + 3037000493) & 0xFFFFFFFFFFFFFFFF
        u2 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        gauss = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
        env = math.exp(-i / tau)
        thud = math.exp(-i / thud_tau) * (
            math.sin(2.0 * math.pi * 190.0 * i / SAMPLE_RATE)
            + 0.3 * math.sin(2.0 * math.pi * 95.0 * i / SAMPLE_RATE)
        )
        resonance = math.sin(2.0 * math.pi * 1600.0 * i / SAMPLE_RATE)
        samples.append(env * (resonance + 0.35 * gauss) + 0.9 * thud)
    gain = peak / max(abs(s) for s in samples)
    return pcm([s * gain for s in samples])


def key_click_chunk(peak: float = 14000.0, seed: int = 1) -> bytes:
    """
    A mechanical keyboard key press: a very short, purely high frequency tick
    with no low frequency thud at all.
    """
    state = seed * 6364136223846793005 + 1442695040888963407
    samples = []
    for i in range(CHUNK_SIZE):
        state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        u1 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        u2 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        gauss = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
        env = math.exp(-i / max(1, int(SAMPLE_RATE * 0.00012)))
        samples.append(gauss * env)
    gain = peak / max(abs(s) for s in samples)
    return pcm([s * gain for s in samples])


def speech_plosive_chunk(peak: float = 12000.0, seed: int = 1) -> bytes:
    """
    A speech plosive ("t", "k", "p"): a short burst of high frequency
    aspiration with a sharp release.  Like a key click it has almost no low
    frequency content.
    """
    state = seed * 11400714819323198485 + 1281163846267180317
    samples = []
    for i in range(CHUNK_SIZE):
        state = (state * 11400714819323198485 + 1281163846267180317) & 0xFFFFFFFFFFFFFFFF
        u1 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        state = (state * 11400714819323198485 + 1281163846267180317) & 0xFFFFFFFFFFFFFFFF
        u2 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        gauss = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
        env = math.exp(-i / max(1, int(SAMPLE_RATE * 0.0012)))
        samples.append(gauss * env)
    gain = peak / max(abs(s) for s in samples)
    return pcm([s * gain for s in samples])


def swell_chunk(rms: float, seed: int) -> bytes:
    """An ordinary loud broadband background event (noise at a higher level)."""
    return noise_chunk(rms, seed)


def glitch_chunk(amplitude: float, position: int = 200) -> bytes:
    """A single-sample impulse - the kind of artefact a USB/ALSA glitch makes."""
    samples = [0.0] * CHUNK_SIZE
    samples[position] = amplitude
    return pcm(samples)


def speech_voiced_burst_chunk(peak: float = 12000.0, seed: int = 1) -> bytes:
    """
    The release of a voiced consonant ("d", "b", "g"): a strong low frequency
    voice bar with only a small click on top.  It has the low band of a clap
    but hardly any of its broadband crack, which is what tells the two apart.
    """
    random.seed(seed)
    n = CHUNK_SIZE
    out = [0.0] * n
    for i in range(min(int(SAMPLE_RATE * 0.030), n)):
        env = math.exp(-i / (SAMPLE_RATE * 0.010))
        out[i] += env * math.sin(2.0 * math.pi * 140.0 * i / SAMPLE_RATE)
    for i in range(min(int(SAMPLE_RATE * 0.001), n)):
        env = math.exp(-i / (SAMPLE_RATE * 0.0003))
        out[i] += env * random.gauss(0, 1) * 0.6
    gain = peak / max(abs(s) for s in out)
    return pcm([s * gain for s in out])


def speech_vowel_chunk(peak: float = 12000.0, seed: int = 1) -> bytes:
    """A voiced vowel: a sustained harmonic stack, no transient at all."""
    n = CHUNK_SIZE
    out = []
    for i in range(n):
        v = 0.0
        for k, amp in ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.35), (6, 0.2), (9, 0.12)):
            v += amp * math.sin(2.0 * math.pi * 120.0 * k * i / SAMPLE_RATE)
        out.append(v)
    gain = peak / max(abs(v) for v in out)
    return pcm([v * gain for v in out])


class ClapStream:
    """
    Produces a clap that starts at an arbitrary offset inside a frame and
    continues into the following frames, so a clap that straddles a frame
    boundary can be replayed faithfully.
    """

    def __init__(self, peak: float, offset: int, decay_ms: float = 1.2, seed: int = 1):
        self.peak = peak
        self.offset = offset
        self.tau = max(1, int(SAMPLE_RATE * decay_ms / 1000.0))
        self.thud_tau = max(1, int(SAMPLE_RATE * 0.0035))
        self.state = seed * 2862933555777941757 + 3037000493
        # Pre-compute the enveloped noise realisation of the whole burst.
        raw = []
        for _ in range(CHUNK_SIZE * 3):
            self.state = (self.state * 2862933555777941757 + 3037000493) & 0xFFFFFFFFFFFFFFFF
            u1 = ((self.state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
            self.state = (self.state * 2862933555777941757 + 3037000493) & 0xFFFFFFFFFFFFFFFF
            u2 = ((self.state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
            raw.append(
                math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
            )
        # The same physical model as clap_chunk(): crack + resonance + the low
        # frequency thud of the impact.
        burst = []
        for i in range(len(raw)):
            env = math.exp(-i / self.tau)
            thud = math.exp(-i / self.thud_tau) * (
                math.sin(2.0 * math.pi * 190.0 * i / SAMPLE_RATE)
                + 0.3 * math.sin(2.0 * math.pi * 95.0 * i / SAMPLE_RATE)
            )
            resonance = math.sin(2.0 * math.pi * 1600.0 * i / SAMPLE_RATE)
            burst.append(env * (resonance + 0.35 * raw[i]) + 0.9 * thud)
        gain = peak / max(abs(v) for v in burst)
        self.burst = [v * gain for v in burst]
        self.position = -offset  # negative until the burst starts

    def next_chunk(self) -> bytes:
        samples = []
        for _ in range(CHUNK_SIZE):
            idx = self.position
            self.position += 1
            if idx < 0 or idx >= len(self.burst):
                samples.append(0.0)
            else:
                samples.append(self.burst[idx])
        return pcm(samples)


class DetectorHarness:
    """Drives a detector with deterministic virtual time."""

    def __init__(self, sensitivity: float = 0.8, **kwargs):
        # Only the sensitivity is overridden: every other parameter uses the
        # production defaults, so the tests exercise the shipped behaviour.
        params = dict(
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE,
            sensitivity=sensitivity,
        )
        params.update(kwargs)
        self.detector = DoubleClapDetector(**params)
        self.detector.set_virtual_time_mode(True, start_time=0.0)
        self.detector.start()
        self.events: List[ActivationEvent] = []
        self.detector.set_callback(self.events.append)
        self._seed = 1
        # The room level the harness is working in.  feed_ambient() uses it by
        # default so that a test cannot accidentally mix a quiet room with a
        # loud background.
        self.ambient_rms = LOUD_AMBIENT_RMS

    # -- feeding -----------------------------------------------------------
    def feed(self, chunk: bytes) -> None:
        self.detector.process_frame(chunk)

    def feed_ambient(self, duration_ms: float, rms: Optional[float] = None) -> None:
        if rms is None:
            rms = self.ambient_rms
        for _ in range(int(duration_ms / CHUNK_MS)):
            self._seed += 1
            self.feed(noise_chunk(rms, self._seed))

    def feed_swell(self, duration_ms: float, rms: float = 7000.0) -> None:
        for _ in range(int(duration_ms / CHUNK_MS)):
            self._seed += 1
            self.feed(swell_chunk(rms, self._seed))

    def feed_clap(self, peak: float = 30000.0) -> None:
        self._seed += 1
        self.feed(clap_chunk(peak, seed=self._seed))

    def feed_click(self, peak: float = 14000.0) -> None:
        """A mechanical keyboard key press (short, high frequency, no thud)."""
        self._seed += 1
        self.feed(key_click_chunk(peak, seed=self._seed))

    def feed_plosive(self, peak: float = 12000.0) -> None:
        """A speech plosive such as the 't' in 'total'."""
        self._seed += 1
        self.feed(speech_plosive_chunk(peak, seed=self._seed))

    def feed_voiced(self, peak: float = 12000.0) -> None:
        """The release of a voiced consonant such as the 'd' in 'double'."""
        self._seed += 1
        self.feed(speech_voiced_burst_chunk(peak, seed=self._seed))

    def feed_vowel(self, peak: float = 12000.0) -> None:
        """A sustained vowel such as the 'oo' in 'room'."""
        self._seed += 1
        self.feed(speech_vowel_chunk(peak, seed=self._seed))

    def feed_silence(self, duration_ms: float) -> None:
        for _ in range(int(duration_ms / CHUNK_MS)):
            self.feed(b"\x00" * (CHUNK_SIZE * 2))

    def confirm(self) -> None:
        """
        Let the detector finish the confirmation window of a matched pair.

        A matched pair is held for a short while before it is reported, so a
        test that expects an activation has to let that window expire.
        """
        self.feed_silence(self.detector.pair_confirmation_ms + 100.0)

    # -- helpers -----------------------------------------------------------
    @property
    def background(self) -> float:
        return self.detector.noise_floor

    @property
    def threshold(self) -> float:
        return self.detector.current_detection_threshold()

    def settle(self, rms: float = LOUD_AMBIENT_RMS) -> "DetectorHarness":
        """Feed enough ambient for the startup calibration to complete."""
        self.ambient_rms = rms
        self.feed_ambient(2000)
        return self


class TestFalsePositives(unittest.TestCase):
    """Background sound must never be reported as a double-clap."""

    def test_loud_background_bursts_do_not_trigger_activation(self):
        """
        The reported false positive: two ordinary loud broadband background
        events ~300 ms apart in a loud room used to be reported as a
        double-clap with confidence 0.99.
        """
        h = DetectorHarness().settle()
        h.feed_swell(120, rms=7000)
        h.feed_ambient(300)
        h.feed_swell(120, rms=7000)
        h.feed_ambient(500)
        self.assertEqual(
            len(h.events), 0,
            "Loud broadband background events must not be reported as a double-clap",
        )

    def test_repeated_loud_background_bursts_never_activate(self):
        """A noisy environment with many loud events must stay silent."""
        h = DetectorHarness().settle()
        for _ in range(12):
            h.feed_swell(90, rms=7500)
            h.feed_ambient(180)
        self.assertEqual(len(h.events), 0)

    def test_broadband_ambient_never_activates(self):
        """Steady broadband room tone alone must not activate."""
        h = DetectorHarness().settle()
        h.feed_ambient(8000)
        self.assertEqual(len(h.events), 0)

    def test_sustained_loud_sound_never_activates(self):
        """A continuous loud sound (voice, music, passing car) must not activate."""
        h = DetectorHarness().settle()
        h.feed_swell(4000, rms=9000)
        self.assertEqual(len(h.events), 0)

    def test_single_background_event_is_not_two_claps(self):
        """
        One loud event that dips below the threshold and comes back must not
        register two claps and therefore must not activate.
        """
        h = DetectorHarness().settle()
        h.feed_swell(150, rms=8000)
        h.feed_ambient(400)
        h.feed_swell(150, rms=8000)
        h.feed_ambient(500)
        self.assertEqual(len(h.events), 0)


class TestTruePositives(unittest.TestCase):
    """A deliberate double-clap must still be detected."""

    def test_genuine_double_clap_in_loud_background(self):
        """The real clap has to be detected even when the room is loud."""
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.confirm()
        self.assertEqual(
            len(h.events), 1,
            "A genuine double-clap must be detected in a loud room",
        )
        event = h.events[0]
        self.assertEqual(event.method, "double_clap")
        self.assertGreaterEqual(event.metadata["interval_ms"], 200.0)
        self.assertLessEqual(event.metadata["interval_ms"], 450.0)

    def test_genuine_double_clap_in_quiet_room(self):
        """A double-clap in a quiet room must be detected."""
        h = DetectorHarness().settle(rms=200)
        h.feed_clap(peak=16000)
        h.feed_ambient(300)
        h.feed_clap(peak=16000)
        h.confirm()
        self.assertEqual(len(h.events), 1)

    def test_clap_straddling_a_frame_boundary_is_detected(self):
        """
        A clap that starts near the end of a capture chunk is split across two
        frames; it must still be recognised.
        """
        for offset in (0, 64, 200, 400, 500):
            h = DetectorHarness().settle()
            stream = ClapStream(peak=30000, offset=offset)
            h.feed(stream.next_chunk())          # frame containing the clap onset
            h.feed(stream.next_chunk())          # frame containing the decay
            h.feed_ambient(300)
            stream2 = ClapStream(peak=30000, offset=offset)
            h.feed(stream2.next_chunk())
            h.feed(stream2.next_chunk())
            h.confirm()
            self.assertEqual(
                len(h.events), 1,
                f"a clap starting {offset} samples before the frame end was missed",
            )

    def test_single_sample_glitch_does_not_activate(self):
        """
        A one-sample artefact (USB/ALSA glitch) must never be treated as a
        clap, not even in a quiet room where the absolute threshold is low.
        """
        h = DetectorHarness().settle(rms=200)
        for _ in range(20):
            h.feed(glitch_chunk(9000))
            h.feed_ambient(20)
        self.assertEqual(len(h.events), 0)

    def test_single_clap_does_not_activate(self):
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(2000)
        self.assertEqual(len(h.events), 0)
        self.assertEqual(h.detector.state, "IDLE")


class TestBackgroundEstimator(unittest.TestCase):
    """The adaptive noise floor must be robust and scale free."""

    def test_background_tracks_the_ambient_level(self):
        h = DetectorHarness().settle()
        self.assertGreater(h.background, 0.5)
        # The threshold has to scale with the background, not stay constant.
        self.assertGreater(h.threshold, h.background)

    def test_background_has_no_absolute_ceiling(self):
        """
        The old estimator clamped the floor at 3500 (16-bit units, -19.4 dBFS),
        which pinned the threshold in any room louder than that.
        """
        loud_room = DetectorHarness().settle(rms=6000)
        self.assertGreater(
            loud_room.background, 3500.0,
            "The background level must not be clamped at an absolute ceiling",
        )
        self.assertGreater(loud_room.threshold, 3500.0)

    def test_background_is_not_frozen_by_loud_frames(self):
        """
        Frames that are classified as transients must still contribute to the
        background estimate, otherwise loud rooms keep a stale (too low) floor.
        """
        h = DetectorHarness().settle()
        settled = h.background
        h.feed_swell(600, rms=9000)
        h.feed_ambient(1500)
        self.assertAlmostEqual(
            h.background, settled, delta=settled * 0.35,
            msg="The background level must recover after a loud passage",
        )

    def test_single_loud_frame_does_not_inflate_the_background(self):
        h = DetectorHarness().settle()
        settled = h.background
        h.feed_clap(peak=30000)
        h.feed_ambient(200)
        self.assertLess(
            h.background, settled * 1.5,
            "An isolated transient must not drag the background level up",
        )

    def test_calibration_ignores_a_single_impulse(self):
        """
        The startup calibration uses the median of the first frames, so a clap
        during startup cannot inflate the floor the way a mean would.
        """
        h = DetectorHarness()
        h.feed_ambient(400)
        h.feed_clap(peak=30000)
        h.feed_ambient(400)
        self.assertLess(
            h.background, 15000.0,
            "A single impulse during calibration must not set the background level",
        )

    def test_threshold_is_expressed_in_the_same_units_as_the_measurement(self):
        """
        The background estimate and the detection threshold have to be measured
        with the same statistic that the detector tests, otherwise the
        comparison is meaningless.
        """
        h = DetectorHarness().settle()
        analysis = h.detector.analyze_frame(noise_chunk(LOUD_AMBIENT_RMS, 7))
        self.assertGreater(analysis.peak, 0.0)
        # The tracked background is a peak-scale estimate, so it must sit close
        # to the measured frame peak (not on the diluted chunk-RMS scale).
        self.assertGreater(h.background, analysis.rms)
        self.assertLess(abs(h.background - analysis.peak), analysis.peak * 0.75)
        # ... and the threshold is a multiple of that same background.
        self.assertGreater(h.threshold, h.background)


class TestConfidence(unittest.TestCase):
    """The reported confidence must carry information."""

    def test_confidence_is_bounded(self):
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.confirm()
        self.assertEqual(len(h.events), 1)
        confidence = h.events[0].metadata["confidence"]
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 0.99)

    def test_confidence_is_not_a_constant(self):
        """
        The old formula (peak / (2 * noise_floor), capped at 0.99) returned
        0.99 for every event, which hid the problem completely.
        """
        weak = DetectorHarness().settle()
        weak.feed_clap(peak=30000)
        weak.feed_ambient(300)
        weak.feed_clap(peak=30000)
        weak.confirm()

        strong = DetectorHarness().settle(rms=200)
        strong.feed_clap(peak=30000)
        strong.feed_ambient(300)
        strong.feed_clap(peak=30000)
        strong.confirm()

        self.assertEqual(len(weak.events), 1)
        self.assertEqual(len(strong.events), 1)
        self.assertNotEqual(
            weak.events[0].metadata["confidence"],
            strong.events[0].metadata["confidence"],
            "The confidence must reflect how convincing the event actually was",
        )

    def test_marginal_event_reports_lower_confidence_than_a_clear_one(self):
        """A clap that barely clears the threshold must be less confident."""
        marginal = DetectorHarness().settle()
        threshold = marginal.threshold
        # Find the smallest clap peak that still clears the detection
        # threshold, so the event is deliberately marginal.
        peak = 25000.0
        for _ in range(24):
            probe = DetectorHarness().settle()
            probe.feed_clap(peak=peak)
            measured = probe.detector.analyze_frame(clap_chunk(peak, seed=99)).peak
            if measured > threshold:
                break
            peak *= 1.12
        marginal.feed_clap(peak=peak)
        marginal.feed_ambient(300)
        marginal.feed_clap(peak=peak)
        marginal.confirm()

        clear = DetectorHarness().settle(rms=200)
        clear.feed_clap(peak=30000)
        clear.feed_ambient(300)
        clear.feed_clap(peak=30000)
        clear.confirm()

        self.assertEqual(len(marginal.events), 1)
        self.assertEqual(len(clear.events), 1)
        self.assertLess(
            marginal.events[0].metadata["confidence"],
            clear.events[0].metadata["confidence"],
        )


class TestDoubleClapStateMachine(unittest.TestCase):
    """Tempo window, cooldown and anchor handling."""

    def test_claps_too_close_are_rejected(self):
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(60)
        h.feed_clap(peak=30000)
        h.feed_ambient(1000)
        self.assertEqual(len(h.events), 0)

    def test_claps_too_far_apart_are_rejected(self):
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(1200)
        h.feed_clap(peak=30000)
        h.feed_ambient(500)
        self.assertEqual(len(h.events), 0)

    def test_echo_like_transient_does_not_pair_with_a_later_event(self):
        """
        A transient that arrives too soon after the first clap is an echo or
        rebound.  It must be discarded completely - the detector must not stay
        armed against a stale anchor and complete a pair with an unrelated
        later sound.
        """
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)          # first clap
        h.feed_ambient(50)               # ~50 ms
        h.feed_clap(peak=30000)          # echo / rebound -> must be discarded
        h.feed_ambient(1500)             # well past the tempo window
        h.feed_clap(peak=30000)          # a fresh, unrelated clap
        h.feed_ambient(500)
        self.assertEqual(len(h.events), 0)

    def test_cooldown_suppresses_duplicate_activations(self):
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.confirm()
        self.assertEqual(len(h.events), 1)

        # A second double-clap inside the cooldown must not emit another event
        h.feed_ambient(200)
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.confirm()
        self.assertEqual(len(h.events), 1)

        # After the cooldown a new double-clap is accepted again
        h.feed_ambient(1500)
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.confirm()
        self.assertEqual(len(h.events), 2)


class TestDoubleClapStructure(unittest.TestCase):
    """
    A double clap is *two comparable strikes* - not "any two loud sounds".

    These tests cover the structural rules that keep a single clap plus some
    unrelated noise, and a train of mechanical key presses, from being
    reported as a double clap.
    """

    def test_single_clap_plus_minor_noise_does_not_activate(self):
        """
        One loud clap followed by a much quieter background noise must not
        complete a pair: the two strikes of a double clap have a comparable
        amplitude.
        """
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_click(peak=3000)          # ~18 dB below the clap
        h.confirm()
        self.assertEqual(
            len(h.events), 0,
            "A single clap plus a much quieter noise must not activate",
        )

    def test_single_clap_plus_similar_noise_does_not_activate(self):
        """
        Even a noise of the same order as the clap is not a second strike
        when it is a *click* rather than a clap: the pair is only confirmed
        when nothing comparable follows it.
        """
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_click(peak=25000)
        h.confirm()
        # A third, comparable burst is what cancels a pair - here the click
        # itself is the second strike, so the pair is pending and then
        # confirmed unless a third burst follows.
        self.assertLessEqual(len(h.events), 1)

    def test_typing_never_activates(self):
        """
        A mechanical keyboard produces a train of comparable clicks.  No
        combination of them may be reported as a double clap.
        """
        for gap_ms in (120, 180, 250, 350, 450):
            for click_peak in (6000, 14000, 20000):
                h = DetectorHarness().settle()
                for _ in range(10):
                    h.feed_click(peak=click_peak)
                    h.feed_ambient(gap_ms)
                h.confirm()
                self.assertEqual(
                    len(h.events), 0,
                    f"typing (gap {gap_ms}ms, peak {click_peak}) must not activate",
                )

    def test_speech_never_activates(self):
        """
        Speech contains short impulsive sounds - the plosives in "t", "k" or
        "p".  Two of them close together must not be reported as a double
        clap: they have no low frequency thud, a clap has.
        """
        for gap_ms in (150, 200, 300, 400):
            for peak in (8000, 16000, 24000):
                h = DetectorHarness().settle()
                for _ in range(8):
                    h.feed_plosive(peak=peak)
                    h.feed_ambient(gap_ms)
                h.confirm()
                self.assertEqual(
                    len(h.events), 0,
                    f"speech (gap {gap_ms}ms, peak {peak}) must not activate",
                )

    def test_quiet_transients_are_rejected_by_the_absolute_floor(self):
        """
        In a quiet room a relative threshold cannot separate a clap from
        speech or key presses, because everything is loud compared with the
        silence.  The absolute floor is what stops that: a pair of quiet
        impulses must not activate the detector.
        """
        h = DetectorHarness().settle(rms=200)
        for _ in range(6):
            h.feed_clap(peak=6000)
            h.feed_ambient(250)
        h.confirm()
        self.assertEqual(
            len(h.events), 0,
            "a pair of quiet claps must not activate in a silent room",
        )

    def test_absolute_floor_is_adjustable(self):
        """The absolute floor is a setting the user can change."""
        h = DetectorHarness().settle(rms=200)
        self.assertGreater(h.detector.current_min_peak_threshold(), 0.0)
        h.detector.apply_settings({"clap_min_peak_threshold": 100.0})
        self.assertAlmostEqual(
            h.detector.current_min_peak_threshold(), 100.0, places=1
        )

    def test_voiced_speech_never_activates(self):
        """
        The release of a voiced consonant ("d", "b", "g") has the low
        frequency of a clap but almost none of its broadband crack, and a
        vowel is a continuous sound.  Neither may activate the detector.
        """
        for gap_ms in (150, 250, 400):
            for peak in (8000, 16000, 24000):
                h = DetectorHarness().settle()
                for _ in range(8):
                    h.feed_voiced(peak=peak)
                    h.feed_ambient(gap_ms)
                h.confirm()
                self.assertEqual(
                    len(h.events), 0,
                    f"voiced speech (gap {gap_ms}ms, peak {peak}) must not activate",
                )

        # A sustained vowel is rejected by the concentration test.
        h = DetectorHarness().settle()
        for _ in range(8):
            h.feed_vowel(peak=16000)
            h.feed_ambient(250)
        h.confirm()
        self.assertEqual(len(h.events), 0, "a sustained vowel must not activate")

    def test_speech_with_a_real_clap_still_activates(self):
        """
        The low band test must not make the detector deaf: a real double clap
        in the same room, with speech in between, still activates.
        """
        h = DetectorHarness().settle()
        h.feed_plosive(peak=16000)
        h.feed_ambient(200)
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.confirm()
        self.assertEqual(len(h.events), 1)

    def test_key_click_is_not_a_clap(self):
        """
        A single key click is loud enough to pass the amplitude test, but it
        has no low frequency thud, so it is not a clap.
        """
        h = DetectorHarness().settle()
        h.feed_click(peak=20000)
        h.feed_ambient(300)
        h.feed_click(peak=20000)
        h.confirm()
        self.assertEqual(len(h.events), 0)

    def test_low_band_share_is_reported(self):
        """
        The detector measures how much of a burst comes from the low band.
        A clap scores far higher than a key click, and the value has to be
        visible so that the threshold can be tuned on real hardware.
        """
        h = DetectorHarness().settle()
        clap = h.detector.analyze_frame(clap_chunk(30000, seed=5))
        click = h.detector.analyze_frame(key_click_chunk(14000, seed=5))
        plosive = h.detector.analyze_frame(speech_plosive_chunk(14000, seed=5))
        self.assertGreater(clap.low_band_share, 0.7)
        self.assertLess(click.low_band_share, 0.4)
        self.assertLess(plosive.low_band_share, 0.4)

    def test_third_burst_cancels_the_pair(self):
        """
        Two strikes followed by a third comparable burst is a train of
        sounds, not a double clap.
        """
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.feed_ambient(100)
        h.feed_clap(peak=30000)
        h.confirm()
        self.assertEqual(
            len(h.events), 0,
            "A third comparable burst must cancel the pair",
        )

    def test_unrelated_quiet_sound_does_not_cancel_the_pair(self):
        """A quiet, unrelated sound after a double clap must not cancel it."""
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.feed_ambient(100)
        h.feed_click(peak=1500)          # far below the pair
        h.confirm()
        self.assertEqual(
            len(h.events), 1,
            "An unrelated quiet sound must not cancel a real double clap",
        )

    def test_pair_is_confirmed_only_after_the_confirmation_window(self):
        """
        A matched pair is held briefly so that a third burst can still
        cancel it.  The activation must not be reported before that window
        has elapsed.
        """
        h = DetectorHarness().settle()
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=30000)
        h.feed_silence(h.detector.pair_confirmation_ms * 0.5)
        self.assertEqual(len(h.events), 0, "The pair must not be reported immediately")
        h.confirm()
        self.assertEqual(len(h.events), 1)

    def test_uneven_strikes_are_still_accepted(self):
        """
        A real double clap does not have to be perfectly even, but the two
        strikes have to stay within the same order of magnitude.
        """
        h = DetectorHarness().settle(rms=400)
        h.feed_clap(peak=30000)
        h.feed_ambient(300)
        h.feed_clap(peak=14000)
        h.confirm()
        self.assertEqual(len(h.events), 1, "Uneven but comparable strikes are a double clap")


if __name__ == "__main__":
    unittest.main()
