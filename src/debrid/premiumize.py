import json

from constants import NO_CACHE_VIDEO_URL
from debrid.availability import AvailabilityResult
from debrid.base_debrid import BaseDebrid
from models.config import Config
from torrent.magnet import get_info_hash_from_magnet
from torrent.matching import season_episode_in_filename
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Premiumize(BaseDebrid):
    def __init__(self, config: Config):
        super().__init__(config)
        self.base_url = "https://www.premiumize.me/api"

    def add_magnet(self, magnet: str, ip: str | None = None) -> dict:
        url = f"{self.base_url}/transfer/create?apikey={self.config.debrid_key}"
        form = {"src": magnet}
        result = self.get_json_response(url, method="post", data=form)
        return result if result is not None else {}

    def add_torrent(self, torrent_file: bytes) -> dict:
        url = f"{self.base_url}/transfer/create?apikey={self.config.debrid_key}"
        form = {"file": torrent_file}
        result = self.get_json_response(url, method="post", data=form)
        return result if result is not None else {}

    def list_transfers(self) -> dict:
        url = f"{self.base_url}/transfer/list?apikey={self.config.debrid_key}"
        result = self.get_json_response(url)
        return result if result is not None else {}

    def get_folder_or_file_details(self, item_id: str, is_folder: bool = True) -> dict:
        if is_folder:
            logger.info(f"Getting folder details with id: {item_id}")
            url = f"{self.base_url}/folder/list?id={item_id}&apikey={self.config.debrid_key}"
        else:
            logger.info(f"Getting file details with id: {item_id}")
            url = f"{self.base_url}/item/details?id={item_id}&apikey={self.config.debrid_key}"
        result = self.get_json_response(url)
        return result if result is not None else {}

    def get_availability(self, hash: str | None = None) -> dict:
        if hash is None:
            return {}
        url = f"{self.base_url}/cache/check?apikey={self.config.debrid_key}&items[]={hash}"
        result = self.get_json_response(url)
        return result if result is not None else {}

    def get_availability_bulk(
        self, hashes_or_magnets: list[str], ip: str | None = None
    ) -> dict:
        url = (
            f"{self.base_url}/cache/check?apikey={self.config.debrid_key}&items[]="
            + "&items[]=".join(hashes_or_magnets)
        )
        result = self.get_json_response(url)
        return result if result is not None else {}

    def get_stream_link(self, query_string: str, ip: str | None = None) -> str:
        query_dict = json.loads(query_string)
        magnet = query_dict["magnet"]
        logger.info(f"Received query for magnet: {magnet}")
        info_hash = get_info_hash_from_magnet(magnet)
        logger.info(f"Info hash extracted: {info_hash}")
        stream_type = query_dict["type"]
        logger.info(f"Stream type: {stream_type}")

        transfer_data = self.add_magnet(magnet)
        if not transfer_data or "id" not in transfer_data:
            logger.error("Failed to create transfer.")
            return "Error: Failed to create transfer."
        transfer_id = transfer_data["id"]
        logger.info(f"Transfer created with ID: {transfer_id}")

        if not self.wait_for_ready_status(
            lambda: self.get_availability(info_hash)["transcoded"][0] is True
        ):
            logger.info("Torrent not ready, caching in progress")
            return NO_CACHE_VIDEO_URL

        logger.info("Torrent is ready.")

        transfers = self.list_transfers()
        item_id, is_folder = None, False
        for item in transfers.get("transfers", []):
            if item["id"] == transfer_id:
                if item.get("folder_id"):
                    item_id = item["folder_id"]
                    is_folder = True
                else:
                    item_id = item["file_id"]
                break

        if not item_id:
            logger.error("Transfer completed but no item ID found.")
            return "Error: Transfer completed but no item ID found."

        details = self.get_folder_or_file_details(item_id, is_folder)
        logger.info("Got details")

        if stream_type == "movie":
            logger.info("Getting link for movie")
            if is_folder:
                content = details.get("content", [])
                if content:
                    link = max(content, key=lambda x: x.get("size", 0)).get("link", "")
                else:
                    link = ""
            else:
                link = details.get("link", "")
        elif stream_type == "series":
            logger.info("Getting link for series")
            if is_folder:
                season = query_dict["season"]
                episode = query_dict["episode"]
                files = details.get("content", [])
                matching_files = []

                for file in files:
                    if season_episode_in_filename(
                        file.get("name", ""), season, episode
                    ):
                        matching_files.append(file)

                if len(matching_files) == 0:
                    logger.error(
                        f"No matching files for {season} {episode} in torrent."
                    )
                    return (
                        f"Error: No matching files for {season} {episode} in torrent."
                    )

                link = max(matching_files, key=lambda x: x.get("size", 0)).get(
                    "link", ""
                )
            else:
                link = details.get("link", "")
        else:
            logger.error("Unsupported stream type.")
            return "Error: Unsupported stream type."

        if not link:
            return NO_CACHE_VIDEO_URL

        logger.info(f"Link generated: {link}")
        return link

    def extract_availability(
        self, response: dict, hashes: list[str], media
    ) -> "AvailabilityResult":
        from debrid.availability import AvailabilityResult

        result = AvailabilityResult()
        if "response" not in response or "transcoded" not in response:
            return result

        responses = response["response"]
        transcoded = response["transcoded"]

        for i, torrent_hash in enumerate(hashes):
            if i < len(responses) and responses[i]:
                result.flags[torrent_hash] = transcoded[i] is True
        return result
