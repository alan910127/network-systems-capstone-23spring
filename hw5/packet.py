from __future__ import annotations

import ctypes
from dataclasses import asdict, dataclass
from enum import Enum, auto

from utils import get_colored_logger

logger = get_colored_logger("PACKET")


class QuicPacketType(Enum):
    Initial = auto()
    OneRTT = auto()

    def __repr__(self) -> str:
        return self.name


@dataclass
class QuicPacketHeader:
    packet_type: QuicPacketType
    packet_number: int

    class Struct(ctypes.BigEndianStructure):
        _fields_ = [
            ("packet_type", ctypes.c_uint8),
            ("packet_number", ctypes.c_uint32),
        ]

        def to_dict(self):
            return dict((field, getattr(self, field)) for field, _ in self._fields_)

    @classmethod
    def from_bytes(cls, data: bytes) -> QuicPacketHeader:
        obj = cls.Struct.from_buffer_copy(data)
        values = obj.to_dict()
        values["packet_type"] = QuicPacketType(values["packet_type"])
        return cls(**values)

    def to_bytes(self) -> bytes:
        values = asdict(self)
        values["packet_type"] = values["packet_type"].value
        obj = self.Struct(**values)
        return bytes(obj)

    @classmethod
    def size(cls) -> int:
        return ctypes.sizeof(cls.Struct)


class QuicFrameType(Enum):
    Ack = auto()
    Stream = auto()

    def __repr__(self) -> str:
        return self.name


@dataclass
class QuicFrameHeader:
    frame_type: QuicFrameType

    class Struct(ctypes.BigEndianStructure):
        _fields_ = [
            ("frame_type", ctypes.c_uint8),
        ]

        def to_dict(self):
            return dict((field, getattr(self, field)) for field, _ in self._fields_)

    @classmethod
    def from_bytes(cls, data: bytes) -> QuicFrameHeader:
        obj = cls.Struct.from_buffer_copy(data)
        values = obj.to_dict()
        values["frame_type"] = QuicFrameType(values["frame_type"])
        return cls(**values)

    def to_bytes(self) -> bytes:
        values = asdict(self)
        values["frame_type"] = values["frame_type"].value
        obj = self.Struct(**values)
        return bytes(obj)

    @classmethod
    def size(cls) -> int:
        return ctypes.sizeof(cls.Struct)


@dataclass
class QuicAckFrame:
    packet_number: int
    window_size: int

    class Struct(ctypes.BigEndianStructure):
        _fields_ = [
            ("packet_number", ctypes.c_uint32),
            ("window_size", ctypes.c_uint32),
        ]

        def to_dict(self):
            return dict((field, getattr(self, field)) for field, _ in self._fields_)

    @classmethod
    def from_bytes(cls, data: bytes) -> QuicAckFrame:
        obj = cls.Struct.from_buffer_copy(data)
        values = obj.to_dict()
        return cls(**values)

    def to_bytes(self) -> bytes:
        obj = self.Struct(**asdict(self))
        return bytes(obj)

    @classmethod
    def size(cls) -> int:
        return ctypes.sizeof(cls.Struct)


@dataclass
class QuicStreamFrame:
    stream_id: int
    offset: int
    length: int
    finished: bool
    data: bytes

    class Struct(ctypes.BigEndianStructure):
        _fields_ = [
            ("stream_id", ctypes.c_uint32),
            ("offset", ctypes.c_uint64),
            ("length", ctypes.c_uint16),
            ("finished", ctypes.c_uint8),
        ]

        def to_dict(self):
            return dict((field, getattr(self, field)) for field, _ in self._fields_)

    @classmethod
    def from_bytes(cls, data: bytes) -> QuicStreamFrame:
        obj = cls.Struct.from_buffer_copy(data)
        values = obj.to_dict()
        return cls(**values, data=data[cls.size() :])

    def to_bytes(self) -> bytes:
        obj = self.Struct(**asdict(self))
        return bytes(obj) + self.data

    @classmethod
    def size(cls) -> int:
        return ctypes.sizeof(cls.Struct)
