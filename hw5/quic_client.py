import logging
import socket

from quic_impl import Connection

logger = logging.getLogger("quic_client")


class QUICClient:
    def __init__(self):
        """Initialize the QUIC client."""

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connection: Connection | None = None

    def connect(self, socket_addr: tuple[str, int]) -> None:
        """Connect to a QUIC server on the given socket address."""

        self.connection = Connection(socket_addr)
        self.connection.client_handshake()
        logger.info(f"Connected to {socket_addr[0]}:{socket_addr[1]}")

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        if self.connection is None:
            raise RuntimeError("No server connected")

        self.connection.send(stream_id, data)

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream."""

        if self.connection is None:
            raise RuntimeError("No server connected")

        return self.connection.recv()

    def close(self) -> None:
        """Close the connection and the socket."""

        if self.connection is not None:
            self.connection.close()

        self.socket.close()


def main():
    client = QUICClient()
    client.connect(("127.0.0.1", 30000))
    _, recv_data = client.recv()
    print(recv_data.decode())  # "SOME DATA, MAY EXCEED 1500 bytes"
    client.send(1, b"Hello Server!")
    client.close()


if __name__ == "__main__":
    main()
