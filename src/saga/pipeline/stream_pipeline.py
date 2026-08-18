from __future__ import annotations

import time

from saga.filtering.pipeline import filter_items, sort_items
from saga.jackett.client import JackettClient
from saga.metadata.base import MetadataProvider
from saga.metadata.cinemeta import Cinemeta
from saga.metadata.tmdb import TMDB
from saga.models.config import Config
from saga.rendering.render import build_stream_response
from saga.torrent.container import TorrentContainer
from saga.torrent.torrent_service import TorrentService
from saga.utils.logger import setup_logger


def build_metadata_provider(config: Config) -> MetadataProvider:
    if config.metadata_provider == "tmdb" and config.tmdb_api:
        return TMDB(config)
    else:
        return Cinemeta(config)

class StreamPipeline:
    def __init__(
        self,
        config: Config,
        community_version: bool = False,
    ):
        self.config = config
        self.community_version = community_version
        self.logger = setup_logger(__name__)

    async def build_streams(self, stream_type: str, stream_id: str) -> dict:
        start = time.time()
        stream_id = stream_id.replace(".json", "")

        metadata_provider = build_metadata_provider(self.config)

        self.logger.info(f"Getting media from {self.config.metadata_provider}")
        media = await metadata_provider.get_metadata(stream_id, stream_type)
        if media is None:
            self.logger.error(f"Failed to get metadata for {stream_id} ({stream_type})")
            return {"streams": []}
        self.logger.info(f"Got media and properties: {media.titles}")

        search_results = []

        # Search Jackett
        if not self.community_version:
            self.logger.info("Searching for results on Jackett")
            jackett_client = JackettClient(self.config)
            jackett_search_results = await jackett_client.search(media)
            self.logger.info(f"Got {len(jackett_search_results)} results from Jackett")

            self.logger.info("Filtering Jackett results")
            filtered_results = filter_items(jackett_search_results, media, self.config)
            self.logger.info("Filtered Jackett results")

            search_results.extend(filtered_results)

        # Convert to TorrentItems
        self.logger.debug(
            f"Converting result to TorrentItems (results: {len(search_results)})"
        )
        torrent_service = TorrentService()
        torrent_results = torrent_service.convert_and_process(search_results, media)
        self.logger.debug(
            f"Converted result to TorrentItems (results: {len(torrent_results)})"
        )

        # Build container
        torrent_container = TorrentContainer(torrent_results, media)

        # Get best matching and sort
        self.logger.debug("Getting best matching results")
        best_matching_results = torrent_container.get_best_matching()
        best_matching_results = sort_items(best_matching_results, self.config)
        self.logger.debug(
            f"Got best matching results (results: {len(best_matching_results)})"
        )

        # Build stream response
        self.logger.info("Processing results")
        stream_list = build_stream_response(best_matching_results, self.config, media)
        self.logger.info(f"Processed results (results: {len(stream_list)})")

        self.logger.info(f"Total time: {time.time() - start}s")

        return {"streams": stream_list}
