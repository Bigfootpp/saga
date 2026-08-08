from __future__ import annotations

from typing import TYPE_CHECKING, Any

from debrid.alldebrid import AllDebrid
from debrid.base_debrid import BaseDebrid
from debrid.premiumize import Premiumize
from debrid.realdebrid import RealDebrid
from debrid.torbox import TorBox
from torrent.torrent_item import TorrentItem
from utils.general import season_episode_in_filename
from utils.logger import setup_logger

if TYPE_CHECKING:
    from models.media import Media


class TorrentSmartContainer:
    def __init__(self, torrent_items: list[TorrentItem], media: Media | None):
        self.logger = setup_logger(__name__)
        self._items_dict: dict[str, TorrentItem] = self._build_items_dict_by_infohash(
            torrent_items
        )
        self._media = media

    def get_hashes(self) -> list[str]:
        return list(self._items_dict.keys())

    def get_items(self) -> list[TorrentItem]:
        return list(self._items_dict.values())

    def get_direct_torrentable(self) -> list[TorrentItem]:
        return [
            torrent_item
            for torrent_item in self._items_dict.values()
            if torrent_item.privacy == "public" and torrent_item.file_index is not None
        ]

    def get_best_matching(self) -> list[TorrentItem]:
        best_matching = []
        self.logger.debug(f"Amount of items: {len(self._items_dict)}")
        for torrent_item in self._items_dict.values():
            self.logger.debug("-------------------")
            self.logger.debug(f"Checking {torrent_item.raw_title}")
            self.logger.debug(
                f"Has torrent: {torrent_item.torrent_download is not None}"
            )
            if torrent_item.torrent_download is not None:
                self.logger.debug(
                    f"Has file index: {torrent_item.file_index is not None}"
                )
                torrent_item.file_index = torrent_item.file_index or 0
            best_matching.append(torrent_item)
        return best_matching

    def update_availability(
        self, debrid_response: dict, debrid_service: BaseDebrid, media: Media
    ) -> None:
        if isinstance(debrid_service, RealDebrid):
            self._update_availability_realdebrid(debrid_response, media)
        elif isinstance(debrid_service, AllDebrid):
            self._update_availability_alldebrid(debrid_response, media)
        elif isinstance(debrid_service, Premiumize):
            self._update_availability_premiumize(debrid_response)
        elif isinstance(debrid_service, TorBox):
            self._update_availability_torbox(debrid_response, media)
        else:
            raise NotImplementedError(
                f"Debrid type {type(debrid_service)} not supported"
            )

    def _get_season_episode(self, media: Media | None) -> tuple[str | None, str | None]:
        """Extract season and episode from media if it's a Series."""
        from models.series import Series

        if isinstance(media, Series):
            return media.season, media.episode
        return None, None

    def _update_availability_realdebrid(self, response: dict, media: Media) -> None:
        for info_hash, details in response.items():
            if "rd" not in details:
                continue

            torrent_item: TorrentItem = self._items_dict[info_hash]

            files: list[dict[str, Any]] = []
            self.logger.info(torrent_item.type)
            if torrent_item.type == "series":
                season, episode = self._get_season_episode(media)
                if season is None or episode is None:
                    return
                for variants in details["rd"]:
                    for file_index, file in variants.items():
                        self.logger.info(file["filename"])
                        clean_season = season.replace("S", "")
                        clean_episode = episode.replace("E", "")
                        numeric_season = int(clean_season)
                        numeric_episode = int(clean_episode)
                        if season_episode_in_filename(
                            file["filename"], numeric_season, numeric_episode
                        ):
                            self.logger.info("File details 2")
                            self.logger.info(file["filename"])
                            files.append(
                                {
                                    "file_index": file_index,
                                    "title": file["filename"],
                                    "size": file["filesize"],
                                }
                            )
            else:
                for variants in details["rd"]:
                    for file_index, file in variants.items():
                        self.logger.info("File details 3")
                        self.logger.info(file["filename"])
                        files.append(
                            {
                                "file_index": file_index,
                                "title": file["filename"],
                                "size": file["filesize"],
                            }
                        )

            self._update_file_details(torrent_item, files)

    def _update_availability_alldebrid(
        self, response: dict, media: Media | None
    ) -> None:
        if response.get("status") != "success":
            self.logger.error(f"Error while updating availability: {response}")
            return

        for data in response["data"]["magnets"]:
            if not data["instant"]:
                continue

            torrent_item: TorrentItem = self._items_dict[data["hash"]]

            files: list[dict[str, Any]] = []
            type_ = torrent_item.type or "movie"
            season, episode = self._get_season_episode(media)
            self._explore_folders(data["files"], files, 1, type_, season, episode)

            self._update_file_details(torrent_item, files)

    def _update_availability_torbox(self, response: dict, media: Media | None) -> None:
        for torrent_hash, data in response.items():
            if not torrent_hash or torrent_hash not in self._items_dict:
                self.logger.warning(f"Hash {torrent_hash} not found in itemsDict.")
                continue
            torrent_item: TorrentItem = self._items_dict[torrent_hash]
            files: list[dict[str, Any]] = []
            season, episode = self._get_season_episode(media)
            type_ = torrent_item.type or "movie"
            self._explore_folders(
                folder=data.get("files", []),
                files=files,
                file_index=1,
                type_=type_,
                season=season,
                episode=episode,
            )
            self._update_file_details(torrent_item, files)

    def _update_availability_premiumize(self, response: dict) -> None:
        if response.get("status") != "success":
            self.logger.error(f"Error while updating availability: {response}")
            return

        torrent_items = self.get_items()
        for i in range(len(response["response"])):
            if bool(response["response"][i]):
                torrent_items[i].availability = response["transcoded"][i] is True

    def _update_file_details(
        self, torrent_item: TorrentItem, files: list[dict[str, Any]]
    ) -> None:
        if len(files) == 0:
            return

        file = max(files, key=lambda f: f["size"])
        torrent_item.availability = True
        torrent_item.file_index = file["file_index"]
        torrent_item.file_name = file["title"]
        torrent_item.size = file["size"]

    def _build_items_dict_by_infohash(
        self, items: list[TorrentItem]
    ) -> dict[str, TorrentItem]:
        self.logger.debug(f"Building items dict by infohash ({len(items)} items)")
        items_dict: dict[str, TorrentItem] = {}
        for item in items:
            if item.info_hash is not None:
                self.logger.debug(f"Adding {item.info_hash} to items dict")
                if item.info_hash in items_dict:
                    self.logger.debug(f"Duplicate info hash found: {item.info_hash}")
                items_dict[item.info_hash] = item
            else:
                self.logger.warning(f"Could not find info hash for {item.raw_title}")
        return items_dict

    def _explore_folders(
        self,
        folder: list[dict[str, Any]] | None,
        files: list[dict[str, Any]],
        file_index: int,
        type_: str,
        season: str | None = None,
        episode: str | None = None,
    ) -> int:
        if folder is None:
            return file_index
        if season is None or episode is None:
            return file_index
        if type_ == "series":
            for file in folder:
                if "e" in file or "files" in file:
                    sub_folder = file.get("e") or file.get("files")
                    if isinstance(sub_folder, list):
                        file_index = self._explore_folders(
                            sub_folder, files, file_index, type_, season, episode
                        )
                    continue

                file_name = file.get("n") or file.get("name")
                file_size = file.get("s") or file.get("size", 0)
                if not file_name:
                    self.logger.warning(f"Filename missing for : {file}")
                    continue

                if season_episode_in_filename(file_name, season, episode):
                    files.append(
                        {
                            "file_index": file_index,
                            "title": file_name,
                            "size": file_size,
                        }
                    )
                file_index += 1

        elif type_ == "movie":
            file_index = 1
            for file in folder:
                if "e" in file or "files" in file:
                    sub_folder = file.get("e") or file.get("files")
                    if isinstance(sub_folder, list):
                        file_index = self._explore_folders(
                            sub_folder, files, file_index, type_
                        )
                    continue

                file_name = file.get("n") or file.get("name")
                file_size = file.get("s") or file.get("size", 0)

                if not file_name:
                    self.logger.warning(f"Filename missing for : {file}")
                    continue

                files.append(
                    {
                        "file_index": file_index,
                        "title": file_name,
                        "size": file_size,
                    }
                )
                file_index += 1

        return file_index
