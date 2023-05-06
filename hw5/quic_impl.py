from __future__ import annotations

import socket
import time
from threading import Thread

import utils
from packet import (QuicAckFrame, QuicFrameHeader, QuicInitialPacket,
                    QuicPacketBuilder, QuicPacketHeader)
from utils import DataParser

RETRY_COUNT = 3
RECEIVE_SIZE = 1500


logger = utils.get_colored_logger("QUIC_IMPL")


class QuicConnection:
    def __init__(self, sock: socket.socket) -> None:
        """Initialize the QUIC connection."""

        self.socket = sock
        self.is_closed = False

        self.sender = Thread(target=self.sender_thread)
        self.receiver = Thread(target=self.receiver_thread)

        self.sender.start()
        self.receiver.start()

        self.send_buffer: dict[int, bytes] = {}
        self.recv_buffer: dict[int, bytes] = {}

    @classmethod
    def accept_one(cls, sock: socket.socket) -> tuple[QuicConnection, str, int] | None:
        """Accept a single QUIC connection on the given socket."""

        data, addr = sock.recvfrom(RECEIVE_SIZE)
        parser = DataParser(data)

        header = parser.parse(QuicPacketHeader)
        if not header.is_initial():
            logger.warn("Received invalid packet type")
            return None

        client_hello = parser.consume(QuicInitialPacket)
        logger.debug(f"Received {client_hello!r} from {addr}")

        server_hello = (
            QuicPacketBuilder.initial(packet_id=0)
            .chain(QuicFrameHeader.ack())
            .chain(QuicAckFrame(window_size=RECEIVE_SIZE))
            .build()
        )

        for _ in range(RETRY_COUNT):
            n = sock.sendto(server_hello, addr)
            logger.debug(f"Sent {n} bytes to {addr}")

            data, addr = sock.recvfrom(RECEIVE_SIZE)
            parser = DataParser(data)

            header = parser.consume(QuicPacketHeader)
            if not header.is_initial():
                logger.warn("Received invalid packet type")
                continue

            frame = parser.consume(QuicFrameHeader)
            if not frame.is_ack():
                logger.warn("Received invalid ack")
                continue

            ack = parser.consume(QuicAckFrame)
            logger.debug(f"Received {ack!r} from {addr}")

            return cls(sock), *addr

        logger.error("Failed to establish connection")
        return None

    @classmethod
    def connect_to(cls, addr: tuple[str, int]) -> QuicConnection:
        """Connect to a QUIC server at the given address."""

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(addr)
        sock.settimeout(1)

        client_hello = (
            QuicPacketBuilder.initial(packet_id=0)
            .chain(QuicFrameHeader.ack())
            .chain(QuicAckFrame(window_size=RECEIVE_SIZE))
            .build()
        )

        for _ in range(RETRY_COUNT):
            try:
                sock.send(client_hello)

                data = sock.recv(RECEIVE_SIZE)
                parser = DataParser(data)
                header = parser.parse(QuicPacketHeader)
                logger.debug(f"Received {header!r}")
                if not header.is_initial():
                    logger.warn("Received invalid packet type, retrying...")
                    continue

                server_hello = parser.consume(QuicInitialPacket)
                logger.debug(f"Received {server_hello!r}")

                frame_header = parser.consume(QuicFrameHeader)
                if not frame_header.is_ack():
                    logger.warn("Received invalid ack, retrying...")
                    continue

                server_ack = parser.consume(QuicAckFrame)
                server_window_size = server_ack.window_size
                logger.debug(f"{server_window_size=}")

                ack = (
                    QuicPacketBuilder.initial(packet_id=0)
                    .chain(QuicFrameHeader.ack())
                    .chain(QuicAckFrame(window_size=RECEIVE_SIZE))
                    .build()
                )

                sock.send(ack)

                return cls(sock)

            except TimeoutError:
                logger.debug("Timeout, retrying...")
                time.sleep(1)

        logger.error("Failed to establish connection")
        raise RuntimeError("Failed to establish connection")

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        self.send_buffer[stream_id] = self.send_buffer.get(stream_id, b"") + data

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
