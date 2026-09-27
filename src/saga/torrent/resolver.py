import asyncio
import pathlib
import tempfile
import time
from collections.abc import Callable

import httpx
import libtorrent as lt
from torf import Torrent

from saga.models.torrent import RawTorrent, ResolvedTorrent, TorrentFileEntry
from saga.torrent.exceptions import TorrentResolveError


class TorrentResolver:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 7.0,
    ):
        self.client = client or httpx.AsyncClient()
        self.timeout = timeout
        self._lt_session: lt.session = lt.session(
            {
                "listen_interfaces": "0.0.0.0:0",
                "enable_dht": True,
                "enable_upnp": True,
                "enable_natpmp": True,
                "alert_mask": 0,
                "active_downloads": 100,
                "active_limit": 100,
                "active_checking": 100,
            }
        )
        self._lt_session.add_dht_router("dht.transmissionbt.com", 6881)
        self._lt_session.add_dht_router("router.bittorrent.com", 6881)
        self._lt_session.add_dht_router("dht.libtorrent.org", 25401)
        self._lt_session.add_dht_router("router.utorrent.com", 6881)

    async def resolve(self, raw_torrent: RawTorrent) -> ResolvedTorrent:
        # if raw_torrent.torrent_link:
        #     try:
        #         resolved_torrent = await self._resolve_via_torrent_link(raw_torrent)
        #         if resolved_torrent:
        #             return resolved_torrent
        #         # if files is not None:
        #         #     return self._to_resolved(raw_torrent, files)
        #     except Exception:
        #         pass

        try:
            return await self._resolve_via_libtorrent(raw_torrent)
            # return self._to_resolved(raw_torrent, files)
        except Exception as e:
            if isinstance(e, TorrentResolveError):
                raise
            raise TorrentResolveError(
                f"Failed to resolve torrent via libtorrent: {e}"
            ) from e

    async def _resolve_via_torrent_link(
        self, raw_torrent: RawTorrent
    ) -> ResolvedTorrent | None:
        if not raw_torrent.torrent_link:
            return None
        try:
            response = await self.client.get(
                raw_torrent.torrent_link, timeout=self.timeout
            )
            response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError):
            return None

        content = response.content
        if not content:
            return None

        try:
            files = await asyncio.to_thread(self._parse_torf_bytes, content)
            return self._to_resolved(raw_torrent, files)
        except Exception:
            return None

    @staticmethod
    def _parse_torf_bytes(content: bytes) -> list[TorrentFileEntry]:
        torrent = Torrent.read_stream(content)
        entries: list[TorrentFileEntry] = []
        for idx, f in enumerate(torrent.files):
            path = str(f)
            file_name = pathlib.Path(path).name
            entries.append(
                TorrentFileEntry(
                    file_idx=idx, file_name=file_name, path=path, size=f.size
                )
            )
        return entries

    async def _resolve_via_libtorrent(self, raw_torrent: RawTorrent) -> ResolvedTorrent:
        magnet = raw_torrent.magnet
        ses = self._lt_session

        try:
            params = lt.parse_magnet_uri(magnet)
        except Exception as e:
            raise TorrentResolveError(f"Invalid magnet URI: {e}") from e

        params.save_path = tempfile.gettempdir()

        # params.flags |= lt.torrent_flags.upload_mode
        # params.flags |= lt.torrent_flags.stop_when_ready

        handle = ses.add_torrent(params)
        handle.resume()
        start = time.monotonic()

        try:
            while not handle.has_metadata():
                if time.monotonic() - start > self.timeout:
                    raise TorrentResolveError(
                        f"Timeout fetching metadata via libtorrent for {magnet}"
                    )
                await asyncio.sleep(0.1)

            status = handle.status()
            distributed_copies = status.distributed_copies
            seeders = status.num_seeds
            peers = status.num_peers
            ti = handle.torrent_file()
            if ti is None:
                raise TorrentResolveError("No torrent info after metadata fetch")

            handle.pause()
            handle.prioritize_files([0] * ti.num_files())

            fs = ti.files()
            entries: list[TorrentFileEntry] = []
            for idx in range(fs.num_files()):
                path = fs.file_path(idx)
                file_name = pathlib.Path(path).name
                size = fs.file_size(idx)
                entries.append(
                    TorrentFileEntry(
                        file_idx=idx, file_name=file_name, path=path, size=size
                    )
                )
            return self._to_resolved(
                raw_torrent,
                entries,
                seeders=seeders,
                peers=peers,
                distributed_copies=distributed_copies,
            )

        finally:
            try:
                if handle.is_valid():
                    ses.remove_torrent(handle)
            except Exception:
                pass

    @staticmethod
    def _to_resolved(
        raw: RawTorrent,
        files: list[TorrentFileEntry],
        peers: int | None = None,
        seeders: int | None = None,
        distributed_copies: float | None = None,
    ) -> ResolvedTorrent:
        return ResolvedTorrent(
            title=raw.title,
            info_hash=raw.info_hash.lower(),
            magnet=raw.magnet,
            files=files,
            peers=peers or raw.peers,
            seeders=seeders or raw.seeders,
            distributed_copies=distributed_copies,
        )

    async def bulk_resolve(
        self,
        raw_torrents: list[RawTorrent],
        max_result: int | None = None,
        concurrency: int = 10,
        is_valid: Callable[[ResolvedTorrent], bool] | None = None,
    ) -> list[ResolvedTorrent]:
        semaphore = asyncio.Semaphore(concurrency)

        async def _resolve_one(raw: RawTorrent) -> ResolvedTorrent | None:
            async with semaphore:
                try:
                    return await self.resolve(raw)
                except TorrentResolveError:
                    print(f"Timeout fetching {raw.title}, {raw.info_hash}")
                    return None

        resolved_torrents: list[ResolvedTorrent] = []
        tasks = [asyncio.create_task(_resolve_one(r)) for r in raw_torrents]

        try:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result is not None:
                    if is_valid is None or is_valid(result):
                        resolved_torrents.append(result)

                    if max_result is not None and len(resolved_torrents) >= max_result:
                        break
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)

        return resolved_torrents
