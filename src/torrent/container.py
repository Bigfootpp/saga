from __future__ import annotations

from typing import TYPE_CHECKING

from torrent.torrent_item import TorrentItem
from utils.logger import setup_logger

if TYPE_CHECKING:
    from models.media import Media


class TorrentContainer:
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

    def get_best_matching(self) -> list[TorrentItem]:
        best_matching = []
        self.logger.debug(f"Amount of items: {len(self._items_dict)}")
        for torrent_item in self._items_dict.values():
            if torrent_item.torrent_download is not None:
                torrent_item.file_index = torrent_item.file_index or 0
            best_matching.append(torrent_item)
        return best_matching

    def _build_items_dict_by_infohash(
        self, items: list[TorrentItem]
    ) -> dict[str, TorrentItem]:
        self.logger.debug(f"Building items dict by infohash ({len(items)} items)")
        items_dict: dict[str, TorrentItem] = {}
        for item in items:
            if item.info_hash is not None:
                items_dict[item.info_hash] = item
            else:
                self.logger.warning(f"Could not find info hash for {item.raw_title}")
        return items_dict
