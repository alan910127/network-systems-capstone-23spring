from __future__ import annotations

import socket
import time
from collections import deque
from threading import Thread
from urllib.parse import urlparse

from .http_2_utils import HttpFrameFlag, HttpFrameHeader, HttpFrameType
from .utils import STREAM_BLOCK_SIZE, get_colored_logger

log = get_colored_logger("HTTP/2.0 Client")

OK = "OK"
NOT_YET = "Not yet"


class HTTPClient:
    def __init__(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream_id = 1
        self.responses: dict[int, Response] = {}
        self.is_receiving = False
        self.worker = Thread(target=self.receive_worker)

    def get(self, url: str, headers: dict[str, str] | None = None) -> Response:
        components = urlparse(url, scheme="http")
        log.info(f"GET {components.path} {components.query}")

        request_headers: list[tuple[str, str]] = [
            (":method", "GET"),
            (":path", components.path),
            (":scheme", "http"),
            (":authority", components.netloc or "localhost"),
        ]

        if headers is not None:
            for key, value in headers.items():
                request_headers.append((key, value))

        byte_headers = "\r\n".join(
            f"{key}: {value}" for key, value in request_headers
        ).encode()

        frame_header = HttpFrameHeader(
            payload_length=len(byte_headers),
            type=HttpFrameType.Headers,
            flag=HttpFrameFlag.EndStream,
            stream_id=self.stream_id,
        )
        self.stream_id += 2

        try:
            self.socket.sendall(frame_header.to_bytes() + byte_headers)
        except BrokenPipeError:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((components.hostname, components.port or 80))
            self.socket.sendall(frame_header.to_bytes() + byte_headers)

        if not self.is_receiving:
            self.is_receiving = True
            self.worker.start()

        response = Response(self.stream_id - 2)
        self.responses[response.stream_id] = response

        return response

    def receive_worker(self):
        self.socket.settimeout(5)
        while self.is_receiving:
            try:
                data = self.socket.recv(HttpFrameHeader.size())
                if len(data) < HttpFrameHeader.size():
                    continue
                header = HttpFrameHeader.from_bytes(data)
            except socket.timeout:
                self.is_receiving = False
                break

            payload = bytearray()
            while len(payload) < header.payload_length:
                receive_size = min(
                    STREAM_BLOCK_SIZE, header.payload_length - len(payload)
                )
                payload += self.socket.recv(receive_size)

            if header.flags == HttpFrameFlag.EndStream:
                self.responses[header.stream_id].complete = True

            if header.type == HttpFrameType.Headers:
                payload = bytes(payload).decode()

                for header_line in payload.split("\r\n"):
                    if not header_line:
                        continue
                    log.info(f"Header: {header_line}")
                    key, value = header_line.split(": ")
                    self.responses[header.stream_id].headers[key] = value

                self.responses[header.stream_id].status = "OK"
                continue

            self.responses[header.stream_id].contents.append(payload)


class Response:
    def __init__(
        self,
        stream_id: int,
        headers: dict[str, str] | None = None,
        status: str = NOT_YET,
    ) -> None:
        self.stream_id = stream_id
        self.headers = headers or {}

        self.status = status
        self.body = b""

        self.contents: deque[bytes] = deque()
        self.complete = False

    def get_headers(self) -> dict[str, str] | None:
        begin_time = time.time()
        while self.status == NOT_YET:
            if time.time() - begin_time > 5:
                return None
        return self.headers

    def get_full_body(self) -> bytes | None:
        begin_time = time.time()
        while not self.complete:
            if time.time() - begin_time > 5:
                return None

        if len(self.body) > 0:
            return self.body

        while len(self.contents) > 0:
            self.body += self.contents.popleft()

        return self.body

    def get_stream_content(self) -> bytes | None:
        begin_time = time.time()
        while len(self.contents) == 0:
            if self.complete or time.time() - begin_time > 5:
                return None

        return self.contents.popleft()
