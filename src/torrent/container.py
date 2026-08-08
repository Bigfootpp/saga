from __future__ import annotations

from typing import TYPE_CHECKING

from debrid.availability import AvailabilityResult, FileEntry
from torrent.torrent_item import TorrentItem
from utils.logger import setup_logger

if TYPE_CHECKING:
    from models.media import Media


class TorrentSmartContainer:
    def __init__(self, torrent_items: list[TorrentItem], media: Media | None):
        self.logger = setup_logger(__name__)
        self._items_dict: dict[str, TorrentItem] = self._build_items_dict_by_infohash(
            torrent_items
        )

    def get_hashes(self) -> list[str]:
        return list(self._items_dict.keys())

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

    def apply_availability(self, result: AvailabilityResult) -> None:
        """Apply normalized availability data from a debrid provider."""
        for info_hash, files in result.files.items():
            torrent_item = self._items_dict.get(info_hash)
            if torrent_item and files:
                self._update_file_details(torrent_item, files)

        for info_hash, flag in result.flags.items():
            torrent_item = self._items_dict.get(info_hash)
            if torrent_item:
                torrent_item.availability = flag

    def _update_file_details(
        self, torrent_item: TorrentItem, files: list[FileEntry]
    ) -> None:
        if len(files) == 0:
            return

        best_file = max(
            files, key=lambda f: int(f.size) if isinstance(f.size, str) else f.size
        )
        torrent_item.availability = True
        torrent_item.file_index = best_file.file_index
        torrent_item.file_name = best_file.title
        torrent_item.size = (
            int(best_file.size) if isinstance(best_file.size, str) else best_file.size
        )

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
