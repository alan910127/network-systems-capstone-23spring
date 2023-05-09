from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from threading import Thread

import utils
from packet import (
    QuicAckFrame,
    QuicFrameHeader,
    QuicFrameType,
    QuicPacketHeader,
    QuicPacketType,
    QuicStreamFrame,
)

RETRY_COUNT = 3
RECEIVE_SIZE = 650  # 650 packets, ~1MB
PACKET_SIZE = 1500  # 1.5KB
SSTHRESH = 64  # 64 packets
TIMEOUT = 1.0  # 1 second


logger = utils.get_colored_logger("QUIC_IMPL")


@dataclass
class SenderWindowEntry:
    packet_number: int
    frame: QuicStreamFrame
    sent_time: float


class QuicConnection:
    def __init__(
        self, sock: socket.socket, max_window_size: int, packet_number: int
    ) -> None:
        """Initialize the QUIC connection."""

        self.socket = sock
        self.is_closed = False
        self.max_window_size = max_window_size

        self.sender = Thread(target=self.sender_thread)
        self.receiver = Thread(target=self.receiver_thread)

        self.send_buffer: dict[int, list[QuicStreamFrame]] = {}
        self.sender_window_size = 4
        self.sender_window: list[SenderWindowEntry] = []
        self.ack_list: list[QuicAckFrame] = []
        self.exponential_growth = True
        self.packet_number = packet_number

        self.recv_buffer: dict[int, list[QuicStreamFrame]] = {}

        self.sender.start()
        self.receiver.start()

    def get_packet_number(self) -> int:
        """Get the next packet number."""

        packet_number = self.packet_number
        self.packet_number += 1
        return packet_number

    @classmethod
    def accept_one(cls, sock: socket.socket) -> tuple[QuicConnection, str, int] | None:
        """Accept a single QUIC connection on the given socket."""

        # accept the initial packet from the client
        data, addr = sock.recvfrom(PACKET_SIZE)
        if not data:
            return None

        header = QuicPacketHeader.from_bytes(data)
        if header.packet_type != QuicPacketType.Initial:
            logger.debug(f"Received a non-initial packet from {addr}")
            return None

        logger.debug(f"Received {header} from {addr}")

        # send an ACK packet to the client
        header = QuicPacketHeader(packet_type=QuicPacketType.Initial, packet_number=0)
        frame_header = QuicFrameHeader(frame_type=QuicFrameType.Ack)
        ack = QuicAckFrame(packet_number=header.packet_number, window_size=RECEIVE_SIZE)

        packet = header.to_bytes() + frame_header.to_bytes() + ack.to_bytes()
        sock.sendto(packet, addr)

        # receive the ACK packet from the clients
        data, addr = sock.recvfrom(PACKET_SIZE)
        if not data:
            return None

        header = QuicPacketHeader.from_bytes(data)
        if header.packet_type != QuicPacketType.Initial:
            logger.debug(f"Received a non-initial packet from {addr}")
            return None

        logger.debug(f"Received {header} from {addr}")

        frame_header = QuicFrameHeader.from_bytes(data[QuicPacketHeader.size() :])
        if frame_header.frame_type != QuicFrameType.Ack:
            logger.debug(f"Received a non-ack frame from {addr}")
            return None

        ack = QuicAckFrame.from_bytes(
            data[QuicPacketHeader.size() + QuicFrameHeader.size() :]
        )
        if ack.packet_number != header.packet_number:
            logger.debug(f"Received an ack for the wrong packet from {addr}")
            return None

        sock.connect(addr)

        return cls(sock, ack.window_size, 1), addr[0], addr[1]

    @classmethod
    def connect_to(cls, addr: tuple[str, int]) -> QuicConnection:
        """Connect to a QUIC server at the given address."""

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(addr)

        # send an initial packet to the server
        header = QuicPacketHeader(packet_type=QuicPacketType.Initial, packet_number=0)
        frame_header = QuicFrameHeader(frame_type=QuicFrameType.Ack)
        ack = QuicAckFrame(packet_number=header.packet_number, window_size=RECEIVE_SIZE)

        packet = header.to_bytes() + frame_header.to_bytes() + ack.to_bytes()
        sock.send(packet)

        # receive the ACK packet from the server
        data = sock.recv(PACKET_SIZE)
        if not data:
            raise RuntimeError("Failed to connect to the server")

        header = QuicPacketHeader.from_bytes(data)
        if header.packet_type != QuicPacketType.Initial:
            raise RuntimeError("Failed to connect to the server")

        logger.debug(f"Received {header} from {addr}")

        frame_header = QuicFrameHeader.from_bytes(data[QuicPacketHeader.size() :])
        if frame_header.frame_type != QuicFrameType.Ack:
            logger.fatal(f"Expected: ACK, Received: {frame_header} from {addr}")
            raise RuntimeError("Failed to connect to the server")

        ack = QuicAckFrame.from_bytes(
            data[QuicPacketHeader.size() + QuicFrameHeader.size() :]
        )
        if ack.packet_number != header.packet_number:
            raise RuntimeError("Failed to connect to the server")

        # send an ACK packet to the server
        header = QuicPacketHeader(packet_type=QuicPacketType.Initial, packet_number=1)
        frame_header = QuicFrameHeader(frame_type=QuicFrameType.Ack)
        ack = QuicAckFrame(packet_number=header.packet_number, window_size=RECEIVE_SIZE)

        packet = header.to_bytes() + frame_header.to_bytes() + ack.to_bytes()
        sock.send(packet)

        return cls(sock, ack.window_size, 2)

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        max_stream_size = (
            PACKET_SIZE
            - QuicPacketHeader.size()
            - QuicFrameHeader.size()
            - QuicStreamFrame.size()
        )

        # split the data into multiple packets
        frames: list[QuicStreamFrame] = []
        for i in range(0, len(data), max_stream_size):
            finished = i + max_stream_size >= len(data)
            frame = QuicStreamFrame(
                stream_id=stream_id,
                offset=i,
                length=len(data) - i if finished else max_stream_size,
                data=data[i : i + max_stream_size],
                finished=finished,
            )
            frames.append(frame)

        logger.debug(f"{frames=}")

        self.send_buffer[stream_id] = frames

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        while not self.is_closed:
            logger.debug(f"{self.recv_buffer=}")
            for stream_id, frames in self.recv_buffer.items():
                if len(frames) == 0:
                    continue

                logger.debug(f"{frames=} {stream_id=}")
                ordered_frames = sorted(frames, key=lambda f: f.offset)
                if not ordered_frames[-1].finished:
                    continue

                if ordered_frames[0].offset != 0:
                    continue

                # check if the frames are contiguous
                for i in range(len(ordered_frames) - 1):
                    if (
                        ordered_frames[i].offset + ordered_frames[i].length
                        != ordered_frames[i + 1].offset
                    ):
                        break

                # remove the frames from the receive buffer
                data = b"".join(f.data for f in ordered_frames)
                del self.recv_buffer[stream_id]

                return stream_id, data

            time.sleep(0.1)

        return -1, b""

    def close(self) -> None:
        """Close the connection and the socket."""

        logger.info("Closing the connection")

        self.is_closed = True
        self.sender.join()
        self.receiver.join()

    def sender_thread(self) -> None:
        """Thread that sends data on the socket."""

        while True:
            while len(self.sender_window) < self.sender_window_size:
                # move frames from the send buffer to the sender window
                has_frames = False
                send_buffer = self.send_buffer.copy()
                for frames in send_buffer.values():
                    if len(frames) == 0:
                        continue

                    if len(self.sender_window) >= self.sender_window_size:
                        break

                    entry = SenderWindowEntry(
                        packet_number=self.get_packet_number(),
                        frame=frames.pop(0),
                        sent_time=0,
                    )
                    self.sender_window.append(entry)
                    has_frames = True

                if not has_frames:
                    break

            has_loss = False
            for entry in self.sender_window:
                if time.time() - entry.sent_time <= TIMEOUT:
                    continue

                if entry.sent_time != 0:
                    has_loss = True

                entry.sent_time = time.time()

                # send the frame
                header = QuicPacketHeader(
                    packet_type=QuicPacketType.OneRTT,
                    packet_number=entry.packet_number,
                )
                frame_header = QuicFrameHeader(frame_type=QuicFrameType.Stream)

                packet = (
                    header.to_bytes() + frame_header.to_bytes() + entry.frame.to_bytes()
                )
                logger.debug(f"Sending {header.packet_number} {entry}")
                self.socket.send(packet)

            if has_loss:
                self.sender_window_size = max(1, self.sender_window_size // 2)
                self.exponential_growth = False

            # copy the ack list to avoid concurrent modification
            ack_list = self.ack_list.copy()
            if len(ack_list) > 0:
                logger.debug(f"{ack_list=}")
            for ack in ack_list:
                header = QuicPacketHeader(
                    packet_type=QuicPacketType.OneRTT,
                    packet_number=self.get_packet_number(),
                )
                frame_header = QuicFrameHeader(frame_type=QuicFrameType.Ack)
                packet = header.to_bytes() + frame_header.to_bytes() + ack.to_bytes()
                logger.debug(f"Sending {ack}")
                self.socket.send(packet)
                self.ack_list.remove(ack)

            if self.is_closed and len(self.ack_list) == 0:
                break

    def receiver_thread(self) -> None:
        """Thread that receives data on the socket."""

        self.socket.setblocking(False)
        while not self.is_closed:
            try:
                data = self.socket.recv(PACKET_SIZE)
            except BlockingIOError:
                continue
            except ConnectionRefusedError:
                self.is_closed = True
                return

            if not data:
                continue

            header = QuicPacketHeader.from_bytes(data)
            logger.debug(f"Received {header}")
            if header.packet_type == QuicPacketType.Initial:
                continue

            frame_header = QuicFrameHeader.from_bytes(data[QuicPacketHeader.size() :])

            if frame_header.frame_type == QuicFrameType.Ack:
                frame = QuicAckFrame.from_bytes(
                    data[QuicPacketHeader.size() + QuicFrameHeader.size() :]
                )
                logger.debug(f"Received {frame}")
                self.handle_ack(frame)

            elif frame_header.frame_type == QuicFrameType.Stream:
                frame = QuicStreamFrame.from_bytes(
                    data[QuicPacketHeader.size() + QuicFrameHeader.size() :]
                )
                logger.debug(f"Received {frame}")
                self.handle_stream(header.packet_number, frame)

    def handle_ack(self, ack: QuicAckFrame) -> None:
        """Handle an ACK frame."""

        logger.debug(f"ACK {ack.packet_number}")

        for i, packet in enumerate(self.sender_window):
            if packet.packet_number == ack.packet_number:
                break
        else:
            # packet number not found
            return
        logger.debug(f"Found at {i}: {packet}")

        self.sender_window.pop(i)
        if self.exponential_growth:
            self.sender_window_size *= 2
        else:
            self.sender_window_size += 1

        if self.sender_window_size > self.max_window_size:
            self.sender_window_size = self.max_window_size

        if self.sender_window_size > SSTHRESH:
            self.exponential_growth = False

    def handle_stream(self, packet_number: int, frame: QuicStreamFrame) -> None:
        """Handle a STREAM frame."""

        self.recv_buffer.setdefault(frame.stream_id, []).append(frame)

        # send an ACK frame
        ack = QuicAckFrame(packet_number=packet_number, window_size=RECEIVE_SIZE)
        self.ack_list.append(ack)
