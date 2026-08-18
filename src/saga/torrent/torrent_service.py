import asyncio
import hashlib
import os
import urllib.parse
from typing import TypedDict, cast

import bencode
import httpx
import requests
from RTN import parse as rtn_parse

from saga.jackett.jackett_result import JackettResult
from saga.models.media import Media
from saga.models.series import Series
from saga.shared_types import TorrentFile, TorrentInfoDict, TorrentMetadata
from saga.torrent.magnet import get_info_hash_from_magnet
from saga.torrent.torrent_item import TorrentItem
from saga.utils.logger import setup_logger


class FileEntryDict(TypedDict):
    file_index: int
    title: str
    size: int


class TorrentService:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self._session = httpx.AsyncClient()

    async def convert_and_process(
        self, results: list[JackettResult], media: Media
    ) -> list[TorrentItem]:
        semaphore = asyncio.Semaphore(10)

        async def process_result(result: JackettResult) -> TorrentItem:
            async with semaphore:
                torrent_item = result.convert_to_torrent_item()
                if torrent_item.link.startswith("magnet:"):
                    return await self._process_magnet(torrent_item)
                return await self._process_web_url(torrent_item, media)

        tasks = [process_result(r) for r in results]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        torrent_items_result = []
        for res in raw_results:
            if isinstance(res, (RuntimeError, ValueError)):
                self.logger.error(f"Error processing torrent: {res}")
            elif isinstance(res, Exception):
                self.logger.error(f"Unexpected error: {res}")
            else:
                torrent_items_result.append(res)

        return torrent_items_result

    async def _process_web_url(
        self, result: TorrentItem, media: Media
    ) -> TorrentItem:
        timeout = float(os.environ.get("JACKETT_RESOLVER_TIMEOUT", "15"))
        try:
            response = await self._session.get(
                result.link, follow_redirects=False, timeout=timeout
            )
        except requests.exceptions.ReadTimeout:
            self.logger.error(
                f"Timeout while processing url (took longer than {timeout} seconds)"
            )
            return result
        except requests.exceptions.RequestException:
            self.logger.error(f"Error while processing url: {result.link}")
            return result

        if response.status_code == 200:
            return await self._process_torrent(result, response.content, media)
        elif response.status_code == 302:
            result.magnet = response.headers["Location"]
            return await self._process_magnet(result)
        else:
            self.logger.error(
                f"Error code {response.status_code} while processing url: {result.link}"
            )

        return result

    async def _process_torrent(
        self, result: TorrentItem, torrent_file: bytes, media: Media
    ) -> TorrentItem:
        metadata: TorrentMetadata = bencode.bdecode(torrent_file)

        result.torrent_download = result.link
        result.trackers = await self._get_trackers_from_torrent(metadata)
        result.info_hash = await self._convert_torrent_to_hash(metadata["info"])
        result.magnet = await self._build_magnet(
            result.info_hash, metadata["info"]["name"], result.trackers
        )

        if "files" not in metadata["info"]:
            result.file_index = 1
            return result

        result.files = list(metadata["info"]["files"])

        if result.files is None:
            return result

        if result.type == "series" and isinstance(media, Series):
            season = int(media.season.replace("S", ""))
            episode = int(media.episode.replace("E", ""))

            episode_file = self._find_episode_file(result.files, season, episode)

            if episode_file is not None:
                file_index, file_details = episode_file
                result.file_index = cast(int | None, file_index)
                result.file_name = cast(str | None, file_details["path"][-1])
                result.size = cast(int, file_details["length"])
        else:
            result.file_index = self._find_movie_file(result.files)

        return result

    async def _process_magnet(self, result: TorrentItem) -> TorrentItem:
        if not result.magnet:
            result.magnet = result.link

        if not result.info_hash:
            result.info_hash = get_info_hash_from_magnet(result.magnet)

        result.trackers = self._get_trackers_from_magnet(result.magnet)

        return result

    async def _convert_torrent_to_hash(self, torrent_contents: TorrentInfoDict) -> str:
        hashcontents = bencode.bencode(torrent_contents)
        hex_hash = hashlib.sha1(hashcontents).hexdigest()
        return hex_hash.lower()

    async def _build_magnet(self, hash_: str, display_name: str, trackers: list[str]) -> str:
        magnet_base = "magnet:?xt=urn:btih:"
        magnet = f"{magnet_base}{hash_}&dn={display_name}"

        if len(trackers) > 0:
            magnet = f"{magnet}&tr={'&tr='.join(trackers)}"

        return magnet

    async def _get_trackers_from_torrent(
        self, torrent_metadata: TorrentMetadata
    ) -> list[str]:
        announce = torrent_metadata.get("announce", [])
        announce_list = torrent_metadata.get("announce-list", [])

        trackers = set()
        if isinstance(announce, str):
            trackers.add(announce)
        elif isinstance(announce, list):
            for tracker in announce:
                trackers.add(tracker)

        for announce_list_item in announce_list:
            if isinstance(announce_list_item, list):
                for tracker in announce_list_item:
                    trackers.add(tracker)
            if isinstance(announce_list_item, str):
                trackers.add(announce_list_item)

        return list(trackers)

    def _get_trackers_from_magnet(self, magnet: str) -> list[str]:
        url_parts = urllib.parse.urlparse(magnet)
        query_parts = urllib.parse.parse_qs(url_parts.query)
        return query_parts.get("tr", [])

    def _find_episode_file(
        self, file_structure: list[TorrentFile], season: int, episode: int
    ) -> tuple[int, TorrentFile] | None:
        biggest_idx: int | None = None
        largest_size: int = 0
        for file_index, files in enumerate(file_structure):
            parsed_file = rtn_parse(files["path"][-1])

            if season in parsed_file.seasons and episode in parsed_file.episodes and files["length"] > largest_size:
                biggest_idx = file_index
                largest_size = files["length"]

        if biggest_idx is not None:
            return biggest_idx, file_structure[biggest_idx]
        return None

    def _find_movie_file(self, file_structure: list[TorrentFile]) -> int:
        max_size = 0
        max_file_index = 1
        for idx, files in enumerate(file_structure):
            if files["length"] > max_size:
                max_file_index = idx
                max_size = cast(int, files["length"])

        return max_file_index
