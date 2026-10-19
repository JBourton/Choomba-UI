"""
Automated Unit Tests for LocalWebSocketServer & Protocol
Verifies RFC 6455 handshake, frame parsing, origin security validation, and event broadcasting.
"""

import asyncio
import base64
import hashlib
import json
import struct
import unittest

from backend.server import LocalWebSocketServer, WS_GUID


class TestLocalWebSocketServer(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.server = LocalWebSocketServer(
            host="127.0.0.1",
            port=0,
            allowed_origins={"http://localhost:3000", "http://127.0.0.1:3000"},
            on_command=self._handle_cmd,
        )
        self.received_commands = []
        await self.server.start()
        # Retrieve actual bound port allocated by OS
        self.port = self.server._server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        await self.server.stop()

    async def _handle_cmd(self, cmd, writer):
        self.received_commands.append(cmd)
        if cmd.get("action") == "ping":
            await self.server.send_to_client(writer, {"type": "pong"})

    def _build_handshake(self, key: str, origin: str = "http://localhost:3000") -> bytes:
        return (
            f"GET / HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"Origin: {origin}\r\n\r\n"
        ).encode("utf-8")

    def _build_masked_text_frame(self, text: str) -> bytes:
        payload = text.encode("utf-8")
        length = len(payload)
        mask_key = bytes([0x12, 0x34, 0x56, 0x78])

        header = bytearray([0x81])  # FIN=1, Opcode=1
        if length <= 125:
            header.append(length | 0x80)
        else:
            header.append(126 | 0x80)
            header.extend(struct.pack("!H", length))

        header.extend(mask_key)
        masked_payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return bytes(header) + masked_payload

    async def _read_unmasked_text_frame(self, reader: asyncio.StreamReader) -> str:
        head = await reader.readexactly(2)
        opcode = head[0] & 0x0F
        self.assertEqual(opcode, 0x01, "Expected text frame")
        payload_len = head[1] & 0x7F
        if payload_len == 126:
            ext = await reader.readexactly(2)
            payload_len = struct.unpack("!H", ext)[0]
        elif payload_len == 127:
            ext = await reader.readexactly(8)
            payload_len = struct.unpack("!Q", ext)[0]

        payload = await reader.readexactly(payload_len)
        return payload.decode("utf-8")

    async def test_handshake_and_ping_pong(self):
        """Test valid WebSocket handshake and round-trip ping-pong frame."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        handshake = self._build_handshake(key, origin="http://localhost:3000")
        writer.write(handshake)
        await writer.drain()

        # Read handshake response
        response = await reader.readuntil(b"\r\n\r\n")
        response_str = response.decode("utf-8")
        self.assertIn("101 Switching Protocols", response_str)

        expected_accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        self.assertIn(f"Sec-WebSocket-Accept: {expected_accept}", response_str)
        self.assertEqual(self.server.client_count, 1)

        # Send ping action command
        cmd_frame = self._build_masked_text_frame(json.dumps({"action": "ping"}))
        writer.write(cmd_frame)
        await writer.drain()

        # Read response
        reply_json_str = await self._read_unmasked_text_frame(reader)
        reply = json.loads(reply_json_str)
        self.assertEqual(reply.get("type"), "pong")

        writer.close()
        await writer.wait_closed()

    async def test_unauthorized_origin_rejected(self):
        """Connection from unauthorized browser origin must be rejected with HTTP 403."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        # Malicious external origin
        handshake = self._build_handshake(key, origin="http://malicious-site.example.com")
        writer.write(handshake)
        await writer.drain()

        response = await reader.readuntil(b"\r\n\r\n")
        response_str = response.decode("utf-8")
        self.assertIn("403 Forbidden", response_str)
        self.assertEqual(self.server.client_count, 0)

        writer.close()
        await writer.wait_closed()

    async def test_broadcast_event(self):
        """Broadcasted event should be received by all connected WebSocket clients."""
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        writer.write(self._build_handshake(key))
        await writer.drain()
        await reader.readuntil(b"\r\n\r\n")

        # Broadcast event
        test_event = {
            "type": "activation.detected",
            "method": "double_clap",
            "timestamp": "2026-10-19T01:00:00Z",
            "metadata": {"interval_ms": 320.0},
        }
        await self.server.broadcast(test_event)

        received_str = await self._read_unmasked_text_frame(reader)
        received_obj = json.loads(received_str)
        self.assertEqual(received_obj["type"], "activation.detected")
        self.assertEqual(received_obj["method"], "double_clap")
        self.assertEqual(received_obj["metadata"]["interval_ms"], 320.0)

        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    unittest.main()
