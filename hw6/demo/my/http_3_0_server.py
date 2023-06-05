from __future__ import annotations

import random
import time
from pathlib import Path
from threading import Thread

from QUIC.quic_server import QUICServer

from .http_3_utils import HttpFrameHeader, HttpFrameType
from .utils import STREAM_BLOCK_SIZE, get_colored_logger

log = get_colored_logger("HTTP/3.0 Server")


class HTTPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.server = QUICServer()
        self.address = (host, port)
        self.root_path = Path.cwd()

        self.thread: Thread | None = None
        self.is_running = False
        self.streams: dict[int, bytearray] = {}

    def run(self):
        self.thread = Thread(target=self.run_impl)
        self.is_running = True
        self.thread.start()

    def run_impl(self) -> None:
        self.server.listen(self.address)  # type: ignore
        log.info(f"Listening on {self.address}")

        self.server.accept()
        log.info("Accepting new connection")
        while self.is_running:
            stream_id, data, is_end = self.server.recv()  # type: ignore
            if not isinstance(data, bytes) or not isinstance(stream_id, int):
                continue

            log.info(f"Received {len(data)} bytes from stream {stream_id}")

            self.streams.setdefault(stream_id, bytearray()).extend(data)

            if not is_end:
                continue

            data = bytes(self.streams.pop(stream_id))
            header = HttpFrameHeader.from_bytes(data[: HttpFrameHeader.size()])

            if header.type == HttpFrameType.Headers:
                headers = data[HttpFrameHeader.size() :].decode()
                print(f"Request: {headers!r}")

                method: str | None = None
                path: str | None = None

                for header_raw in headers.split("\r\n"):
                    key, value = header_raw.split(": ", 1)
                    if key == ":path":
                        path = value
                    elif key == ":method":
                        method = value

                if method is None or path is None:
                    continue

                log.info(f"Request: {method} {path}")

                if method == "GET" and path in ("", "/"):
                    handler = self.get_file_list_handler
                elif method == "GET" and path.startswith("/static"):
                    handler = self.get_file_handler
                else:
                    handler = self.not_found_handler

                start = time.perf_counter()
                handler(stream_id, path)
                end = time.perf_counter()

                log.info(f"Request: {method} {path} took {end - start:.3f}s")

    def set_static(self, path: str) -> None:
        self.root_path = Path(path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self.server.close()  # type: ignore

    def get_file_list_handler(self, stream_id: int, _: str) -> None:
        all_files = list(self.root_path.iterdir())
        file_list = random.sample(all_files, 3)

        file_links_html = "<br />".join(
            f'<a href="/static/{file.name}">{file.name}</a>' for file in file_list
        )

        body = f"<html><header></header><body>{file_links_html}</body></html>"

        response_header = b":status: 200\r\ncontent-type: text/html\r\n\r\n"
        response_body = body.encode()

        header_frame = HttpFrameHeader(
            type=HttpFrameType.Headers,
            length=len(response_header),
        )

        body_frame = HttpFrameHeader(
            type=HttpFrameType.Data,
            length=len(response_body),
        )

        response = b"".join(
            [
                header_frame.to_bytes(),
                response_header,
                body_frame.to_bytes(),
                response_body,
            ]
        )

        self.server.send(stream_id, response, end=True)  # type: ignore

    def get_file_handler(self, stream_id: int, path: str) -> None:
        file_path = self.root_path / path.lstrip("/static")

        if not file_path.exists():
            self.not_found_handler(stream_id, path)
            return

        response_header = b":status: 200\r\ncontent-type: text/plain\r\n"
        header_frame = HttpFrameHeader(
            type=HttpFrameType.Headers,
            length=len(response_header),
        )
        self.server.send(  # type: ignore
            stream_id,
            header_frame.to_bytes() + response_header,
        )

        bytes_sent = 0
        file_size = file_path.stat().st_size
        with file_path.open("rb") as f:
            while bytes_sent < file_size:
                chunk = f.read(STREAM_BLOCK_SIZE)
                body_frame = HttpFrameHeader(
                    type=HttpFrameType.Data,
                    length=len(chunk),
                )
                self.server.send(  # type: ignore
                    stream_id,
                    body_frame.to_bytes() + chunk,
                    end=bytes_sent + len(chunk) >= file_size,
                )
                bytes_sent += len(chunk)

    def not_found_handler(self, stream_id: int, path: str) -> None:
        response_header = b":status: 404\r\n"
        header_frame = HttpFrameHeader(
            type=HttpFrameType.Headers,
            length=len(response_header),
        )
        self.server.send(  # type: ignore
            stream_id,
            header_frame.to_bytes() + response_header,
            end=True,
        )
