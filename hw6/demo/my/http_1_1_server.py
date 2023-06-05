from __future__ import annotations

import contextlib
import random
import socket
import time
from pathlib import Path
from threading import Thread

from .utils import (
    STREAM_BLOCK_SIZE,
    Request,
    ResponseBuilder,
    get_colored_logger,
)

log = get_colored_logger("HTTP/1.1 Server")


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
        log.info(f"Listening on {self.socket.getsockname()}")
        self.socket.settimeout(1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.listen()

        while self.is_running:
            try:
                client_socket, addr = self.socket.accept()
            except socket.timeout:
                continue

            log.info(f"Accept a connection from {addr}")
            client_socket.settimeout(5)
            while self.is_running:
                if not self.handle(client_socket):
                    break

            with contextlib.suppress(OSError, socket.error):
                client_socket.close()


    def set_static(self, path: str) -> None:
        self.root_path = Path(path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self.is_running = False
        self.socket.close()

    def handle(self, client: socket.socket) -> bool:
        try:
            request = Request.from_socket(client)
        except socket.timeout:
            return True
        
        if request is None:
            log.warning(f"Connection closed by {client.getpeername()}")
            return False

        log.info(f"Request: {request.method} {request.resource} {request.version}")
        path, _query = (
            request.resource.split("?", 1)
            if "?" in request.resource
            else (
                request.resource,
                "",
            )
        )

        if request.method == "GET" and path in ("", "/"):
            handler = self.get_file_list_handler
        elif request.method == "GET" and path.startswith("/static/"):
            handler = self.get_file_handler
        else:
            handler = self.not_found_handler

        start = time.perf_counter()
        handler(client, request)
        end = time.perf_counter()
        log.info(f"{request.method} {request.resource} {end - start:.2f}s")

        return True

    def get_file_list_handler(self, client: socket.socket, _: Request) -> None:
        all_files = list(self.root_path.iterdir())
        file_list = random.sample(all_files, 3)

        file_links_html = "<br />".join(
            f'<a href="/static/{file.name}">{file.name}</a>' for file in file_list
        )

        body = f"<html><header></header><body>{file_links_html}</body></html>"

        response = (
            ResponseBuilder()
            .set_status_code(200)
            .set_header("Content-Type", "text/html")
            .set_body(body.encode())
            .build()
        )

        client.sendall(response)

    def get_file_handler(self, client: socket.socket, request: Request) -> None:
        file_path = self.root_path / request.resource.lstrip("/static")

        if not file_path.exists():
            self.not_found_handler(client, request)
            return

        file_size = file_path.stat().st_size

        with file_path.open("rb") as f:
            first_chunk = f.read(STREAM_BLOCK_SIZE)
            bytes_sent = len(first_chunk)
            response = (
                ResponseBuilder()
                .set_status_code(200)
                .set_header("Content-Type", "text/plain")
                .set_header("Content-Length", str(file_size))
                .set_body_chunked(first_chunk)
                .build()
            )
            client.sendall(response)

            while bytes_sent < file_size:
                chunk = f.read(STREAM_BLOCK_SIZE)
                bytes_sent += len(chunk)
                client.sendall(chunk)

    def not_found_handler(self, client: socket.socket, _: Request) -> None:
        response = ResponseBuilder().set_status_code(404).build()
        client.sendall(response)
