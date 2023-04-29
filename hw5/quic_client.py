class QUICClient:
    def connect(self, socket_addr: tuple[str, int]) -> None:
        """Connect to a QUIC server on the given socket address."""

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
        """Close the connection and the socket."""

        raise NotImplementedError()


def main():
    client = QUICClient()
    client.connect(("127.0.0.1", 30000))
    _, recv_data = client.recv()
    print(recv_data.decode())  # "SOME DATA, MAY EXCEED 1500 bytes"
    client.send(1, b"Hello Server!")
    client.close()


if __name__ == "__main__":
    main()
