import json
import uuid
from urllib.parse import unquote

from constants import NO_CACHE_VIDEO_URL
from debrid.availability import AvailabilityResult
from debrid.base_debrid import BaseDebrid
from models.config import Config
from torrent.matching import season_episode_in_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AllDebrid(BaseDebrid):
    def __init__(self, config: Config):
        super().__init__(config)
        self.base_url = "https://api.alldebrid.com/v4.1/"

    def add_magnet(self, magnet: str, ip: str | None = None) -> dict:
        url = f"{self.base_url}magnet/upload?agent=jackett&apikey={self.config.debrid_key}&magnet={magnet}&ip={ip}"
        result = self.get_json_response(url)
        return result if result is not None else {}

    def add_torrent(self, torrent_file: bytes, ip: str | None = None) -> dict:
        url = f"{self.base_url}magnet/upload/file?agent=jackett&apikey={self.config.debrid_key}&ip={ip}"
        files = {
            "files[0]": (
                str(uuid.uuid4()) + ".torrent",
                torrent_file,
                "application/x-bittorrent",
            )
        }
        result = self.get_json_response(url, method="post", files=files)
        return result if result is not None else {}

    def check_magnet_status(self, id: str, ip: str | None = None) -> dict:
        url = f"{self.base_url}magnet/status?agent=jackett&apikey={self.config.debrid_key}&id={id}&ip={ip}"
        result = self.get_json_response(url)
        return result if result is not None else {}

    def unrestrict_link(self, link: str, ip: str | None = None) -> dict:
        url = f"{self.base_url}link/unlock?agent=jackett&apikey={self.config.debrid_key}&link={link}&ip={ip}"
        result = self.get_json_response(url)
        return result if result is not None else {}

    def get_stream_link(self, query_string: str, ip: str | None = None) -> str:
        query = json.loads(query_string)

        magnet = query["magnet"]
        stream_type = query["type"]
        torrent_download = (
            unquote(query["torrent_download"])
            if query["torrent_download"] is not None
            else None
        )

        torrent_id = self._add_magnet_or_torrent(magnet, torrent_download, ip)
        logger.info(f"Torrent ID: {torrent_id}")

        if not self.wait_for_ready_status(
            lambda: (
                self.check_magnet_status(torrent_id, ip)
                .get("data", {})
                .get("magnets", {})
                .get("status")
                == "Ready"
            )
        ):
            logger.error("Torrent not ready, caching in progress.")
            return NO_CACHE_VIDEO_URL
        logger.info("Torrent is ready.")

        logger.info(f"Getting data for torrent id: {torrent_id}")
        status_data = self.check_magnet_status(torrent_id, ip)
        data = status_data.get("data", {})
        logger.info("Retrieved data for torrent id")

        link = NO_CACHE_VIDEO_URL
        if stream_type == "movie":
            logger.info("Getting link for movie")
            files = data.get("magnets", {}).get("files", [])
            if files:
                link = files[0].get("l", NO_CACHE_VIDEO_URL)
        elif stream_type == "series":
            season = query["season"]
            episode = query["episode"]
            logger.info(f"Getting link for series {season}, {episode}")
            matching_files = []
            rank = 0
            magnets_files = data.get("magnets", {}).get("files", [])
            if magnets_files and "e" in magnets_files[0]:
                for file in magnets_files[0].get("e", []):
                    if season_episode_in_filename(file.get("n", ""), season, episode):
                        matching_files.append(file)
                    rank += 1
            else:
                for file in magnets_files:
                    if season_episode_in_filename(file.get("n", ""), season, episode):
                        matching_files.append(file)
                    rank += 1

            if len(matching_files) == 0:
                logger.error(f"No matching files for {season} {episode} in torrent.")
                return f"Error: No matching files for {season} {episode} in torrent."

            link = max(matching_files, key=lambda x: x.get("s", 0)).get(
                "l", NO_CACHE_VIDEO_URL
            )
        else:
            logger.error("Unsupported stream type.")
            return "Error: Unsupported stream type."

        if link == NO_CACHE_VIDEO_URL:
            return link

        logger.info(f"Alldebrid link: {link}")

        unlocked_link_data = self.unrestrict_link(link, ip)

        if not unlocked_link_data:
            logger.error("Failed to unlock link.")
            return "Error: Failed to unlock link."

        logger.info(
            f"Unrestricted link: {unlocked_link_data.get('data', {}).get('link')}"
        )

        return unlocked_link_data.get("data", {}).get("link", NO_CACHE_VIDEO_URL)

    def get_availability_bulk(
        self, hashes_or_magnets: list[str], ip: str | None = None
    ) -> dict:
        torrents = f"{self.base_url}magnet/status?agent=jackett&apikey={self.config.debrid_key}&ip={ip}"
        result = self.get_json_response(torrents)
        if result is None:
            return {}
        ids = []
        for element in result.get("data", {}).get("magnets", []):
            if element.get("hash") in hashes_or_magnets:
                ids.append(element.get("id", ""))

        return {}

    def _add_magnet_or_torrent(
        self, magnet: str, torrent_download: str | None = None, ip: str | None = None
    ) -> str:
        torrent_id = ""
        if torrent_download is None:
            logger.info("Adding magnet to AllDebrid")
            magnet_response = self.add_magnet(magnet, ip)
            logger.info(f"AllDebrid add magnet response: {magnet_response}")

            if (
                not magnet_response
                or "status" not in magnet_response
                or magnet_response["status"] != "success"
            ):
                return ""

            magnets_data = magnet_response.get("data", {}).get("magnets", [])
            if magnets_data:
                torrent_id = magnets_data[0].get("id", "")
        else:
            logger.info("Downloading torrent file from Jackett")
            torrent_file = self.download_torrent_file(torrent_download)
            logger.info("Torrent file downloaded from Jackett")

            logger.info("Adding torrent file to AllDebrid")
            upload_response = self.add_torrent(torrent_file, ip)
            logger.info(f"AllDebrid add torrent file response: {upload_response}")

            if (
                not upload_response
                or "status" not in upload_response
                or upload_response["status"] != "success"
            ):
                return ""

            files_data = upload_response.get("data", {}).get("files", [])
            if files_data:
                torrent_id = files_data[0].get("id", "")

        logger.info(f"New torrent ID: {torrent_id}")
        return torrent_id

    def extract_availability(
        self, response: dict, hashes: list[str], media
    ) -> "AvailabilityResult":
        return AvailabilityResult()
