import httpx

from saga.models.torrent import RawTorrent
from saga.torrent.db import ResolvedTorrent, TorrentDatabaseRepo
from saga.torrent.resolver import TorrentResolver


class CachedTorrentResolver(TorrentResolver):
    def __init__(
        self,
        repo: TorrentDatabaseRepo,
        client: httpx.AsyncClient | None = None,
        timeout: float = 7,
    ):
        super().__init__(client, timeout)
        self._repo = repo

    async def resolve(self, raw_torrent: RawTorrent) -> ResolvedTorrent:
        cache = await self._repo.get_torrent(raw_torrent.info_hash)
        if cache:
            return cache
        return await super().resolve(raw_torrent)
