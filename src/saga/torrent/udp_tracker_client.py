import asyncio
import random
import socket
import struct
import time
from typing import TypedDict

from saga.models.tracker import ScrapeItemResult

MAX_HASHES = 50
MAGIC_NUMBER = 0x41727101980


class TrackerError(Exception):
    pass


class ConnectError(TrackerError):
    pass


class ScrapeError(TrackerError):
    pass


class ConnectionID(TypedDict):
    last_connection: float
    id: int


class UDPTrackerClient:
    def __init__(self, timeout: float = 1.5) -> None:
        self.timeout = timeout
        self.connection_ids: dict[tuple[str, int], ConnectionID] = {}

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
        packet = struct.pack(">QII", MAGIC_NUMBER, 0, transaction_id)
        await loop.sock_sendall(sock, packet)
        data = await loop.sock_recv(sock, 16)
        action, res_transaction_id, connection_id = struct.unpack(">IIQ", data)
        if action != 0 or res_transaction_id != transaction_id:
            raise ConnectError("Connection failed")

        return connection_id

    async def scrape(
        self, url: str, port: int, hashes: list[str]
    ) -> dict[str, ScrapeItemResult]:
        if len(hashes) > MAX_HASHES:
            raise ScrapeError("Too much hashes provided")
        sock, loop = await self._connect_to_tracker(url, port)
        connection_id_dict = self.connection_ids.get((url, port))
        if (
            connection_id_dict is None
            or time.monotonic() - connection_id_dict["last_connection"] > 40
        ):
            connection_id = await self._connect(url, port)
            self.connection_ids[(url, port)] = {
                "last_connection": time.monotonic(),
                "id": connection_id,
            }
        else:
            connection_id = connection_id_dict["id"]

        transaction_id = random.getrandbits(32)

        packet = struct.pack(">QII", connection_id, 2, transaction_id) + b"".join(
            [bytes.fromhex(info_hash) for info_hash in hashes]
        )
        await loop.sock_sendall(sock, packet)
        data = await loop.sock_recv(sock, 8 + (len(hashes) * 12))
        action, res_transaction_id = struct.unpack_from(">II", data, 0)
        if action != 2 and res_transaction_id != transaction_id:
            raise ScrapeError("Scrape failed")

        result: dict[str, ScrapeItemResult] = {}
        for i, hash in enumerate(hashes):
            offset = 8 + (i * 12)
            seeders, completed, leechers = struct.unpack_from(">III", data, offset)
            result[hash] = ScrapeItemResult(
                info_hash=hash,
                seeders=seeders,
                completed=completed,
                leechers=leechers,
            )

        sock.close()

        return result
