import asyncio
from urllib.parse import urlparse

from saga.metadata.base import BaseMetadataProvider
from saga.metadata.kitsu import KitsuMetadataProvider
from saga.models.metadata import (
    MediaType,
    Metadata,
    MetadataIdQuery,
    MetadataTitleQuery,
)
from saga.models.query import SeriesQuery
from saga.models.stream import Stream, StreamResult
from saga.models.torrent import RawTorrent, ResolvedTorrent
from saga.models.tracker import ScrapeItemResult
from saga.providers.base import BaseProvider
from saga.services.matching import (
    check_torrent_coverage,
    contain_dubs,
    extract_audio_languages,
    find_file_idx,
    matches_titles,
    parse_trackers,
)
from saga.torrent.resolver import TorrentResolver
from saga.torrent.udp_tracker_client import UDPTrackerClient


class RawTorrentContainer:
    def __init__(
        self,
        titles: list[str],
        dubs: list[str],
        original_language: str,
        episode: int | None,
        season: int | None,
    ) -> None:
        self._dub_torrents: list[RawTorrent] = []
        self._other_torrents: list[RawTorrent] = []
        self._titles = titles
        self._dubs = dubs
        self.original_language = original_language
        self._season = season
        self._episode = episode

    def add_torrents(self, raw_torrents: list[RawTorrent]):
        for torrent in raw_torrents:
            if (
                (torrent.seeders > 0)
                and (
                    self._episode is not None
                    and self._season is not None
                    and check_torrent_coverage(
                        torrent.title, episode=self._episode, season=self._season
                    )
                )
                and matches_titles(torrent.title, titles=self._titles)
            ):
                if contain_dubs(torrent.title, self._dubs, self.original_language):
                    self._dub_torrents.append(torrent)
                else:
                    self._other_torrents.append(torrent)

    @property
    def dubs(self) -> list[RawTorrent]:
        return self._dub_torrents

    @property
    def others(self) -> list[RawTorrent]:
        return self._other_torrents

    @property
    def torrents(self) -> list[RawTorrent]:
        return self._dub_torrents + self._other_torrents


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
        except (ConnectionRefusedError, TimeoutError, OSError):
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


class StreamContainer:
    def __init__(self, season: int, episode: int, original_language: str) -> None:
        self._season = season
        self._episode = episode
        self._original_language = original_language
        self._streams: list[Stream] = []

    def add_torrents(self, torrent: ResolvedTorrent) -> bool:
        file_idx = find_file_idx(torrent, self._season, self._episode)
        if file_idx is not None:
            stream = Stream(
                torrent_name=torrent.title,
                raw_name=torrent.files[file_idx].file_name,
                dubs_language=extract_audio_languages(
                    torrent.title, original_language=self._original_language
                ),
                info_hash=torrent.info_hash,
                file_idx=file_idx,
                sources=parse_trackers(torrent.magnet),
            )
            self._streams.append(stream)
            return True
        return False

    @property
    def streams(self) -> list[Stream]:
        return self._streams


class StreamService:
    def __init__(
        self,
        provider: BaseProvider,
        tracker_client: UDPTrackerClient,
        metadata_provider: BaseMetadataProvider,
        kitsu_metadata_provider: KitsuMetadataProvider,
        resolver: TorrentResolver,
    ):
        self.provider = ProviderWrapper(provider)
        self.metadata_querier = MetadataWrapper(metadata_provider)
        self.kitsu_metadata_querier = MetadataWrapper(kitsu_metadata_provider)
        self.resolver = resolver
        self.tracker_client = TrackerClientWrapper(tracker_client)

    async def get_series_streams(
        self,
        media_id: str,
        season: int,
        episode: int,
        dubs: list[str],
        max_dub_result: int = 10,
        max_other_result: int = 10,
    ) -> StreamResult:
        metadata = await self.metadata_querier.get_series_metadata_id(media_id)

        titles_set: set[str] = {
            metadata.titles[dub]
            for dub in set(dubs) | {"original", "en"}
            if metadata.titles.get(dub)
        }

        if "anime" in metadata.keywords:
            kitsu_metadata = (
                await self.kitsu_metadata_querier.get_series_metadata_title(
                    metadata.titles["en"]
                )
            )
            titles_set |= {
                title for title in kitsu_metadata.titles.values() if title.strip()
            }

        titles = list(titles_set)

        print("Scraping torrents")
        raw_results = await self.provider.search_series(titles, season, episode)
        print(f"Scraped {len(raw_results)} torrents")

        def is_valid(torrent: ResolvedTorrent) -> bool:
            # if (
            #     torrent.distributed_copies is not None
            #     and torrent.distributed_copies < 1
            # ):
            #     return False
            file_idx = find_file_idx(torrent, episode=episode, season=season)
            return file_idx is not None

        # filter raw torrent before resolving to not wasting time on unwanted streams
        container = RawTorrentContainer(
            titles, dubs, metadata.original_language, episode, season
        )
        container.add_torrents(raw_results)

        print(f"Resolving {len(container.torrents)} torrents")
        dubs_resolved_torrents1 = await self.resolver.bulk_resolve(
            container.dubs, is_valid=is_valid, concurrency=15, max_result=max_dub_result
        )
        other_resolved_torrents1 = await self.resolver.bulk_resolve(
            container.others,
            is_valid=is_valid,
            concurrency=15,
            max_result=max_other_result,
        )

        dubs_resolved_torrents = await self.tracker_client.resolve_peers_count(
            dubs_resolved_torrents1
        )
        other_resolved_torrents = await self.tracker_client.resolve_peers_count(
            other_resolved_torrents1
        )

        # converting to stream object
        dubs_streams = StreamContainer(season, episode, metadata.original_language)
        others_streams = StreamContainer(season, episode, metadata.original_language)

        for is_dub, torrents in (
            (True, dubs_resolved_torrents),
            (False, other_resolved_torrents),
        ):
            for torrent in torrents:
                if torrent.seeders > 0:
                    if is_dub:
                        dubs_streams.add_torrents(torrent)
                    else:
                        others_streams.add_torrents(torrent)

        return StreamResult(
            dubs_stream=dubs_streams.streams, others=others_streams.streams
        )
