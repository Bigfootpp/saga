from __future__ import annotations

import time
from typing import TYPE_CHECKING

from debrid.get_debrid_service import get_debrid_service
from filtering.pipeline import filter_items, sort_items
from jackett.client import JackettClient
from metadata.cinemeta import Cinemeta
from metadata.tmdb import TMDB
from models.config import Config
from rendering.render import build_stream_response
from torrent.container import TorrentSmartContainer
from torrent.torrent_service import TorrentService
from utils.logger import setup_logger
from utils.parse_config import parse_config

if TYPE_CHECKING:
    from fastapi import Request


class StreamPipeline:
    def __init__(
        self,
        config: Config,
        request_ip: str,
        community_version: bool = False,
    ):
        self.config = config
        self.request_ip = request_ip
        self.community_version = community_version
        self.logger = setup_logger(__name__)

    @classmethod
    def from_request(
        cls, request: Request, config_b64: str, community_version: bool = False
    ) -> StreamPipeline:
        config_obj = parse_config(config_b64)
        ip = request.client.host if request.client else "127.0.0.1"
        return cls(config_obj, ip, community_version)

    def build_streams(self, stream_type: str, stream_id: str) -> dict:
        start = time.time()
        stream_id = stream_id.replace(".json", "")

        # Select metadata provider
        if self.config.metadata_provider == "tmdb" and self.config.tmdb_api:
            metadata_provider = TMDB(self.config)
            if not self.community_version and self.config.jackett:
                jackett_client = JackettClient(self.config)
                metadata_provider.indexers = jackett_client.get_indexers()
        else:
            metadata_provider = Cinemeta(self.config)

        # Get media metadata
        self.logger.info(f"Getting media from {self.config.metadata_provider}")
        media = metadata_provider.get_metadata(stream_id, stream_type)
        if media is None:
            self.logger.error(f"Failed to get metadata for {stream_id} ({stream_type})")
            return {"streams": []}
        self.logger.info(f"Got media and properties: {media.titles}")

        # Get debrid service
        debrid_service = get_debrid_service(self.config)

        search_results = []

        # Search Jackett if enabled
        if not self.community_version and self.config.jackett:
            self.logger.info("Searching for results on Jackett")
            jackett_client = JackettClient(self.config)
            jackett_search_results = jackett_client.search(media)
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
        torrent_container = TorrentSmartContainer(torrent_results, media)

        # Check debrid availability for supported services
        if self.config.debrid and self.config.service in ["torbox", "premiumize"]:
            self.logger.debug("Checking availability")
            hashes = torrent_container.get_hashes()
            result = debrid_service.get_availability_bulk(hashes, self.request_ip)
            avail_result = debrid_service.extract_availability(result, hashes, media)
            torrent_container.apply_availability(avail_result)
            self.logger.debug(f"Checked availability (results: {len(result.items())})")

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
