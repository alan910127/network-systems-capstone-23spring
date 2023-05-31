from __future__ import annotations

import time
from collections import deque
from threading import Thread
from urllib.parse import urlparse

from QUIC.quic_client import QUICClient

from .http_3_utils import HttpFrameHeader, HttpFrameType
from .utils import get_colored_logger

log = get_colored_logger("HTTP/3.0 Client")

OK = "Ok"
NOT_YET = "Not yet"


class HTTPClient:
    def __init__(self) -> None:
        self.client = QUICClient()
        self.stream_id = 1
        self.responses: dict[int, Response] = {}

        self.worker = Thread(target=self.receive_worker)
        self.is_receiving = False

    def get(self, url: str, headers: dict[str, str] | None = None) -> Response:
        components = urlparse(url, scheme="http")
        log.info(f"GET {components.path} {components.query}")
        self.client.connect(  # type: ignore
            (components.hostname, components.port or 80)
        )

        request_headers: list[tuple[str, str]] = [
            (":method", "GET"),
            (":path", components.path),
            (":scheme", "http"),
            (":authority", components.netloc or "localhost"),
        ]

        if headers is not None:
            request_headers.extend(headers.items())

        byte_headers = "\r\n".join(
            f"{key}: {value}" for key, value in request_headers
        ).encode()

        frame_header = HttpFrameHeader(
            type=HttpFrameType.Headers,
            length=len(byte_headers),
        )
        self.client.send(  # type: ignore
            self.stream_id,
            frame_header.to_bytes() + byte_headers,
            end=True,
        )

        if not self.is_receiving:
            self.is_receiving = True
            self.worker.start()

        response = Response(self.stream_id)
        self.responses[self.stream_id] = response
        self.stream_id += 2

        return response

    def receive_worker(self) -> None:
        while self.is_receiving:
            stream_id, data, is_end = self.client.recv()  # type: ignore

            if not isinstance(data, bytes) or not isinstance(stream_id, int):
                continue

            if len(data) < HttpFrameHeader.size():
                continue

            response = self.responses.setdefault(stream_id, Response(stream_id))
            header = HttpFrameHeader.from_bytes(data[: HttpFrameHeader.size()])
            data = data[HttpFrameHeader.size() :]
            if header.type == HttpFrameType.Headers:
                payload = data[: header.length].decode()
                for header_lilne in payload.split("\r\n"):
                    if header_lilne == "":
                        continue
                    key, value = header_lilne.split(": ")
                    response.headers[key] = value

                response.status = OK
                data = data[header.length :]

                header = HttpFrameHeader.from_bytes(data[: HttpFrameHeader.size()])
                data = data[HttpFrameHeader.size() :]

            if header.type == HttpFrameType.Data:
                response.contents.append(data)
                if is_end:
                    response.complete = True


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

        log.info(f"{self.body=}")
        return self.body

    def get_stream_content(self) -> bytes | None:
        begin_time = time.time()
        while len(self.contents) == 0:
            if self.complete or time.time() - begin_time > 5:
                return None

        return self.contents.popleft()
