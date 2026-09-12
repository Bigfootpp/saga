import asyncio

from saga.config import settings
from saga.metadata.tmdb import TMDBMetadataProvider
from saga.providers.jackett import JackettProvider
from saga.services.stream_service import StreamService
from saga.torrent.resolver import TorrentResolver


async def main():
    provider = JackettProvider(
        base_url=settings.jackett_base_url,
        api_key=settings.jackett_api_key,
    )
    metadata_provider = TMDBMetadataProvider(api_key=settings.tmdb_api_key)
    resolver = TorrentResolver()

    stream_service = StreamService(
        provider=provider, metadata_provider=metadata_provider, resolver=resolver
    )
    result = await stream_service.get_series_streams(
        "tt15975122", 1, 1, dubs=["fr", "en", "mul"]
    )
    print(f"dubs count: {len(result.dubs_stream)}")
    for stream in result.dubs_stream:
        print(stream.raw_name)
    print(f"other count: {len(result.others)}")
    for stream in result.others:
        print(stream.raw_name)


asyncio.run(main())
