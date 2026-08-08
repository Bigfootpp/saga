from typing import Any

from utils.filter.base_filter import BaseFilter


class MaxSizeFilter(BaseFilter):
    def filter(self, data: list[Any]) -> list[Any]:
        filtered_data = []
        for torrent in data:
            if int(torrent.size or 0) <= self.config.max_size:
                filtered_data.append(torrent)
        return filtered_data

    def can_filter(self) -> bool:
        return self.config.max_size > 0 and self.item_type == "movie"
