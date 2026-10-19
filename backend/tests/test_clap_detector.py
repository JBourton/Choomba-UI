"""
Automated Unit Tests for DoubleClapDetector
Tests acoustic transient logic against synthetic audio frames without hardware requirements.
"""

import math
import struct
import unittest
from typing import List

from backend.detector.clap_detector import DoubleClapDetector
from backend.detector.base import ActivationEvent


def make_chunk_silence(num_samples: int = 512) -> bytes:
    """Generate a single frame of silence (zeros)."""
    return b"\x00" * (num_samples * 2)


def make_chunk_transient(num_samples: int = 512, peak: int = 8000) -> bytes:
    """
    Generate an acoustic transient pulse:
    Sharp spike in the center with fast decay, mimicking a hand clap.
    """
    samples = []
    center = num_samples // 4
    for i in range(num_samples):
        dist = abs(i - center)
        # Fast exponential decay
        val = int(peak * math.exp(-dist / 8.0) * math.sin(i * 0.4))
        samples.append(max(-32767, min(32767, val)))
    return struct.pack(f"{num_samples}h", *samples)


def make_chunk_continuous_noise(num_samples: int = 512, amplitude: int = 6000) -> bytes:
    """Generate sustained loud noise across the entire chunk."""
    samples = [int(amplitude * math.sin(i * 0.2)) for i in range(num_samples)]
    return struct.pack(f"{num_samples}h", *samples)


class TestDoubleClapDetector(unittest.TestCase):

    def setUp(self):
        self.sample_rate = 44100
        self.chunk_size = 512
        self.detector = DoubleClapDetector(
            sample_rate=self.sample_rate,
            chunk_size=self.chunk_size,
            sensitivity=0.8,
            min_clap_interval_ms=160.0,
            max_clap_interval_ms=750.0,
            max_transient_duration_ms=80.0,
            cooldown_ms=1200.0,
        )
        self.detector.set_virtual_time_mode(True, start_time=0.0)
        self.detector.start()
        self.events: List[ActivationEvent] = []
        self.detector.set_callback(lambda e: self.events.append(e))

    def feed_silence(self, duration_ms: float):
        chunk_ms = (self.chunk_size / self.sample_rate) * 1000.0
        num_chunks = int(duration_ms / chunk_ms)
        for _ in range(num_chunks):
            self.detector.process_frame(make_chunk_silence(self.chunk_size))

    def feed_clap(self, peak: int = 9000, duration_chunks: int = 2):
        # A clap transient typically spans 1-3 chunks (11ms - 34ms)
        for _ in range(duration_chunks):
            self.detector.process_frame(make_chunk_transient(self.chunk_size, peak=peak))

    def feed_continuous_noise(self, duration_ms: float, amplitude: int = 7000):
        chunk_ms = (self.chunk_size / self.sample_rate) * 1000.0
        num_chunks = int(duration_ms / chunk_ms)
        for _ in range(num_chunks):
            self.detector.process_frame(make_chunk_continuous_noise(self.chunk_size, amplitude=amplitude))

    def test_silence_produces_no_activation(self):
        """Pure ambient silence should never trigger an activation."""
        self.feed_silence(2000.0)
        self.assertEqual(len(self.events), 0)
        self.assertEqual(self.detector.state, "IDLE")

    def test_single_clap_does_not_activate(self):
        """A single clap followed by silence should transition to waiting and then time out."""
        # Baseline calm
        self.feed_silence(200.0)
        # Single clap
        self.feed_clap(peak=10000)
        # Silence for > max_clap_interval
        self.feed_silence(1000.0)

        self.assertEqual(len(self.events), 0, "Single clap must not trigger an activation")
        self.assertEqual(self.detector.state, "IDLE", "Detector should return to IDLE after timeout")

    def test_valid_double_clap_triggers_activation(self):
        """Two claps separated by 300ms should trigger exactly one activation event."""
        # Baseline calm
        self.feed_silence(200.0)

        # Clap 1
        self.feed_clap(peak=12000)

        # 300ms gap between claps
        self.feed_silence(300.0)

        # Clap 2
        self.feed_clap(peak=11000)

        # Let the burst conclude
        self.feed_silence(100.0)

        self.assertEqual(len(self.events), 1, "Valid double clap should trigger exactly 1 event")
        event = self.events[0]
        self.assertEqual(event.type, "activation.detected")
        self.assertEqual(event.method, "double_clap")
        self.assertTrue("interval_ms" in event.metadata)
        # Interval should be approx 300ms + chunk duration
        self.assertGreaterEqual(event.metadata["interval_ms"], 250.0)
        self.assertLessEqual(event.metadata["interval_ms"], 400.0)

    def test_claps_too_close_rejected(self):
        """Two claps separated by only 60ms (less than min_clap_interval) must be rejected."""
        self.feed_silence(200.0)
        # First clap
        self.feed_clap(peak=10000)
        # Only 60ms gap (rebound or echo)
        self.feed_silence(60.0)
        # Second clap too fast
        self.feed_clap(peak=10000)
        # Settle
        self.feed_silence(1000.0)

        self.assertEqual(len(self.events), 0, "Claps spaced too closely should be rejected")

    def test_claps_too_far_apart_rejected(self):
        """Two claps separated by 900ms (greater than max_clap_interval) must not activate together."""
        self.feed_silence(200.0)
        # First clap
        self.feed_clap(peak=10000)
        # 900ms gap (exceeds max_clap_interval_ms of 750ms)
        self.feed_silence(900.0)
        # Second clap arrives after first has expired
        self.feed_clap(peak=10000)
        # Settle
        self.feed_silence(1000.0)

        self.assertEqual(len(self.events), 0, "Claps spaced too far apart should not trigger activation")

    def test_continuous_noise_does_not_activate(self):
        """Sustained loud audio (e.g. speech or vacuum for 300ms) must be gated and rejected."""
        self.feed_silence(200.0)
        # 300ms of continuous high energy (longer than max_transient_duration_ms=80ms)
        self.feed_continuous_noise(300.0, amplitude=9000)
        self.feed_silence(200.0)
        self.feed_continuous_noise(300.0, amplitude=9000)
        self.feed_silence(500.0)

        self.assertEqual(len(self.events), 0, "Continuous sustained noise must not trigger activation")

    def test_cooldown_prevents_duplicate_events(self):
        """Subsequent claps during the cooldown period (1200ms) must not emit duplicate events."""
        self.feed_silence(200.0)
        # Valid double clap
        self.feed_clap(peak=12000)
        self.feed_silence(300.0)
        self.feed_clap(peak=12000)
        self.feed_silence(50.0)
        self.assertEqual(len(self.events), 1)

        # Clap immediately again during cooldown (e.g. applause or cheering)
        self.feed_silence(200.0)
        self.feed_clap(peak=12000)
        self.feed_silence(300.0)
        self.feed_clap(peak=12000)
        self.feed_silence(100.0)

        # Should still be only 1 activation
        self.assertEqual(len(self.events), 1, "No duplicate activations during cooldown period")

        # Advance past cooldown
        self.feed_silence(1500.0)

        # Now a new double-clap sequence should be accepted
        self.feed_clap(peak=12000)
        self.feed_silence(300.0)
        self.feed_clap(peak=12000)
        self.feed_silence(50.0)
        self.assertEqual(len(self.events), 2, "New activation accepted after cooldown has elapsed")

    def test_sensitivity_adjustment(self):
        """Lower sensitivity requires higher energy; higher sensitivity triggers on lower energy."""
        # Low sensitivity (0.1)
        self.detector.set_sensitivity(0.1)
        self.feed_silence(200.0)
        # Moderate clap (peak 2500, RMS ~224)
        self.feed_clap(peak=2500)
        self.feed_silence(300.0)
        self.feed_clap(peak=2500)
        self.feed_silence(200.0)
        self.assertEqual(len(self.events), 0, "Moderate claps should not trigger at sensitivity 0.1")

        # High sensitivity (0.95)
        self.detector.set_sensitivity(0.95)
        self.feed_silence(200.0)
        self.feed_clap(peak=2500)
        self.feed_silence(300.0)
        self.feed_clap(peak=2500)
        self.feed_silence(100.0)
        self.assertEqual(len(self.events), 1, "Moderate claps should trigger at sensitivity 0.95")


if __name__ == "__main__":
    unittest.main()
