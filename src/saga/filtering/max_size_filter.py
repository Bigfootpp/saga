from saga.filtering.base_filter import BaseFilter
from saga.jackett.jackett_result import JackettResult


class MaxSizeFilter(BaseFilter[JackettResult]):
    def filter(self, data: list[JackettResult]) -> list[JackettResult]:
        filtered_data = []
        for torrent in data:
            if int(torrent.size or 0) <= self.config.max_size:
                filtered_data.append(torrent)
        return filtered_data

    def can_filter(self) -> bool:
        return self.config.max_size > 0 and self.item_type == "movie"
