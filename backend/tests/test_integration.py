"""
End-to-End Integration Test for Choomba Activation Service
Tests full pipeline: MockAudioStream -> DoubleClapDetector -> ActivationService -> LocalWebSocketServer.
"""

import asyncio
import json
import unittest

from backend.service import ActivationService
from backend.tests.test_clap_detector import make_chunk_silence, make_chunk_transient
from backend.tests.test_server import WS_GUID


class TestEndToEndActivationIntegration(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Start service with mock audio on ephemeral port
        self.service = ActivationService(host="127.0.0.1", port=0, use_mock_audio=True, sensitivity=0.8)
        await self.service.start()
        self.port = self.service.server._server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        await self.service.stop()

    def _build_handshake(self, key: str = "dGhlIHNhbXBsZSBub25jZQ==") -> bytes:
        return (
            f"GET / HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Origin: http://localhost:3000\r\n\r\n"
        ).encode("utf-8")

    async def _read_frame_json(self, reader: asyncio.StreamReader) -> dict:
        head = await reader.readexactly(2)
        payload_len = head[1] & 0x7F
        if payload_len == 126:
            ext = await reader.readexactly(2)
            payload_len = int.from_bytes(ext, "big")
        elif payload_len == 127:
            ext = await reader.readexactly(8)
            payload_len = int.from_bytes(ext, "big")
        payload = await reader.readexactly(payload_len)
        return json.loads(payload.decode("utf-8"))

    async def test_end_to_end_activation_delivery(self):
        """Verify mock audio clap detection sends activation.detected event over WebSocket."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        writer.write(self._build_handshake())
        await writer.drain()

        # Read handshake response
        await reader.readuntil(b"\r\n\r\n")

        # Feed audio into mock stream: baseline calm.
        # The detector calibrates its background level from the first frames,
        # so enough silence has to be delivered before any clap is analysed.
        for _ in range(30):
            self.service.stream.enqueue_chunk(make_chunk_silence(512))

        # First clap
        for _ in range(2):
            self.service.stream.enqueue_chunk(make_chunk_transient(512, peak=12000))

        # Real-time gap between claps (300ms)
        await asyncio.sleep(0.3)

        # Second clap
        for _ in range(2):
            self.service.stream.enqueue_chunk(make_chunk_transient(512, peak=12000))

        # Post-clap calm
        for _ in range(10):
            self.service.stream.enqueue_chunk(make_chunk_silence(512))

        # Await activation event delivered to WebSocket client
        event = await asyncio.wait_for(self._read_frame_json(reader), timeout=2.0)

        self.assertEqual(event.get("type"), "activation.detected")
        self.assertEqual(event.get("method"), "double_clap")
        self.assertIn("interval_ms", event.get("metadata", {}))
        self.assertIn("timestamp", event)

        writer.close()
        await writer.wait_closed()

    async def test_settings_roundtrip(self):
        """The UI can read and change the detector settings over the socket."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        writer.write(self._build_handshake())
        await writer.drain()
        await reader.readuntil(b"\r\n\r\n")

        async def send(obj):
            payload = json.dumps(obj).encode()
            writer.write(bytearray([0x81, len(payload)]) + payload)
            await writer.drain()

        async def recv():
            head = await reader.readexactly(2)
            length = head[1] & 0x7F
            if length == 126:
                length = int.from_bytes(await reader.readexactly(2), "big")
            return json.loads((await reader.readexactly(length)).decode())

        await send({"action": "get_settings"})
        reply = await recv()
        self.assertEqual(reply.get("type"), "settings")
        self.assertIn("clap_sensitivity", reply.get("settings", {}))

        await send({"action": "set_settings", "settings": {
            "clap_sensitivity": 0.35,
            "clap_min_low_band_share": 0.5,
            "sample_rate": 8000,       # not editable, must be ignored
        }})
        applied = await recv()
        while applied.get("type") != "settings":
            applied = await recv()
        self.assertAlmostEqual(
            self.service.detector.sensitivity, 0.35, places=3
        )
        self.assertAlmostEqual(
            self.service.detector.min_low_band_share, 0.5, places=3
        )

        writer.close()
        await writer.wait_closed()

    async def test_frontend_reconnection_resilience(self):
        """Verify client can disconnect and reconnect cleanly without daemon issues."""
        # Client 1 connects
        reader1, writer1 = await asyncio.open_connection("127.0.0.1", self.port)
        writer1.write(self._build_handshake())
        await writer1.drain()
        await reader1.readuntil(b"\r\n\r\n")
        self.assertEqual(self.service.server.client_count, 1)

        # Client 1 abruptly disconnects
        writer1.close()
        await writer1.wait_closed()
        await asyncio.sleep(0.05)

        # Client 2 connects
        reader2, writer2 = await asyncio.open_connection("127.0.0.1", self.port)
        writer2.write(self._build_handshake())
        await writer2.drain()
        await reader2.readuntil(b"\r\n\r\n")
        self.assertEqual(self.service.server.client_count, 1)

        writer2.close()
        await writer2.wait_closed()


if __name__ == "__main__":
    unittest.main()
