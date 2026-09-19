import asyncio

from saga.metadata.base import BaseMetadataProvider
from saga.models.metadata import MediaType, MetadataQuery
from saga.models.query import SeriesQuery
from saga.models.stream import Stream, StreamResult
from saga.models.torrent import RawTorrent, ResolvedTorrent
from saga.providers.base import BaseProvider
from saga.services.matching import (
    check_torrent_coverage,
    contain_dubs,
    extract_audio_languages,
    find_file_idx,
    parse_trackers,
)
from saga.torrent.resolver import TorrentResolver


class StreamService:
    def __init__(
        self,
        provider: BaseProvider,
        metadata_provider: BaseMetadataProvider,
        resolver: TorrentResolver,
    ):
        self.provider = provider
        self.metadata_provider = metadata_provider
        self.resolver = resolver

    # async def get_series_streams(
    #     self,
    #     media_id: str,
    #     season: int,
    #     episode: int,
    #     dubs: list[str],
    #     max_dub_result: int = 10,
    #     max_other_result: int = 10,
    # ) -> StreamResult:
    #     media_type = MediaType.SERIES
    #     metadata_query = MetadataQuery(type=media_type, id=media_id)
    #     metadata = await self.metadata_provider.get_metadata(metadata_query)
    #
    #     query = SeriesQuery(title=metadata.titles["en"], episode=episode, season=season)
    #     raw_results = await self.provider.search(query)
    #     # print(f"Found {len(raw_results)} raw results")
    #
    #     others_streams: list[Stream] = []
    #     dubs_streams: list[Stream] = []
    #
    #     dub = True
    #
    #     def is_valid(torrent: ResolvedTorrent) -> bool:
    #         try:
    #             stream = find_file_idx(torrent, episode=episode, season=season)
    #             if dub:
    #                 dubs_streams.append(stream)
    #             else:
    #                 others_streams.append(stream)
    #             return True
    #         except NoMatchError:
    #             return False
    #
    #     filtered_results = [
    #         torrent
    #         for torrent in raw_results
    #         if valid_raw_torrent(torrent, episode=episode, season=season)
    #     ]
    #     dub_result = []
    #     other_results = []
    #
    #     for torrent in filtered_results:
    #         if not set(get_dub_language(torrent)).isdisjoint(dubs):
    #             dub_result.append(torrent)
    #         else:
    #             other_results.append(torrent)
    #
    #     # print(f"Found {len(dub_result)} dub results")
    #     # print(f"Found {len(other_results)} other results")
    #
    #     await self.resolver.bulk_resolve(
    #         dub_result, is_valid=is_valid, concurrency=10, max_result=max_dub_result
    #     )
    #     dub = False
    #     await self.resolver.bulk_resolve(
    #         other_results,
    #         is_valid=is_valid,
    #         concurrency=8,
    #         max_result=max_other_result,
    #     )
    #
    #     # print(f"Found {len(dubs_streams)} dub streams")
    #     # print(f"Found {len(others_streams)} other results")
    #
    #     return StreamResult(dubs_stream=dubs_streams, others=others_streams)*

    async def get_series_streams(
        self,
        media_id: str,
        season: int,
        episode: int,
        dubs: list[str],
        max_dub_result: int = 10,
        max_other_result: int = 10,
    ) -> StreamResult:
        if "mul" in dubs:
            raise ValueError("'mul' cannot be use for dubs language")
        media_type = MediaType.SERIES
        metadata_query = MetadataQuery(type=media_type, id=media_id)
        metadata = await self.metadata_provider.get_metadata(metadata_query)

        tasks = [
            self.provider.search(
                SeriesQuery(title=metadata.titles[dub], episode=episode, season=season)
            )
            for dub in dubs
            if metadata.titles.get(dub)
        ]

        print("Scraping torrents")
        raw_results = await asyncio.gather(*tasks)
        raw_results = [torrent for torrents in raw_results for torrent in torrents]

        def is_valid(torrent: ResolvedTorrent) -> bool:
            file_idx = find_file_idx(torrent, episode=episode, season=season)
            return file_idx is not None

        # filter raw torrent before resolving to not wasting time on unwanted streams
        filtered_results = [
            torrent
            for torrent in raw_results
            if check_torrent_coverage(torrent, episode=episode, season=season)
        ]
        dub_result: list[RawTorrent] = []
        other_results: list[RawTorrent] = []

        for torrent in filtered_results:
            if contain_dubs(torrent, dubs, metadata.original_language):
                dub_result.append(torrent)
            else:
                other_results.append(torrent)

        print(f"Resolving {len(dub_result) + len(other_results)} torrents")
        dubs_resolved_torrents = await self.resolver.bulk_resolve(
            dub_result, is_valid=is_valid, concurrency=10, max_result=max_dub_result
        )
        other_resolved_torrents = await self.resolver.bulk_resolve(
            other_results,
            is_valid=is_valid,
            concurrency=8,
            max_result=max_other_result,
        )

        # converting to stream object
        dubs_streams: list[Stream] = []
        others_streams: list[Stream] = []

        for is_dub, torrents in (
            (True, dubs_resolved_torrents),
            (False, other_resolved_torrents),
        ):
            for torrent in torrents:
                file_idx = find_file_idx(torrent, season, episode)
                if file_idx is not None:
                    stream = Stream(
                        torrent_name=torrent.title,
                        raw_name=torrent.files[file_idx].file_name,
                        dubs_language=extract_audio_languages(
                            torrent, original_language=metadata.original_language
                        ),
                        info_hash=torrent.info_hash,
                        file_idx=file_idx,
                        sources=parse_trackers(torrent.magnet),
                    )
                    if is_dub:
                        dubs_streams.append(stream)
                    else:
                        others_streams.append(stream)

        return StreamResult(dubs_stream=dubs_streams, others=others_streams)
