import hashlib
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict, cast

import bencode
import requests
from RTN import parse as rtn_parse

from jackett.jackett_result import JackettResult
from models.movie import Movie
from models.series import Series
from shared_types import TorrentFile, TorrentInfoDict, TorrentMetadata
from torrent.magnet import get_info_hash_from_magnet
from torrent.torrent_item import TorrentItem
from utils.logger import setup_logger


class FileEntryDict(TypedDict):
    file_index: int
    title: str
    size: int


class TorrentService:
    def __init__(self):
        self.logger = setup_logger(__name__)
        self._session = requests.Session()

    def convert_and_process(
        self, results: list[JackettResult], media: Movie | Series
    ) -> list[TorrentItem]:
        torrent_items_result = []

        def process_result(result: JackettResult) -> TorrentItem:
            torrent_item = result.convert_to_torrent_item()

            if torrent_item.link.startswith("magnet:"):
                return self._process_magnet(torrent_item)
            return self._process_web_url(torrent_item, media)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_result, result) for result in results]
            for future in futures:
                try:
                    torrent_items_result.append(future.result())
                except (RuntimeError, ValueError) as e:
                    self.logger.error(f"Error processing torrent: {e}")

        return torrent_items_result

    def _process_web_url(
        self, result: TorrentItem, media: Movie | Series
    ) -> TorrentItem:
        timeout = float(os.environ.get("JACKETT_RESOLVER_TIMEOUT", "15"))
        try:
            response = self._session.get(
                result.link, allow_redirects=False, timeout=timeout
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
            return self._process_torrent(result, response.content, media)
        elif response.status_code == 302:
            result.magnet = response.headers["Location"]
            return self._process_magnet(result)
        else:
            self.logger.error(
                f"Error code {response.status_code} while processing url: {result.link}"
            )

        return result

    def _process_torrent(
        self, result: TorrentItem, torrent_file: bytes, media: Movie | Series
    ) -> TorrentItem:
        metadata: TorrentMetadata = bencode.bdecode(torrent_file)

        result.torrent_download = result.link
        result.trackers = self._get_trackers_from_torrent(metadata)
        result.info_hash = self._convert_torrent_to_hash(metadata["info"])
        result.magnet = self._build_magnet(
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

            file_details = self._find_episode_file(result.files, season, episode)

            if file_details is not None:
                result.file_index = cast(int | None, file_details["file_index"])
                result.file_name = cast(str | None, file_details["title"])
                result.size = cast(int, file_details["size"])
        else:
            result.file_index = self._find_movie_file(result.files)

        return result

    def _process_magnet(self, result: TorrentItem) -> TorrentItem:
        if not result.magnet:
            result.magnet = result.link

        if not result.info_hash:
            result.info_hash = get_info_hash_from_magnet(result.magnet)

        result.trackers = self._get_trackers_from_magnet(result.magnet)

        return result

    def _convert_torrent_to_hash(self, torrent_contents: TorrentInfoDict) -> str:
        hashcontents = bencode.bencode(torrent_contents)
        hex_hash = hashlib.sha1(hashcontents).hexdigest()
        return hex_hash.lower()

    def _build_magnet(self, hash_: str, display_name: str, trackers: list[str]) -> str:
        magnet_base = "magnet:?xt=urn:btih:"
        magnet = f"{magnet_base}{hash_}&dn={display_name}"

        if len(trackers) > 0:
            magnet = f"{magnet}&tr={'&tr='.join(trackers)}"

        return magnet

    def _get_trackers_from_torrent(
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

        trackers = []
        if "tr" in query_parts:
            trackers = query_parts["tr"]

        return trackers

    def _find_episode_file(
        self, file_structure: list[TorrentFile], season: int, episode: int
    ) -> dict[str, object] | None:
        file_index = 1
        episode_files: list[dict] = []
        for files in file_structure:
            for file in cast(list[str], files["path"]):
                parsed_file = rtn_parse(file)

                if season in parsed_file.seasons and episode in parsed_file.episodes:
                    episode_files.append(
                        {
                            "file_index": file_index,
                            "title": file,
                            "size": cast(int, files["length"]),
                        }
                    )

            file_index += 1

        return max(episode_files, key=lambda f: f["size"]) if episode_files else None

    def _find_movie_file(self, file_structure: list[TorrentFile]) -> int:
        max_size = 0
        max_file_index = 1
        current_file_index = 1
        for files in file_structure:
            if cast(int, files["length"]) > max_size:
                max_file_index = current_file_index
                max_size = cast(int, files["length"])
            current_file_index += 1

        return max_file_index
