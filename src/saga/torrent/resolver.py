import asyncio
import pathlib
import tempfile
import time

import httpx
from torf import Torrent

from saga.models.torrent import RawTorrent, ResolvedTorrent, TorrentFileEntry
from saga.torrent.exceptions import TorrentResolveError


class TorrentResolver:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        timeout: float = 15.0,
    ):
        self.client = client or httpx.AsyncClient()
        self.timeout = timeout

    async def resolve(self, raw_torrent: RawTorrent) -> ResolvedTorrent:
        if raw_torrent.torrent_link:
            try:
                files = await self._resolve_via_torrent_link(raw_torrent.torrent_link)
                if files is not None:
                    return self._to_resolved(raw_torrent, files)
            except TorrentResolveError:
                pass

        try:
            files = await self._resolve_via_libtorrent(raw_torrent.magnet)
            return self._to_resolved(raw_torrent, files)
        except Exception as e:
            if isinstance(e, TorrentResolveError):
                raise
            raise TorrentResolveError(
                f"Failed to resolve torrent via libtorrent: {e}"
            ) from e

    async def _resolve_via_torrent_link(
        self, url: str
    ) -> list[TorrentFileEntry] | None:
        try:
            response = await self.client.get(url, timeout=self.timeout)
            response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError):
            return None

        content = response.content
        if not content:
            return None

        try:
            files = await asyncio.to_thread(self._parse_torf_bytes, content)
        except Exception:
            return None

        return files

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

    async def _resolve_via_libtorrent(self, magnet: str) -> list[TorrentFileEntry]:
        try:
            files = await asyncio.wait_for(
                asyncio.to_thread(
                    self._fetch_via_libtorrent_sync, magnet, self.timeout
                ),
                timeout=self.timeout + 2,
            )
            return files
        except TimeoutError as e:
            raise TorrentResolveError(
                f"Timeout fetching metadata via libtorrent for {magnet}"
            ) from e

    @staticmethod
    def _fetch_via_libtorrent_sync(
        magnet: str, timeout: float
    ) -> list[TorrentFileEntry]:
        import libtorrent as lt

        ses = lt.session(
            {
                "listen_interfaces": "0.0.0.0:0",
                "enable_dht": True,
                "alert_mask": int(lt.alert.category_t.error_notification),
            }
        )

        try:
            params = lt.parse_magnet_uri(magnet)
        except Exception as e:
            raise TorrentResolveError(f"Invalid magnet URI: {e}") from e

        params.save_path = tempfile.gettempdir()

        handle = ses.add_torrent(params)

        start = time.monotonic()
        while not handle.has_metadata():
            if time.monotonic() - start > timeout:
                ses.remove_torrent(handle)
                raise TimeoutError(f"Metadata fetch timed out after {timeout}s")

            status = handle.status()
            if status.state not in (0, 1, 2):
                pass
            time.sleep(0.1)

        try:
            ti = handle.torrent_file()
            if ti is None:
                raise TorrentResolveError("No torrent info after metadata fetch")
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
            return entries
        finally:
            try:
                ses.remove_torrent(handle)
            except Exception:
                pass

    @staticmethod
    def _to_resolved(raw: RawTorrent, files: list[TorrentFileEntry]) -> ResolvedTorrent:
        return ResolvedTorrent(
            title=raw.title,
            info_hash=raw.info_hash.lower(),
            magnet=raw.magnet,
            files=files,
        )

    async def bulk_resolve(
        self, raw_torrents: list[RawTorrent], concurrency: int = 5
    ) -> list[ResolvedTorrent]:
        semaphore = asyncio.Semaphore(concurrency)

        async def _resolve_one(raw: RawTorrent) -> ResolvedTorrent | None:
            async with semaphore:
                try:
                    return await self.resolve(raw)
                except TorrentResolveError:
                    return None

        results = await asyncio.gather(*[_resolve_one(r) for r in raw_torrents])
        return [r for r in results if r is not None]
