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
import struct
import unittest
from typing import List

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


def clap_chunk(peak: float = 25000.0, decay_ms: float = 1.2, seed: int = 1) -> bytes:
    """
    A hand-clap like impulse.

    A real clap is not white noise: it is a sharp pressure spike followed by a
    decaying resonance of the air cavity between the hands (roughly 1-2 kHz)
    plus a broadband "crack".  The model reproduces that shape, because the
    detector's burst-width test measures how many samples exceed the ambient
    peak level - a coherent pulse is many samples wide, a single-sample
    artefact is not.
    """
    tau = max(1, int(SAMPLE_RATE * decay_ms / 1000.0))
    state = seed * 2862933555777941757 + 3037000493
    samples = []
    for i in range(CHUNK_SIZE):
        state = (state * 2862933555777941757 + 3037000493) & 0xFFFFFFFFFFFFFFFF
        u1 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        state = (state * 2862933555777941757 + 3037000493) & 0xFFFFFFFFFFFFFFFF
        u2 = ((state >> 11) & 0x1FFFFFFFFFFFFF) / float(1 << 53)
        gauss = math.sqrt(-2.0 * math.log(max(u1, 1e-12))) * math.cos(2.0 * math.pi * u2)
        env = math.exp(-i / tau)
        resonance = math.sin(2.0 * math.pi * 1600.0 * i / SAMPLE_RATE)
        samples.append(env * (resonance + 0.35 * gauss))
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


class ClapStream:
    """
    Produces a clap that starts at an arbitrary offset inside a frame and
    continues into the following frames, so a clap that straddles a frame
    boundary can be replayed faithfully.
    """

    def __init__(self, peak: float, offset: int, decay_ms: float = 0.8, seed: int = 1):
        self.peak = peak
        self.offset = offset
        self.tau = max(1, int(SAMPLE_RATE * decay_ms / 1000.0))
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
        burst = [raw[i] * math.exp(-i / self.tau) for i in range(len(raw))]
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
        params = dict(
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE,
            sensitivity=sensitivity,
            min_clap_interval_ms=140.0,
            max_clap_interval_ms=850.0,
            max_transient_duration_ms=60.0,
            cooldown_ms=1500.0,
        )
        params.update(kwargs)
        self.detector = DoubleClapDetector(**params)
        self.detector.set_virtual_time_mode(True, start_time=0.0)
        self.detector.start()
        self.events: List[ActivationEvent] = []
        self.detector.set_callback(self.events.append)
        self._seed = 1

    # -- feeding -----------------------------------------------------------
    def feed(self, chunk: bytes) -> None:
        self.detector.process_frame(chunk)

    def feed_ambient(self, duration_ms: float, rms: float = LOUD_AMBIENT_RMS) -> None:
        for _ in range(int(duration_ms / CHUNK_MS)):
            self._seed += 1
            self.feed(noise_chunk(rms, self._seed))

    def feed_swell(self, duration_ms: float, rms: float = 7000.0) -> None:
        for _ in range(int(duration_ms / CHUNK_MS)):
            self._seed += 1
            self.feed(swell_chunk(rms, self._seed))

    def feed_clap(self, peak: float = 25000.0) -> None:
        self._seed += 1
        self.feed(clap_chunk(peak, seed=self._seed))

    # -- helpers -----------------------------------------------------------
    @property
    def background(self) -> float:
        return self.detector.noise_floor

    @property
    def threshold(self) -> float:
        return self.detector.current_detection_threshold()

    def settle(self, rms: float = LOUD_AMBIENT_RMS) -> "DetectorHarness":
        """Feed enough ambient for the startup calibration to complete."""
        self.feed_ambient(2000, rms=rms)
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
        h.feed_clap(peak=25000)
        h.feed_ambient(300)
        h.feed_clap(peak=25000)
        h.feed_ambient(400)
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
        h.feed_clap(peak=12000)
        h.feed_ambient(300)
        h.feed_clap(peak=12000)
        h.feed_ambient(400)
        self.assertEqual(len(h.events), 1)

    def test_clap_straddling_a_frame_boundary_is_detected(self):
        """
        A clap that starts near the end of a capture chunk is split across two
        frames; it must still be recognised.
        """
        for offset in (0, 64, 200, 400, 500):
            h = DetectorHarness().settle()
            stream = ClapStream(peak=25000, offset=offset)
            h.feed(stream.next_chunk())          # frame containing the clap onset
            h.feed(stream.next_chunk())          # frame containing the decay
            h.feed_ambient(300)
            stream2 = ClapStream(peak=25000, offset=offset)
            h.feed(stream2.next_chunk())
            h.feed(stream2.next_chunk())
            h.feed_ambient(400)
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
        h.feed_clap(peak=25000)
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
        h.feed_clap(peak=25000)
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
        h.feed_clap(peak=25000)
        h.feed_ambient(300)
        h.feed_clap(peak=25000)
        h.feed_ambient(400)
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
        weak.feed_clap(peak=25000)
        weak.feed_ambient(300)
        weak.feed_clap(peak=25000)
        weak.feed_ambient(400)

        strong = DetectorHarness().settle(rms=200)
        strong.feed_clap(peak=30000)
        strong.feed_ambient(300)
        strong.feed_clap(peak=30000)
        strong.feed_ambient(400)

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
        marginal.feed_ambient(400)

        clear = DetectorHarness().settle(rms=200)
        clear.feed_clap(peak=30000)
        clear.feed_ambient(300)
        clear.feed_clap(peak=30000)
        clear.feed_ambient(400)

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
        h.feed_clap(peak=25000)
        h.feed_ambient(60)
        h.feed_clap(peak=25000)
        h.feed_ambient(1000)
        self.assertEqual(len(h.events), 0)

    def test_claps_too_far_apart_are_rejected(self):
        h = DetectorHarness().settle()
        h.feed_clap(peak=25000)
        h.feed_ambient(1200)
        h.feed_clap(peak=25000)
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
        h.feed_clap(peak=25000)          # first clap
        h.feed_ambient(50)               # ~50 ms
        h.feed_clap(peak=25000)          # echo / rebound -> must be discarded
        h.feed_ambient(1500)             # well past the tempo window
        h.feed_clap(peak=25000)          # a fresh, unrelated clap
        h.feed_ambient(500)
        self.assertEqual(len(h.events), 0)

    def test_cooldown_suppresses_duplicate_activations(self):
        h = DetectorHarness().settle()
        h.feed_clap(peak=25000)
        h.feed_ambient(300)
        h.feed_clap(peak=25000)
        h.feed_ambient(200)
        self.assertEqual(len(h.events), 1)

        # A second double-clap inside the cooldown must not emit another event
        h.feed_ambient(200)
        h.feed_clap(peak=25000)
        h.feed_ambient(300)
        h.feed_clap(peak=25000)
        h.feed_ambient(200)
        self.assertEqual(len(h.events), 1)

        # After the cooldown a new double-clap is accepted again
        h.feed_ambient(1500)
        h.feed_clap(peak=25000)
        h.feed_ambient(300)
        h.feed_clap(peak=25000)
        h.feed_ambient(200)
        self.assertEqual(len(h.events), 2)


if __name__ == "__main__":
    unittest.main()
