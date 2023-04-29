from __future__ import annotations

import logging
import os
from threading import Thread

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s: %(message)s",
)


def set_logging_color(level: int, color: int) -> None:
    def get_color_code(color: int = 0) -> str:
        return f"\033[{color}m"

    fmt = f"{get_color_code(color)}{logging.getLevelName(level)}{get_color_code()}"
    logging.addLevelName(level, fmt)


set_logging_color(logging.DEBUG, 34)  # blue
set_logging_color(logging.INFO, 32)  # green
set_logging_color(logging.WARNING, 33)  # yellow
set_logging_color(logging.ERROR, 31)  # red
set_logging_color(logging.CRITICAL, 35)  # magenta


logger = logging.getLogger("quic_impl")


class Connection:
    def __init__(self, address: tuple[str, int]) -> None:
        """Initialize the QUIC connection from a server's view."""

        self.address = address
        self.sender = QUICMessageSender(address)
        self.receiver = QUICMessageReceiver(address)

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        self.sender.send(stream_id, data)

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        return self.receiver.recv()

    def close(self) -> None:
        """Close the QUIC connection."""

        self.sender.close()
        self.receiver.close()

    def server_handshake(self) -> None:
        """Perform the QUIC handshake from a server's view."""

        raise NotImplementedError()

    def client_handshake(self) -> None:
        """Perform the QUIC handshake from a client's view."""

        raise NotImplementedError()


class QUICMessageSender:
    def __init__(self, address: tuple[str, int]) -> None:
        """Initialize the QUIC message sender."""

        self.worker = Thread(target=self.worker_thread, args=(address,))
        self.message_queue: dict[int, list[bytes]] = {}

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        self.message_queue.setdefault(stream_id, []).append(data)

    def close(self):
        """Close the QUIC message sender."""

        self.worker.join()

    def worker_thread(self, address: tuple[str, int]) -> None:
        """The sender worker thread."""

        raise NotImplementedError()


class QUICMessageReceiver:
    def __init__(self, address: tuple[str, int]) -> None:
        """Initialize the QUIC message receiver."""

        self.worker = Thread(target=self.worker_thread, args=(address,))
        self.message_queue: dict[int, list[bytes]] = {}

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        raise NotImplementedError()

    def close(self):
        """Close the QUIC message receiver."""

        self.worker.join()

    def worker_thread(self, address: tuple[str, int]) -> None:
        """The receiver worker thread."""

        raise NotImplementedError()
