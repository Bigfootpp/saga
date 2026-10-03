from saga.metadata.base import BaseMetadataProvider
from saga.metadata.kitsu import KitsuMetadataProvider
from saga.models.stream import StreamResult
from saga.models.torrent import ResolvedTorrent
from saga.providers.base import BaseProvider
from saga.services.container import RawTorrentContainer, StreamContainer
from saga.services.matching import (
    find_file_idx,
)
from saga.services.wrapper import MetadataWrapper, ProviderWrapper, TrackerClientWrapper
from saga.torrent.resolver import TorrentResolver
from saga.torrent.udp_tracker_client import UDPTrackerClient
from saga.utils.stopwatch import Stopwatch


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

        abs_episode = episode
        if metadata.episodes:
            count = 0
            for metadata_episode in metadata.episodes:
                if metadata_episode.season > 0:
                    count += 1

            abs_episode = count

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

        with Stopwatch() as watch:
            raw_results = await self.provider.search_series(titles, season, episode)
            print(f"Scraped {len(raw_results)} in {watch.time}s")

        raw_results = await self.tracker_client.resolve_peers_count(raw_results)

        def is_valid(torrent: ResolvedTorrent) -> bool:
            # if (
            #     torrent.distributed_copies is not None
            #     and torrent.distributed_copies < 1
            # ):
            #     return False
            file_idx = find_file_idx(torrent, season, episode, abs_episode)
            return file_idx is not None

        # filter raw torrent before resolving to not wasting time on unwanted streams
        container = RawTorrentContainer(
            titles, dubs, metadata.original_language, episode, season
        )
        container.add_torrents(raw_results)

        with Stopwatch() as watch:
            print(f"Resolving {len(container.torrents)} torrents")
            dubs_resolved_torrents = await self.resolver.bulk_resolve(
                container.dubs,
                is_valid=is_valid,
                concurrency=15,
                max_result=max_dub_result,
            )
            other_resolved_torrents = await self.resolver.bulk_resolve(
                container.others,
                is_valid=is_valid,
                concurrency=15,
                max_result=max_other_result,
            )
            print(f"Resolving finished in {watch.time}")

        # converting to stream object
        dubs_streams = StreamContainer(
            season, episode, metadata.original_language, abs_episode
        )
        others_streams = StreamContainer(
            season, episode, metadata.original_language, abs_episode
        )

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
