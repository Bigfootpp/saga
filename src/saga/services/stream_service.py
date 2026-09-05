from saga.metadata.base import BaseMetadataProvider
from saga.models.metadata import MediaType, MetadataQuery
from saga.models.query import SeriesQuery
from saga.models.stream import Stream, StreamResult
from saga.providers.base import BaseProvider
from saga.services.matching import (
    NoMatchError,
    find_file_idx,
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
        self, media_id: str, season: int, episode: int
    ) -> StreamResult:
        media_type = MediaType.SERIES
        metadata_query = MetadataQuery(type=media_type, id=media_id)
        metadata = await self.metadata_provider.get_metadata(metadata_query)

        query = SeriesQuery(title=metadata.titles["en"], episode=episode, season=season)
        raw_results = await self.provider.search(query)
        # print(f"Raw results count: {len(raw_results)}")

        filtered_results = [
            torrent for torrent in raw_results if valid_raw_torrent(torrent, query)
        ]
        # print(f"Filtered results count: {len(filtered_results)}")

        resolved_torrents = await self.resolver.bulk_resolve(
            filtered_results, concurrency=8
        )
        # print(f"Resolved results count: {len(resolved_torrents)}")

        others_streams: list[Stream] = []
        dubs_streams: list[Stream] = []
        for torrent in resolved_torrents:
            try:
                stream = find_file_idx(torrent, query)
                if stream.dubs_language:
                    dubs_streams.append(stream)
                else:
                    others_streams.append(stream)
            except NoMatchError:
                pass

        return StreamResult(dubs_stream=dubs_streams, others=others_streams)
