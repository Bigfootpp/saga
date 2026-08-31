import httpx

from saga.models.torrent import RawTorrent, ResolvedTorrent


class TorrentResolver:
    async def __init__(
        self,
        client: httpx.AsyncClient,
        timeout: float = 15.0
    ): ...
    async def resolve(self, raw_torrent: RawTorrent) -> ResolvedTorrent: ...