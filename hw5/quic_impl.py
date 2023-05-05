from __future__ import annotations

import logging
import os
import socket
import time
from threading import Thread

RETRY_COUNT = 3

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="[%(levelname)s] %(name)s: %(message)s",
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


logger = logging.getLogger("QUIC_IMPL")


class QUICConnection:
    def __init__(self, sock: socket.socket) -> None:
        """Initialize the QUIC connection."""

        self.socket = sock
        self.is_closed = False

        self.sender = Thread(target=self.sender_thread)
        self.receiver = Thread(target=self.receiver_thread)

        self.sender.start()
        self.receiver.start()

    @classmethod
    def accept_one(cls, sock: socket.socket) -> tuple[QUICConnection, str, int] | None:
        """Accept a single QUIC connection on the given socket."""

        data, addr = sock.recvfrom(1024)
        logger.debug(f"Received {data!r} from {addr}")

        for _ in range(RETRY_COUNT):
            n = sock.sendto(b"HELLO", addr)
            logger.debug(f"Sent {n} bytes to {addr}")

            data, addr = sock.recvfrom(1024)
            logger.debug(f"Received {data!r} from {addr}")

            if data == b"ACK":
                break
        else:
            logger.error("Failed to establish connection")
            return None

        return cls(sock), *addr

    @classmethod
    def connect_to(cls, addr: tuple[str, int]) -> QUICConnection:
        """Connect to a QUIC server at the given address."""

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(addr)
        sock.settimeout(1)

        for _ in range(RETRY_COUNT):
            try:
                sock.send(b"HELLO")

                data = sock.recv(1024)
                logger.debug(f"Received {data!r}")
            except TimeoutError:
                logger.debug("Timeout, retrying...")
                time.sleep(1)
            else:
                break
        else:
            logger.error("Failed to establish connection")
            raise RuntimeError("Failed to establish connection")

        sock.send(b"ACK")

        return cls(sock)

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        raise NotImplementedError("todo")

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        raise NotImplementedError("todo")

    def close(self) -> None:
        """Close the connection and the socket."""

        self.is_closed = True
        self.sender.join()
        self.receiver.join()

    def sender_thread(self) -> None:
        """Thread that sends data on the socket."""

        while not self.is_closed:
            raise NotImplementedError("todo")

    def receiver_thread(self) -> None:
        """Thread that receives data on the socket."""

        while not self.is_closed:
            raise NotImplementedError("todo")
