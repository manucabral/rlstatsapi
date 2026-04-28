from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import ssl
from dataclasses import dataclass

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketHandshakeError(ConnectionError):
    """Raised when websocket upgrade fails."""


@dataclass(slots=True)
class SimpleWebSocket:
    """Minimal stdlib websocket client optimized for receiving text frames."""

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    async def recv_text(self) -> str:
        opcode, payload = await self._read_frame()

        if opcode == 0x8:  # close
            await self.close()
            raise ConnectionAbortedError("Websocket closed by peer")
        if opcode == 0x9:  # ping
            await self._send_pong(payload)
            return await self.recv_text()
        if opcode == 0xA:  # pong
            return await self.recv_text()
        if opcode != 0x1:
            raise ConnectionError(f"Unsupported opcode: {opcode}")

        return payload.decode("utf-8")

    async def close(self) -> None:
        if self.writer.is_closing():
            return
        try:
            await self._send_frame(0x8, b"")
        except Exception:
            pass
        self.writer.close()
        await self.writer.wait_closed()

    async def _send_pong(self, payload: bytes) -> None:
        await self._send_frame(0xA, payload)

    async def _send_frame(self, opcode: int, payload: bytes) -> None:
        fin_and_opcode = 0x80 | (opcode & 0x0F)
        mask_and_len = 0x80
        payload_len = len(payload)

        header = bytearray([fin_and_opcode])
        if payload_len < 126:
            header.append(mask_and_len | payload_len)
        elif payload_len <= 0xFFFF:
            header.append(mask_and_len | 126)
            header.extend(payload_len.to_bytes(2, "big"))
        else:
            header.append(mask_and_len | 127)
            header.extend(payload_len.to_bytes(8, "big"))

        mask = os.urandom(4)
        header.extend(mask)

        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))

        self.writer.write(header)
        self.writer.write(masked_payload)
        await self.writer.drain()

    async def _read_frame(self) -> tuple[int, bytes]:
        first_two = await self.reader.readexactly(2)
        first, second = first_two[0], first_two[1]

        fin = (first & 0x80) != 0
        opcode = first & 0x0F
        masked = (second & 0x80) != 0
        payload_len = second & 0x7F

        if payload_len == 126:
            payload_len = int.from_bytes(await self.reader.readexactly(2), "big")
        elif payload_len == 127:
            payload_len = int.from_bytes(await self.reader.readexactly(8), "big")

        mask_key = await self.reader.readexactly(4) if masked else b""
        payload = await self.reader.readexactly(payload_len)

        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

        if not fin:
            raise ConnectionError("Fragmented frames are not supported")

        return opcode, payload


async def connect_websocket(
    *,
    host: str,
    port: int,
    path: str = "/",
    timeout: float = 5.0,
    secure: bool = False,
) -> SimpleWebSocket:
    """Open websocket connection via stdlib stream upgrade."""

    key = base64.b64encode(os.urandom(16)).decode("ascii")

    ssl_ctx = ssl.create_default_context() if secure else None
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host=host, port=port, ssl=ssl_ctx),
        timeout=timeout,
    )

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )

    writer.write(request.encode("ascii"))
    await writer.drain()

    response = await _read_http_response(reader)
    status_line = response[0]

    if " 101 " not in status_line:
        writer.close()
        await writer.wait_closed()
        raise WebSocketHandshakeError(f"Handshake failed: {status_line.strip()}")

    headers = _parse_headers(response[1:])
    accept = headers.get("sec-websocket-accept")

    expected = base64.b64encode(
        hashlib.sha1((key + _WS_GUID).encode("ascii")).digest()
    ).decode("ascii")
    if accept != expected:
        writer.close()
        await writer.wait_closed()
        raise WebSocketHandshakeError("Invalid Sec-WebSocket-Accept from server")

    return SimpleWebSocket(reader=reader, writer=writer)


async def _read_http_response(reader: asyncio.StreamReader) -> list[str]:
    lines: list[str] = []
    while True:
        line = (await reader.readline()).decode("iso-8859-1")
        if not line:
            raise WebSocketHandshakeError("Unexpected EOF during handshake")
        lines.append(line)
        if line == "\r\n":
            return lines


def _parse_headers(lines: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in lines:
        if line == "\r\n":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return headers
