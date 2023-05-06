from __future__ import annotations

import ctypes
from enum import Enum, auto

from utils import ReprBuilder, annotated_struct, get_colored_logger

logger = get_colored_logger("PACKET")


class QuicPacketType(Enum):
    Initial = auto()
    OneRtt = auto()

    def __repr__(self) -> str:
        return self.name.split(".")[-1]


class QuicFrameType(Enum):
    Ack = auto()
    Stream = auto()


class CStruct(ctypes.BigEndianStructure):
    def __repr__(self) -> str:
        builder = ReprBuilder(self.__class__.__name__)

        for field, _ in self._fields_:
            builder.field(field, getattr(self, field))

        return builder.finish()


class QuicPacketBuilder:
    def __init__(self) -> None:
        self.buffer = bytearray()

    @classmethod
    def initial(cls, packet_id: int) -> QuicPacketBuilder:
        builder = cls()
        builder.buffer.extend(bytes(QuicPacketHeader.initial(packet_id)))
        return builder

    @classmethod
    def one_rtt(cls, packet_id: int) -> QuicPacketBuilder:
        builder = cls()
        builder.buffer.extend(bytes(QuicPacketHeader.one_rtt(packet_id)))
        return builder

    def chain(self, data: bytes | ctypes.BigEndianStructure) -> QuicPacketBuilder:
        self.buffer.extend(bytes(data))
        return self

    def build(self) -> bytes:
        return bytes(self.buffer)


@annotated_struct
class QuicPacketHeader(CStruct):
    packet_type: ctypes.c_uint8
    packet_id: ctypes.c_uint32

    def is_initial(self) -> bool:
        return self.packet_type == QuicPacketType.Initial.value  # type: ignore

    def is_one_rtt(self) -> bool:
        return self.packet_type == QuicPacketType.OneRtt.value  # type: ignore

    def chain(self, data: bytes | ctypes.BigEndianStructure) -> bytes:
        return bytes(self) + bytes(data)

    @classmethod
    def initial(cls, packet_id: int) -> QuicPacketHeader:
        return cls(packet_type=QuicPacketType.Initial.value, packet_id=packet_id)

    @classmethod
    def one_rtt(cls, packet_id: int) -> QuicPacketHeader:
        return cls(packet_type=QuicPacketType.OneRtt.value, packet_id=packet_id)


@annotated_struct
class QuicInitialPacket(CStruct):
    packet_header: QuicPacketHeader


@annotated_struct
class QuicFrameHeader(CStruct):
    type: ctypes.c_uint8

    def is_ack(self) -> bool:
        return self.type == QuicFrameType.Ack.value  # type: ignore

    def is_stream(self) -> bool:
        return self.type == QuicFrameType.Stream.value  # type: ignore

    def chain(self, data: bytes | ctypes.BigEndianStructure) -> bytes:
        return bytes(self) + bytes(data)

    @classmethod
    def ack(cls) -> QuicFrameHeader:
        return cls(type=QuicFrameType.Ack.value)

    @classmethod
    def stream(cls) -> QuicFrameHeader:
        return cls(type=QuicFrameType.Stream.value)


@annotated_struct
class QuicAckFrame(CStruct):
    window_size: ctypes.c_uint32


@annotated_struct
class QuicAckPacket(CStruct):
    packet_header: QuicPacketHeader
    frame_header: QuicFrameHeader
    ack: QuicAckFrame


@annotated_struct
class QuicStreamFrame(CStruct):
    ...


@annotated_struct
class QuicStreamPacket(CStruct):
    packet_header: QuicPacketHeader
    frame_header: QuicFrameHeader
    ack: ctypes.c_uint32
    ack: ctypes.c_uint32
