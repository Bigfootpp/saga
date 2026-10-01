import asyncio
import random
import socket
import struct
from typing import TypedDict


class TrackerError(Exception):
    pass


class ConnectError(TrackerError):
    pass


class ConnectionID(TypedDict):
    last_connection: int
    id: int


class UDPTrackerClient:
    def __init__(self, timeout: float = 1.5, max_per_batch: int = 50) -> None:
        self.timeout = timeout
        self.max_per_batch = max_per_batch
        self.connection_ids: dict[str, ConnectionID] = {}

    async def _connect_to_tracker(
        self, url: str, port: int
    ) -> tuple[socket.socket, asyncio.AbstractEventLoop]:
        loop = asyncio.get_running_loop()
        result = await loop.getaddrinfo(
            url, port, family=socket.AF_INET, type=socket.SOCK_DGRAM
        )
        address = result[0][4]

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.connect(address)

        return sock, loop

    async def _connect(self, url: str, port: int) -> int:
        sock, loop = await self._connect_to_tracker(url, port)

        transaction_id = random.getrandbits(32)
        packet = struct.pack(">QII", 0x41727101980, 0, transaction_id)
        await loop.sock_sendall(sock, packet)
        data = await loop.sock_recv(sock, 16)
        action, res_transaction_id, connection_id = struct.unpack(">IIQ", data)
        if action != 0 or res_transaction_id != transaction_id:
            raise ConnectError("Connection failed")

        return connection_id
