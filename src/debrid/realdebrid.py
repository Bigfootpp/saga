import json
import time
from urllib.parse import unquote

from constants import NO_CACHE_VIDEO_URL
from debrid.availability import AvailabilityResult
from debrid.base_debrid import BaseDebrid
from models.config import Config
from torrent.magnet import get_info_hash_from_magnet
from torrent.matching import is_video_file, season_episode_in_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RealDebrid(BaseDebrid):
    def __init__(self, config: Config):
        super().__init__(config)
        self.base_url = "https://api.real-debrid.com"
        self.headers = {"Authorization": f"Bearer {self.config.debrid_key}"}

    def add_magnet(self, magnet: str, ip: str | None = None) -> dict:
        url = f"{self.base_url}/rest/1.0/torrents/addMagnet"
        data = {"magnet": magnet}
        result = self.get_json_response(
            url, method="post", headers=self.headers, data=data
        )
        return result if result is not None else {}

    def add_torrent(self, torrent_file: bytes) -> dict:
        url = f"{self.base_url}/rest/1.0/torrents/addTorrent"
        result = self.get_json_response(
            url, method="put", headers=self.headers, data=torrent_file
        )
        return result if result is not None else {}

    def delete_torrent(self, id: str) -> dict:
        url = f"{self.base_url}/rest/1.0/torrents/delete/{id}"
        result = self.get_json_response(url, method="delete", headers=self.headers)
        return result if result is not None else {}

    def get_torrent_info(self, torrent_id: str) -> dict | None:
        logger.info(f"Getting torrent info for: {torrent_id}")
        url = f"{self.base_url}/rest/1.0/torrents/info/{torrent_id}"
        torrent_info = self.get_json_response(url, headers=self.headers)

        if not torrent_info or "files" not in torrent_info:
            return None

        return torrent_info

    def select_files(self, torrent_id: str, file_id: str) -> None:
        logger.info(f"Selecting file(s): {file_id}")
        url = f"{self.base_url}/rest/1.0/torrents/selectFiles/{torrent_id}"
        data = {"files": str(file_id)}
        self._session.post(url, headers=self.headers, data=data, timeout=10)

    def unrestrict_link(self, link: str) -> dict:
        url = f"{self.base_url}/rest/1.0/unrestrict/link"
        data = {"link": link}
        result = self.get_json_response(
            url, method="post", headers=self.headers, data=data
        )
        return result if result is not None else {}

    def wait_for_link(
        self, torrent_id: str, timeout: int = 30, interval: int = 5
    ) -> list:
        start_time = time.time()
        while time.time() - start_time < timeout:
            torrent_info = self.get_torrent_info(torrent_id)
            if (
                torrent_info
                and "links" in torrent_info
                and len(torrent_info["links"]) > 0
            ):
                return torrent_info["links"]
            time.sleep(interval)

        return []

    def get_availability_bulk(
        self, hashes_or_magnets: list[str], ip: str | None = None
    ) -> dict:
        if len(hashes_or_magnets) == 0:
            logger.info("No hashes to be sent to Real-Debrid.")
            return {}

        url = f"{self.base_url}/torrents/"
        result = self.get_json_response(url, headers=self.headers)
        if result is None:
            return {}
        ids = []
        for element in result.get("data", {}).get("hash", []):
            if element["hash"] in hashes_or_magnets:
                ids.append(element["id"])
        return result

    def get_stream_link(self, query_string: str, ip: str | None = None) -> str:
        query = json.loads(query_string)

        magnet = query["magnet"]
        stream_type = query["type"]
        file_index = (
            int(query["file_index"]) if query["file_index"] is not None else None
        )
        season = query["season"]
        episode = query["episode"]
        torrent_download = (
            unquote(query["torrent_download"])
            if query["torrent_download"] is not None
            else None
        )
        info_hash = get_info_hash_from_magnet(magnet)
        logger.info(
            f"RealDebrid get stream link for {stream_type} with hash: {info_hash}"
        )

        cached_torrent_ids = self._get_cached_torrent_ids(info_hash)
        logger.info(
            f"Found {len(cached_torrent_ids)} cached torrents with hash: {info_hash}"
        )

        torrent_info = None
        if len(cached_torrent_ids) > 0:
            if stream_type == "movie":
                torrent_info = self.get_torrent_info(cached_torrent_ids[0])
            elif stream_type == "series":
                torrent_info = self._get_cached_torrent_info(
                    cached_torrent_ids, file_index, season, episode
                )
            else:
                return "Error: Unsupported stream type."

        if torrent_info is None:
            torrent_info = self._add_magnet_or_torrent(magnet, torrent_download)
            if not torrent_info or "files" not in torrent_info:
                return "Error: Failed to get torrent info."

            logger.info("Selecting file")
            self._select_file(torrent_info, stream_type, file_index, season, episode)

            if (
                len(cached_torrent_ids) == 0
                and stream_type == "series"
                and len(torrent_info["files"]) > 5
            ):
                logger.info("Prefetching season pack")
                prefetched_torrent_info = self._prefetch_season_pack(
                    magnet, torrent_download
                )
                if len(prefetched_torrent_info["links"]) > 0:
                    self.delete_torrent(torrent_info["id"])
                    torrent_info = prefetched_torrent_info

        torrent_id = torrent_info["id"]
        logger.info(f"Waiting for the link(s) to be ready for torrent ID: {torrent_id}")
        links = self.wait_for_link(torrent_id)
        if links is None:
            return NO_CACHE_VIDEO_URL

        if len(links) > 1:
            logger.info("Finding appropriate link")
            download_link = self._find_appropriate_link(
                torrent_info, links, file_index, season, episode
            )
        else:
            download_link = links[0]

        logger.info(f"Unrestricting the download link: {download_link}")
        unrestrict_response = self.unrestrict_link(download_link)
        if not unrestrict_response or "download" not in unrestrict_response:
            return "Error: Failed to unrestrict link."

        logger.info(f"Got download link: {unrestrict_response['download']}")
        return unrestrict_response["download"]

    def _get_cached_torrent_ids(self, info_hash: str | None) -> list[str]:
        if info_hash is None:
            return []
        url = f"{self.base_url}/rest/1.0/torrents"
        torrents = self.get_json_response(url, headers=self.headers)

        logger.info(f"Searching users real-debrid downloads for {info_hash}")
        torrent_ids = []
        if torrents is None:
            return torrent_ids
        for torrent in torrents:
            if torrent["hash"].lower() == info_hash:
                torrent_ids.append(torrent["id"])

        return torrent_ids

    def _get_cached_torrent_info(
        self, cached_ids: list[str], file_index: int | None, season: str, episode: str
    ) -> dict | None:
        cached_torrents = []
        for cached_torrent_id in cached_ids:
            cached_torrent_info = self.get_torrent_info(cached_torrent_id)
            if cached_torrent_info is None:
                continue
            if self._torrent_contains_file(
                cached_torrent_info, file_index, season, episode
            ):
                if (
                    cached_torrent_info.get("links")
                    and len(cached_torrent_info["links"]) > 0
                ):
                    return cached_torrent_info

                cached_torrents.append(cached_torrent_info)

        if len(cached_torrents) == 0:
            return None

        return max(cached_torrents, key=lambda x: x.get("progress", 0))

    def _torrent_contains_file(
        self, torrent_info: dict, file_index: int | None, season: str, episode: str
    ) -> bool:
        if not torrent_info or "files" not in torrent_info:
            return False

        if file_index is None:
            for file in torrent_info["files"]:
                if file["selected"] and season_episode_in_filename(
                    file["path"], season, episode
                ):
                    return True
        else:
            for file in torrent_info["files"]:
                if file["id"] == file_index:
                    return file["selected"] == 1

        return False

    def _add_magnet_or_torrent(
        self, magnet: str, torrent_download: str | None = None
    ) -> dict:
        torrent_id = ""
        if torrent_download is None:
            logger.info("Adding magnet to RealDebrid")
            magnet_response = self.add_magnet(magnet)
            logger.info(f"RealDebrid add magnet response: {magnet_response}")

            if not magnet_response or "id" not in magnet_response:
                return {}

            torrent_id = magnet_response["id"]
        else:
            logger.info("Downloading torrent file from Jackett")
            torrent_file = self.download_torrent_file(torrent_download)
            logger.info("Torrent file downloaded from Jackett")

            logger.info("Adding torrent file to RealDebrid")
            upload_response = self.add_torrent(torrent_file)
            logger.info(f"RealDebrid add torrent file response: {upload_response}")

            if not upload_response or "id" not in upload_response:
                return {}

            torrent_id = upload_response["id"]

        logger.info(f"New torrent ID: {torrent_id}")
        result = self.get_torrent_info(torrent_id)
        return result if result is not None else {}

    def _prefetch_season_pack(self, magnet: str, torrent_download: str | None) -> dict:
        torrent_info = self._add_magnet_or_torrent(magnet, torrent_download)
        if not torrent_info or "files" not in torrent_info:
            return {}
        video_file_indexes = []

        for file in torrent_info["files"]:
            if is_video_file(file["path"]):
                video_file_indexes.append(str(file["id"]))

        self.select_files(torrent_info["id"], ",".join(video_file_indexes))
        time.sleep(10)
        result = self.get_torrent_info(torrent_info["id"])
        return result if result is not None else {}

    def _select_file(
        self,
        torrent_info: dict,
        stream_type: str,
        file_index: int | None,
        season: str,
        episode: str,
    ) -> None:
        torrent_id = torrent_info.get("id", "")
        if file_index is not None:
            logger.info(f"Selecting file_index: {file_index}")
            self.select_files(torrent_id, str(file_index))
            return

        files = torrent_info.get("files", [])
        if stream_type == "movie":
            if files:
                largest_file_id = max(files, key=lambda x: x.get("bytes", 0))["id"]
                logger.info(f"Selecting file_index: {largest_file_id}")
                self.select_files(torrent_id, str(largest_file_id))
        elif stream_type == "series":
            strict_matching_files = []
            matching_files = []
            for file in files:
                if season_episode_in_filename(file["path"], season, episode):
                    strict_matching_files.append(file)
                elif season_episode_in_filename(file["path"], season, episode):
                    matching_files.append(file)

            if len(strict_matching_files) > 0:
                matching_files = strict_matching_files

            if matching_files:
                largest_file_id = max(matching_files, key=lambda x: x.get("bytes", 0))[
                    "id"
                ]
                logger.info(f"Selecting file_index: {largest_file_id}")
                self.select_files(torrent_id, str(largest_file_id))

    def _find_appropriate_link(
        self,
        torrent_info: dict,
        links: list[str],
        file_index: int | None,
        season: str,
        episode: str,
    ) -> str:
        selected_files = list(
            filter(
                lambda file: file.get("selected") == 1, torrent_info.get("files", [])
            )
        )

        index = 0
        if file_index is not None:
            for file in selected_files:
                if file.get("id") == file_index:
                    break
                index += 1
        else:
            matching_indexes = []
            strict_matching_indexes = []
            for file in selected_files:
                if season_episode_in_filename(file.get("path", ""), season, episode):
                    strict_matching_indexes.append({"index": index, "file": file})
                elif season_episode_in_filename(file.get("path", ""), season, episode):
                    matching_indexes.append({"index": index, "file": file})
                index += 1

            if len(strict_matching_indexes) > 0:
                matching_indexes = strict_matching_indexes

            if matching_indexes:
                index = max(matching_indexes, key=lambda x: x["file"].get("bytes", 0))[
                    "index"
                ]

        if len(links) - 1 < index:
            logger.debug(
                f"From selected files {selected_files}, index: {index} is out of range for {links}."
            )
            return NO_CACHE_VIDEO_URL

        return links[index]

    def extract_availability(
        self, response: dict, hashes: list[str], media
    ) -> "AvailabilityResult":
        return AvailabilityResult()
