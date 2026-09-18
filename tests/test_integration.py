import asyncio
from datetime import datetime
from pathlib import Path

import anyio
import pytest

from saga.env_model import env
from saga.metadata.tmdb import TMDBMetadataProvider
from saga.providers.jackett import JackettProvider
from saga.services.stream_service import StreamService
from saga.torrent.resolver import TorrentResolver

media_id = "tt2560140"
season = 1
episode = 1
dubs = ["fr", "en"]


@pytest.mark.integration
async def test_integration():
    provider = JackettProvider(
        base_url=env.jackett_base_url,
        api_key=env.jackett_api_key,
    )
    metadata_provider = TMDBMetadataProvider(api_key=env.tmdb_api_key)
    resolver = TorrentResolver()

    stream_service = StreamService(
        provider=provider, metadata_provider=metadata_provider, resolver=resolver
    )
    result = await stream_service.get_series_streams(
        media_id, season, episode, dubs=dubs
    )
    print(f"dubs count: {len(result.dubs_stream)}")
    for stream in result.dubs_stream:
        print(f"{stream.torrent_name} -> {stream.raw_name}")
    print(f"other count: {len(result.others)}")
    for stream in result.others:
        print(f"{stream.torrent_name} -> {stream.raw_name}")

    now = datetime.now(tz=datetime.now().astimezone().tzinfo)

    path = (
        Path.cwd()
        / "results"
        / f"{media_id}_{'-'.join(dubs)}_{now.strftime('%Y-%m-%d_%H-%M-%S')}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)

    async with await anyio.open_file(path, mode="w") as f:
        await f.write(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(test_integration())
