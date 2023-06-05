from __future__ import annotations

import socket
from urllib.parse import urlparse

from .utils import RequestBuilder, Response, get_colored_logger

log = get_colored_logger("HTTP/1.0 Client")


class HTTPClient:
    def __init__(self) -> None:
        """Create a HTTP client."""

    def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        stream: bool = False,
    ) -> Response:
        components = urlparse(url, scheme="http")
        log.info(f"GET {components.path} {components.query}")
        builder = (
            RequestBuilder()
            .set_method("GET")
            .set_resource(components.path, components.query)
            .set_version("HTTP/1.0")
        )

        if headers is not None:
            for key, value in headers.items():
                builder.set_header(key, value)

        request = builder.build()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((components.hostname, components.port or 80))
        sock.sendall(request)

        response = Response(sock, stream)
        response.parse_header()

        return response

