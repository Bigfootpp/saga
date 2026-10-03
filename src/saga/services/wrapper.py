import asyncio
from urllib.parse import urlparse

from saga.metadata.base import BaseMetadataProvider
from saga.models.metadata import (
    MediaType,
    Metadata,
    MetadataIdQuery,
    MetadataTitleQuery,
)
from saga.models.query import SeriesQuery
from saga.models.torrent import RawTorrent
from saga.models.tracker import ScrapeItemResult
from saga.providers.base import BaseProvider
from saga.services.matching import parse_trackers
from saga.torrent.udp_tracker_client import TrackerError, UDPTrackerClient


class MetadataWrapper:
    def __init__(self, metadata_provider: BaseMetadataProvider) -> None:
        self.metadata_provider = metadata_provider

    async def get_series_metadata_id(self, media_id: str) -> Metadata:
        media_type = MediaType.SERIES
        metadata_query = MetadataIdQuery(type=media_type, id=media_id)
        return await self.metadata_provider.get_metadata(metadata_query)

    async def get_series_metadata_title(self, title: str) -> Metadata:
        media_type = MediaType.SERIES
        metadata_query = MetadataTitleQuery(type=media_type, title=title)
        return await self.metadata_provider.get_metadata(metadata_query)


class ProviderWrapper:
    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider

    async def search_series(
        self, titles: list[str], season: int, episode: int
    ) -> list[RawTorrent]:
        tasks = [
            self.provider.search(SeriesQuery(title=dub, episode=episode, season=season))
            for dub in set(titles)
        ]

        raw_results = await asyncio.gather(*tasks)
        raw_results = [torrent for torrents in raw_results for torrent in torrents]
        raw_results = list({t.info_hash.lower(): t for t in raw_results}.values())
        return raw_results


class TrackerClientWrapper:
    def __init__(self, tracker_client: UDPTrackerClient) -> None:
        self.client = tracker_client

    async def _scrape_tracker(
        self, tracker: str, info_hashes: list[str]
    ) -> dict[str, ScrapeItemResult] | None:
        parsed_address = urlparse(tracker)
        hostname = parsed_address.hostname
        port = parsed_address.port

        if hostname is None or port is None:
            return None

        try:
            return await self.client.scrape(hostname, port, info_hashes)
        except (TrackerError, ConnectionRefusedError, TimeoutError, OSError):
            return None

    async def resolve_peers_count[T: RawTorrent](self, torrents: list[T]) -> list[T]:
        trackers = {
            tracker
            for torrent in torrents
            for tracker in parse_trackers(torrent.magnet)
        }
        info_hashes = list({torrent.info_hash for torrent in torrents})

        tasks = [self._scrape_tracker(tracker, info_hashes) for tracker in trackers]
        scrape_responses = await asyncio.gather(*tasks, return_exceptions=True)

        best_scrape_results: dict[str, ScrapeItemResult] = {}
        for response in scrape_responses:
            if not isinstance(response, dict):
                continue

            for info_hash, info in response.items():
                current_best = best_scrape_results.get(info_hash)

                if current_best is None or (info.leechers + info.seeders) > (
                    current_best.leechers + current_best.seeders
                ):
                    best_scrape_results[info_hash] = info

        result: list[T] = []
        for torrent in torrents:
            item = best_scrape_results.get(torrent.info_hash)
            if item:
                result.append(
                    torrent.model_copy(
                        update={
                            "peers": item.leechers + item.seeders,
                            "seeders": item.seeders,
                        }
                    )
                )
            else:
                result.append(torrent.model_copy())

        return result
