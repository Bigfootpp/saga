import time

import httpx

from saga.models.torrent import RawTorrent
from saga.torrent.db import ResolvedTorrent, TorrentDatabaseRepo
from saga.torrent.exceptions import TorrentResolveError
from saga.torrent.resolver import TorrentResolver

# 2h
CACHE_TTL = 2 * 60 * 60


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
            if isinstance(cache, ResolvedTorrent):
                return cache
            elif time.time() - cache.updated_at < CACHE_TTL:
                raise TorrentResolveError(
                    f"Torrent considered dead, next cache invalidation in {CACHE_TTL - (time.time() - cache.updated_at)}"
                )
        try:
            resolved_torrent = await super().resolve(raw_torrent)
            await self._repo.update_torrent(
                resolved_torrent.info_hash, resolved_torrent
            )
        except TorrentResolveError:
            await self._repo.update_torrent(raw_torrent.info_hash, None)
            raise
        return resolved_torrent
