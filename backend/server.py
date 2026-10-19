"""
Choomba Local WebSocket Server (RFC 6455)
Provides an ultra-lightweight, zero-dependency WebSocket transport over asyncio.
Strictly binds to 127.0.0.1 with local origin validation for offline privacy.
"""

import asyncio
import base64
import hashlib
import json
import struct
from typing import Set, Dict, Any, Optional, Callable, Awaitable

from .config import HOST, PORT, ALLOWED_ORIGINS

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
CommandHandler = Callable[[Dict[str, Any], asyncio.StreamWriter], Awaitable[None]]


class LocalWebSocketServer:
    """
    Lightweight, dependency-free RFC 6455 WebSocket server.
    Ensures safe loopback-only communication between backend daemon and frontend UI.
    """

    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        allowed_origins: Optional[Set[str]] = None,
        on_command: Optional[CommandHandler] = None,
    ):
        self.host = host
        self.port = port
        self.allowed_origins = allowed_origins if allowed_origins is not None else ALLOWED_ORIGINS
        self.on_command = on_command

        self._clients: Set[asyncio.StreamWriter] = set()
        self._server: Optional[asyncio.Server] = None
        self._is_running = False

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self) -> None:
        """Start listening on the loopback socket."""
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
            reuse_address=True,
        )
        self._is_running = True
        print(f"[WebSocket] Local server running on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Gracefully close all client connections and terminate listener."""
        self._is_running = False
        # Send close frame to all connected clients
        close_frame = bytes([0x88, 0x00])
        for writer in list(self._clients):
            try:
                writer.write(close_frame)
                await writer.drain()
                writer.close()
            except Exception:
                pass
        self._clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        print("[WebSocket] Server stopped.")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast JSON payload to all active frontend clients."""
        if not self._clients:
            return

        payload = json.dumps(message).encode("utf-8")
        frame = self._encode_text_frame(payload)

        dead_clients = []
        for writer in self._clients:
            try:
                writer.write(frame)
                await writer.drain()
            except Exception:
                dead_clients.append(writer)

        for dead in dead_clients:
            self._unregister_client(dead)

    async def send_to_client(self, writer: asyncio.StreamWriter, message: Dict[str, Any]) -> None:
        """Send a single message to a specific client."""
        try:
            payload = json.dumps(message).encode("utf-8")
            frame = self._encode_text_frame(payload)
            writer.write(frame)
            await writer.drain()
        except Exception:
            self._unregister_client(writer)

    def _encode_text_frame(self, payload: bytes) -> bytes:
        """Encode bytes into an unmasked RFC 6455 text frame (FIN=1, Opcode=0x1)."""
        length = len(payload)
        header = bytearray([0x81])  # FIN=1, Opcode=1 (Text)

        if length <= 125:
            header.append(length)
        elif length <= 65535:
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))

        return bytes(header) + payload

    def _validate_origin(self, origin_header: Optional[str]) -> bool:
        """
        Validate browser origin.
        Allows configured local development origins or empty/loopback client origins.
        """
        if not origin_header:
            # Non-browser local tools, curl, or automated test scripts
            return True

        # Check exact origin match or localhost loopback port
        origin_clean = origin_header.strip().rstrip("/")
        if origin_clean in self.allowed_origins:
            return True

        if origin_clean.startswith("http://localhost:") or origin_clean.startswith("http://127.0.0.1:"):
            return True

        return False

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle individual incoming client connection lifecycle."""
        peer = writer.get_extra_info("peername")

        # 1. Read HTTP Upgrade Request Handshake
        try:
            request_bytes = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)
            request_text = request_bytes.decode("utf-8", errors="replace")
        except Exception:
            writer.close()
            return

        lines = request_text.split("\r\n")
        if not lines or not lines[0].startswith("GET"):
            writer.close()
            return

        headers: Dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        # 2. Origin check for security & privacy
        origin = headers.get("origin")
        if not self._validate_origin(origin):
            print(f"[WebSocket] Rejected unauthorized connection from origin: {origin}")
            writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\nOrigin not allowed")
            await writer.drain()
            writer.close()
            return

        # 3. Verify WebSocket Upgrade headers
        upgrade = headers.get("upgrade", "").lower()
        connection = headers.get("connection", "").lower()
        sec_key = headers.get("sec-websocket-key")

        if upgrade != "websocket" or "upgrade" not in connection or not sec_key:
            writer.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\nInvalid WebSocket upgrade")
            await writer.drain()
            writer.close()
            return

        # 4. Compute Sec-WebSocket-Accept response
        accept_raw = sec_key + WS_GUID
        accept_sha1 = hashlib.sha1(accept_raw.encode("utf-8")).digest()
        accept_b64 = base64.b64encode(accept_sha1).decode("utf-8")

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_b64}\r\n\r\n"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()

        # Registered client
        self._clients.add(writer)
        print(f"[WebSocket] Client connected: {peer} (Origin: {origin or 'Local CLI'})")

        # 5. Frame processing loop
        try:
            while self._is_running and not reader.at_eof():
                # Read frame header (2 bytes)
                head = await reader.readexactly(2)
                byte0, byte1 = head[0], head[1]

                opcode = byte0 & 0x0F
                has_mask = bool(byte1 & 0x80)
                payload_len = byte1 & 0x7F

                # Close frame
                if opcode == 0x08:
                    # Echo close frame
                    writer.write(bytes([0x88, 0x00]))
                    await writer.drain()
                    break

                # Ping frame -> reply with Pong
                if opcode == 0x09:
                    pong_frame = bytearray([0x8A, payload_len])
                    if payload_len > 0:
                        ping_data = await reader.readexactly(payload_len)
                        pong_frame.extend(ping_data)
                    writer.write(bytes(pong_frame))
                    await writer.drain()
                    continue

                # Pong frame -> ignore
                if opcode == 0x0A:
                    if payload_len > 0:
                        await reader.readexactly(payload_len)
                    continue

                # Determine extended payload length
                if payload_len == 126:
                    ext = await reader.readexactly(2)
                    payload_len = struct.unpack("!H", ext)[0]
                elif payload_len == 127:
                    ext = await reader.readexactly(8)
                    payload_len = struct.unpack("!Q", ext)[0]

                # Read mask key (client frames must be masked per RFC 6455)
                mask_key = await reader.readexactly(4) if has_mask else None

                # Read payload bytes
                payload = await reader.readexactly(payload_len)
                if mask_key:
                    payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

                # If text frame (opcode 0x01), process command
                if opcode == 0x01:
                    try:
                        text = payload.decode("utf-8")
                        data = json.loads(text)
                        if self.on_command:
                            await self.on_command(data, writer)
                    except Exception as e:
                        print(f"[WebSocket] Error parsing command from client: {e}")

        except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            print(f"[WebSocket] Client connection error: {e}")
        finally:
            self._unregister_client(writer)
            print(f"[WebSocket] Client disconnected: {peer}")

    def _unregister_client(self, writer: asyncio.StreamWriter) -> None:
        self._clients.discard(writer)
        try:
            writer.close()
        except Exception:
            pass
