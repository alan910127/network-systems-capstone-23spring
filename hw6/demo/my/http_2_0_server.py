from __future__ import annotations

import random
import socket
from pathlib import Path
from threading import Thread

from .http_2_utils import HttpFrameFlag, HttpFrameHeader, HttpFrameType
from .utils import STREAM_BLOCK_SIZE, get_colored_logger

log = get_colored_logger("HTTP/2.0 Server")


class HTTPServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.is_running = False
        self.root_path = Path.cwd()

    def run(self) -> None:
        thread = Thread(target=self.run_impl)
        self.is_running = True
        thread.start()

    def run_impl(self) -> None:
        self.socket.settimeout(1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.listen()
        log.info(f"Listening on {self.socket.getsockname()}")

        while self.is_running:
            try:
                client_socket, addr = self.socket.accept()
            except socket.timeout:
                continue

            log.info(f"Accept a connection from {addr}")
            while True:
                try:
                    self.handle(client_socket)
                except socket.timeout:
                    client_socket.close()
                    break

    def set_static(self, path: str) -> None:
        self.root_path = Path(path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self.is_running = False
        self.socket.close()

    def handle(self, client: socket.socket) -> None:
        header = client.recv(HttpFrameHeader.size())
        if len(header) < HttpFrameHeader.size():
            return

        header = HttpFrameHeader.from_bytes(header)

        data = bytearray()
        while len(data) < header.payload_length:
            chunk_size = min(STREAM_BLOCK_SIZE, header.payload_length - len(data))
            chunk = client.recv(chunk_size)
            data.extend(chunk)

        if header.type == HttpFrameType.Headers:
            headers = data.decode()
            log.info(f"Request: {headers!r}")

            method: str | None = None
            path: str | None = None

            for header_raw in headers.split("\r\n"):
                key, value = header_raw.split(": ", 1)
                if key == ":path":
                    path = value
                elif key == ":method":
                    method = value

            if method is None or path is None:
                return

            if method == "GET" and path in ("", "/"):
                handler = self.get_file_list_handler
            elif method == "GET" and path.startswith("/static"):
                handler = self.get_file_handler
            else:
                handler = self.not_found_handler

            handler(client, path, header.stream_id)

    def get_file_list_handler(self, client: socket.socket, _: str, stream_id: int):
        all_files = list(self.root_path.iterdir())
        file_list = random.sample(all_files, 3)

        file_links_html = "<br />".join(
            f'<a href="/static/{file.name}">{file.name}</a>' for file in file_list
        )

        body = f"<html><header></header><body>{file_links_html}</body></html>"

        response_header = b":status: 200\r\ncontent-type: text/html\r\n"
        response_body = body.encode()

        header_frame = HttpFrameHeader(
            payload_length=len(response_header),
            type=HttpFrameType.Headers,
            flag=HttpFrameFlag.Default,
            stream_id=stream_id,
        )
        body_frame = HttpFrameHeader(
            payload_length=len(response_body),
            type=HttpFrameType.Data,
            flag=HttpFrameFlag.EndStream,
            stream_id=stream_id,
        )

        response = b"".join(
            [
                header_frame.to_bytes(),
                response_header,
                body_frame.to_bytes(),
                response_body,
            ]
        )

        client.sendall(response)

    def get_file_handler(self, client: socket.socket, path: str, stream_id: int):
        file_path = self.root_path / path.lstrip("/static")

        if not file_path.exists():
            return self.not_found_handler(client, path, stream_id)

        response_header = b":status: 200\r\ncontent-type: text/plain\r\n"
        header_frame = HttpFrameHeader(
            payload_length=len(response_header),
            type=HttpFrameType.Headers,
            flag=HttpFrameFlag.Default,
            stream_id=stream_id,
        )
        client.sendall(header_frame.to_bytes() + response_header)

        bytes_sent = 0
        file_size = file_path.stat().st_size
        with file_path.open("rb") as f:
            while bytes_sent < file_size:
                is_end = bytes_sent + STREAM_BLOCK_SIZE >= file_size
                chunk = f.read(STREAM_BLOCK_SIZE)
                body_frame = HttpFrameHeader(
                    payload_length=len(chunk),
                    type=HttpFrameType.Data,
                    flag=HttpFrameFlag.EndStream if is_end else HttpFrameFlag.Default,
                    stream_id=stream_id,
                )
                client.sendall(body_frame.to_bytes() + chunk)
                bytes_sent += len(chunk)            

    def not_found_handler(self, client: socket.socket, _: str, stream_id: int):
        response_header = b":status: 404\r\n"
        header_frame = HttpFrameHeader(
            payload_length=len(response_header),
            type=HttpFrameType.Headers,
            flag=HttpFrameFlag.EndStream,
            stream_id=stream_id,
        )
        client.sendall(header_frame.to_bytes() + response_header)
