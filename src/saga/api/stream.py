from typing import Literal

import httpx
from fastapi import APIRouter
from pydantic import ValidationError

from saga.env_model import env
from saga.metadata.kitsu import KitsuMetadataProvider
from saga.metadata.tmdb import TMDBMetadataProvider
from saga.models.stream import StremioStreamResult
from saga.providers.jackett import JackettProvider
from saga.services.formatter import (
    DubsLanguagesElement,
    Formatter,
    NewLineElement,
    RawNameElement,
)
from saga.services.stream_service import StreamService
from saga.torrent.cached_resolver import CachedTorrentResolver
from saga.torrent.db import TorrentDatabaseRepo
from saga.torrent.udp_tracker_client import UDPTrackerClient
from saga.utils.config_parser import parse_config
from saga.utils.stremio import convert_to_stremio_stream_result, parse_series_id

router = APIRouter()

http_client = httpx.AsyncClient()

provider = JackettProvider(
    base_url=env.jackett_base_url, api_key=env.jackett_api_key, client=http_client
)
metadata_provider = TMDBMetadataProvider(api_key=env.tmdb_api_key, client=http_client)
kitsu_metadata_provider = KitsuMetadataProvider(client=http_client)

repo = TorrentDatabaseRepo(path=env.saga_data_dir / "saga.db")
resolver = CachedTorrentResolver(repo=repo, client=http_client)
udp_tracker_client = UDPTrackerClient()

stream_service = StreamService(
    provider=provider,
    metadata_provider=metadata_provider,
    kitsu_metadata_provider=kitsu_metadata_provider,
    resolver=resolver,
    tracker_client=udp_tracker_client,
)


formatter = Formatter(RawNameElement(), NewLineElement(), DubsLanguagesElement())


@router.get("/{configb64}/stream/{stream_type}/{stream_id}")
@router.get("/{configb64}/stream/{stream_type}/{stream_id}.json")
async def stream(
    configb64: str, stream_type: Literal["series"], stream_id: str
) -> StremioStreamResult:
    try:
        config = parse_config(configb64)
    except ValidationError:
        return StremioStreamResult(streams=[])
    match stream_type:
        case "series":
            full_id = parse_series_id(stream_id)
            if full_id:
                series_id, season, episode = full_id
                result = await stream_service.get_series_streams(
                    series_id,
                    season,
                    episode,
                    dubs=config.preferred_dubs,
                    max_dub_result=config.dub_max_results,
                    max_other_result=config.other_max_results,
                )

                return convert_to_stremio_stream_result(result, "Saga", formatter)
    return StremioStreamResult(streams=[])
