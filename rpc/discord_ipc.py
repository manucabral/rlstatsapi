"""Discord local IPC client for Rich Presence (Windows-first)."""

from __future__ import annotations

import enum
import inspect
import json
import logging
import os
import struct
import time
import typing
import uuid

logger = logging.getLogger("rlstatsapi.rpc")


class OperationCode(enum.Enum):
    HANDSHAKE = 0
    FRAME = 1
    CLOSE = 2


class ActivityType(enum.Enum):
    PLAYING = 0
    LISTENING = 2
    WATCHING = 3
    COMPETING = 5


class ClientRPC:
    def __init__(self, client_id: str | int | None = None, debug: bool = False) -> None:
        self.debug = debug
        self.__client_id = "" if client_id is None else str(client_id)

        self.__socket: typing.BinaryIO | None = None
        self.__connected = False
        self._pipe_connected = True
        self._rpc_pid = os.getpid()

        pipe_template = r"\\.\pipe\discord-ipc-{}"
        for index in range(10):
            path = pipe_template.format(index)
            try:
                self.__socket = open(path, "w+b")
                if self.debug:
                    logger.info("Connected to Discord IPC: %s", path)
                break
            except FileNotFoundError:
                continue
            except OSError as exc:
                logger.error("OS error opening pipe %s: %s", path, exc)
        else:
            logger.error("Failed to connect to Discord IPC (is Discord running?)")
            self._pipe_connected = False

    @property
    def is_connected(self) -> bool:
        return self._pipe_connected and self.__connected

    def connect(self) -> None:
        if not self._pipe_connected:
            logger.warning("Discord pipe not connected")
            return
        if self.__connected:
            return
        self.__handshake()

    def update(
        self,
        state: str | None,
        details: str | None,
        activity_type: ActivityType | None,
        start_time: int | None,
        end_time: int | None,
        large_image: str | None,
        large_text: str | None,
        small_image: str | None,
        small_text: str | None,
        buttons: list[dict[str, str]] | None,
    ) -> None:
        if not self._pipe_connected or not self.__connected:
            return

        if activity_type is not None and not isinstance(activity_type, ActivityType):
            raise ValueError("Invalid activity type")

        activity: dict[str, typing.Any] = {}
        if state is not None:
            activity["state"] = state
        if details is not None:
            activity["details"] = details
        if activity_type is not None:
            activity["type"] = activity_type.value

        timestamps: dict[str, int] = {}
        if start_time is not None:
            timestamps["start"] = start_time
        if end_time is not None:
            timestamps["end"] = end_time
        if timestamps:
            activity["timestamps"] = timestamps

        assets: dict[str, str] = {}
        if large_image is not None:
            assets["large_image"] = large_image
        if large_text is not None:
            assets["large_text"] = large_text
        if small_image is not None:
            assets["small_image"] = small_image
        if small_text is not None:
            assets["small_text"] = small_text
        if assets:
            activity["assets"] = assets

        if buttons:
            activity["buttons"] = buttons[:2]

        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": self._rpc_pid, "activity": _remove_none(activity)},
            "nonce": str(uuid.uuid4()),
        }

        if self.debug:
            caller = "unknown"
            try:
                frm = inspect.stack()[1]
                mod = inspect.getmodule(frm[0])
                caller = mod.__name__ if mod else frm.filename
            except Exception:
                pass
            logger.debug("SET_ACTIVITY pid=%s caller=%s", self._rpc_pid, caller)

        self.__send(payload, OperationCode.FRAME)
        self.__recv()

    def clear_activity(self) -> None:
        if not self._pipe_connected or not self.__connected:
            return

        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": self._rpc_pid, "activity": None},
            "nonce": str(uuid.uuid4()),
        }
        if self.debug:
            logger.debug("Clearing activity pid=%s", self._rpc_pid)

        self.__send(payload, OperationCode.FRAME)
        self.__recv()

    def close(self) -> None:
        if not self._pipe_connected:
            return

        if self.__connected:
            try:
                self.clear_activity()
                time.sleep(0.25)
            except Exception:
                pass

            try:
                self.__send({}, OperationCode.CLOSE)
            except Exception:
                pass

        try:
            if self.__socket:
                self.__socket.close()
        except Exception as exc:
            logger.error("Error closing IPC socket: %s", exc)

        self.__connected = False
        if self.debug:
            logger.info("Discord RPC closed cleanly")

    def __handshake(self) -> None:
        self.__send({"v": 1, "client_id": self.__client_id}, OperationCode.HANDSHAKE)
        data = self.__recv()

        if data.get("code") == 4000:
            raise ValueError(data.get("message", "Handshake error"))

        if data.get("evt") == "READY":
            self.__connected = True
            if self.debug:
                user = data.get("data", {}).get("user", {}).get("username")
                logger.info("Discord RPC ready (user=%s)", user)
            return

        raise ValueError(f"Handshake failed: {data}")

    def __send(self, payload: dict, operation_code: OperationCode) -> None:
        if not self.__socket:
            return
        raw = json.dumps(payload).encode("utf-8")
        packet = struct.pack("<ii", operation_code.value, len(raw)) + raw
        self.__socket.write(packet)
        self.__socket.flush()
        if self.debug:
            logger.debug("IPC SEND op=%s", operation_code.name)

    def __recv(self) -> dict:
        if not self.__socket:
            return {}
        header = self.__socket.read(8)
        if not header or len(header) < 8:
            return {}

        _, size = struct.unpack("<ii", header)
        data = self.__socket.read(size)
        if not data or len(data) < size:
            return {}

        payload = json.loads(data.decode("utf-8"))
        if self.debug:
            logger.debug("IPC RECV payload=%s", payload)
        return payload


def _remove_none(value: typing.Any) -> typing.Any:
    if isinstance(value, dict):
        return {k: _remove_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_remove_none(v) for v in value if v is not None]
    return value
