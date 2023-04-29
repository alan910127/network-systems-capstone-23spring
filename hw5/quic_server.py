class QUICServer:
    def listen(self, socket_addr: tuple[str, int]) -> None:
        """Listen for incoming QUIC connections on the given socket address."""

        raise NotImplementedError()

    def accept(self) -> None:
        """Accept an incoming QUIC connection."""

        raise NotImplementedError()

    def send(self, stream_id: int, data: bytes) -> None:
        """Send data on the given stream."""

        raise NotImplementedError()

    def recv(self) -> tuple[int, bytes]:
        """Receive data on any stream.

        Returns:
            int: The stream ID.
            bytes: The data.
        """

        raise NotImplementedError()

    def close(self) -> None:
        """Close the QUIC server."""

        raise NotImplementedError()


def main():
    server = QUICServer()
    server.listen(("", 30000))
    server.accept()
    server.send(1, b"SOME DATA, MAY EXCEED 1500 bytes")
    _, recv_data = server.recv()
    print(recv_data.decode())  # "Hello Server!"
    server.close()


if __name__ == "__main__":
    main()
