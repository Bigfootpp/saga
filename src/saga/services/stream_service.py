from saga.metadata.base import BaseMetadataProvider
from saga.models.metadata import MediaType, MetadataQuery
from saga.models.query import SeriesQuery
from saga.models.stream import Stream, StreamResult
from saga.models.torrent import ResolvedTorrent
from saga.providers.base import BaseProvider
from saga.services.matching import (
    NoMatchError,
    find_file_idx,
    get_dub_language,
    valid_raw_torrent,
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

    async def get_series_streams(
        self,
        media_id: str,
        season: int,
        episode: int,
        dubs: list[str],
        max_dub_result: int = 10,
        max_other_result: int = 10,
    ) -> StreamResult:
        media_type = MediaType.SERIES
        metadata_query = MetadataQuery(type=media_type, id=media_id)
        metadata = await self.metadata_provider.get_metadata(metadata_query)

        query = SeriesQuery(title=metadata.titles["en"], episode=episode, season=season)
        raw_results = await self.provider.search(query)
        # print(f"Found {len(raw_results)} raw results")

        others_streams: list[Stream] = []
        dubs_streams: list[Stream] = []

        dub = True

        def is_valid(torrent: ResolvedTorrent) -> bool:
            try:
                stream = find_file_idx(torrent, query)
                if dub:
                    dubs_streams.append(stream)
                else:
                    others_streams.append(stream)
                return True
            except NoMatchError:
                return False

        filtered_results = [
            torrent for torrent in raw_results if valid_raw_torrent(torrent, query)
        ]
        dub_result = []
        other_results = []

        for torrent in filtered_results:
            dub = get_dub_language(torrent)
            if not set(get_dub_language(torrent)).isdisjoint(dubs):
                dub_result.append(torrent)
            else:
                other_results.append(torrent)

        # print(f"Found {len(dub_result)} dub results")
        # print(f"Found {len(other_results)} other results")

        await self.resolver.bulk_resolve(
            dub_result, is_valid=is_valid, concurrency=10, max_result=max_dub_result
        )
        dub = False
        await self.resolver.bulk_resolve(
            other_results,
            is_valid=is_valid,
            concurrency=8,
            max_result=max_other_result,
        )

        # print(f"Found {len(dubs_streams)} dub streams")
        # print(f"Found {len(others_streams)} other results")

        return StreamResult(dubs_stream=dubs_streams, others=others_streams)
