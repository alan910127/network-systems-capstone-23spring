from __future__ import annotations

import ctypes
import logging
import os
import socket
from threading import Event, Thread
from typing import Callable

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


class HandshakePacket(ctypes.BigEndianStructure):
    _fields_ = [
        ("window_size", ctypes.c_uint32),
    ]


def get_window_size(data: bytes) -> int:
    return HandshakePacket.from_buffer_copy(data).window_size


class QUICConnectionBuilder:
    def __init__(self):
        """Initialize the QUIC connection builder."""

        self.address: tuple[str, int] | None = None
        self.send_window_size: int | None = None
        self.sock: socket.socket | None = None
        self.receive_window_size = 1500  # default to 1500, can be overwritten

    def set_peer_address(self, address: tuple[str, int]) -> QUICConnectionBuilder:
        """Set the peer address."""

        self.address = address
        return self

    def set_send_window_size(self, size: int) -> QUICConnectionBuilder:
        """Set the send window size."""

        self.send_window_size = size
        return self

    def set_socket(self, sock: socket.socket) -> QUICConnectionBuilder:
        """Set the socket."""

        self.sock = sock
        return self

    def set_receive_window_size(self, size: int) -> QUICConnectionBuilder:
        """Set the receive window size."""

        self.receive_window_size = size
        return self

    def with_server_handshake(
        self, sock: socket.socket
    ) -> tuple[QUICConnection, str, int]:
        """Perform the QUIC handshake from a server's view."""

        # Receive the initial packet from the client
        data, client_address = sock.recvfrom(self.receive_window_size)
        client_receive_size = get_window_size(data)
        logger.debug(f"{client_receive_size=}")

        sock.settimeout(1.0)
        # Try to send the initial packet to the client until it is received
        while True:
            try:
                # Send the initial packet to the client
                packet = HandshakePacket(window_size=self.receive_window_size)
                sock.sendto(bytes(packet), client_address)

                # Receive the ACK packet from the client
                data = sock.recv(self.receive_window_size)
                if data == b"ACK\n":
                    break
            except TimeoutError:
                logger.debug("Handshake timeout, retrying...")

        sock.settimeout(None)

        return (
            self.set_send_window_size(client_receive_size)
            .set_socket(sock)
            .set_peer_address(client_address)
            .build(),
            client_address[0],
            client_address[1],
        )

    def with_client_handshake(self) -> QUICConnection:
        """Perform the QUIC handshake from a client's view."""

        if self.address is None:
            raise ValueError("The peer address must be set")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send the initial packet to the server
        packet = HandshakePacket(window_size=self.receive_window_size)
        sock.sendto(bytes(packet), self.address)

        # Receive the initial packet from the server
        data = sock.recv(self.receive_window_size)
        server_receive_size = get_window_size(data)
        logger.debug(f"{server_receive_size=}")

        # Send the ACK packet to the server
        n = sock.sendto(b"ACK\n", self.address)
        logger.debug(f"{n=}")

        return (
            self.set_send_window_size(server_receive_size)
            .set_socket(sock)
            .set_peer_address(self.address)
            .build()
        )

    def build(self) -> QUICConnection:
        """Build the QUIC connection."""

        if self.address is None:
            raise ValueError("Peer address is not set")
        if self.send_window_size is None:
            raise ValueError("Send window size is not set")
        if self.sock is None:
            raise ValueError("Socket is not set")

        return QUICConnection(
            self.sock,
            self.address,
            self.receive_window_size,
            self.send_window_size,
        )


class QUICConnection:
    def __init__(
        self,
        sock: socket.socket,
        peer_address: tuple[str, int],
        receive_window_size: int,
        send_window_size: int,
    ) -> None:
        """Initialize the QUIC connection."""

        self.peer_address = peer_address
        self.sender = QUICMessageSender(sock, peer_address, send_window_size)
        self.receiver = QUICMessageReceiver(sock, peer_address, receive_window_size)

    @staticmethod
    def builder() -> QUICConnectionBuilder:
        """Create a new QUIC connection builder."""

        return QUICConnectionBuilder()

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


class QUICMessageWorker:
    def __init__(self, workhorse: Callable[[Callable[[], bool]], None]) -> None:
        """Initialize the QUIC message worker."""

        self.worker = Thread(target=workhorse, args=(self.is_stopped,))
        self.stop_event = Event()

    def stop(self) -> None:
        """Stop the QUIC message worker."""

        self.stop_event.set()
        self.worker.join()

    def is_stopped(self) -> bool:
        """Check if the QUIC message worker is stopped."""

        return self.stop_event.is_set()


class QUICMessageSender:
    def __init__(
        self, sock: socket.socket, address: tuple[str, int], send_window_size: int
    ) -> None:
        """Initialize the QUIC message sender."""

        self.sock = sock
        self.address = address
        self.send_window_size = send_window_size
        self.worker = QUICMessageWorker(self.workhorse)
        self.message_queue: dict[int, list[bytes]] = {}

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        self.message_queue.setdefault(stream_id, []).append(data)

    def close(self):
        """Close the QUIC message sender."""

        self.worker.stop()

    def workhorse(self, is_stopped: Callable[[], bool]) -> None:
        """The sender workhorse"""

        while not is_stopped():
            raise NotImplementedError()


class QUICMessageReceiver:
    def __init__(
        self, sock: socket.socket, address: tuple[str, int], receive_window_size: int
    ) -> None:
        """Initialize the QUIC message receiver."""

        self.sock = sock
        self.address = address
        self.receive_window_size = receive_window_size
        self.worker = QUICMessageWorker(self.workhorse)
        self.message_queue: dict[int, list[bytes]] = {}

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        raise NotImplementedError()

    def close(self):
        """Close the QUIC message receiver."""

        self.worker.stop()

    def workhorse(self, is_stopped: Callable[[], bool]) -> None:
        """The receiver workhorse."""

        while not is_stopped():
            raise NotImplementedError()
