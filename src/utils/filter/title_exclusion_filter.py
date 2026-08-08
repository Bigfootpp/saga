from typing import Any

from utils.filter.base_filter import BaseFilter


class TitleExclusionFilter(BaseFilter):
    def filter(self, data: list[Any]) -> list[Any]:
        filtered_items = []
        excluded_keywords = [
            keyword.upper() for keyword in self.config.exclusion_keywords
        ]
        for stream in data:
            raw_title = (stream.raw_title or "").upper()
            for keyword in excluded_keywords:
                if keyword in raw_title:
                    break
            else:
                filtered_items.append(stream)
        return filtered_items

    def can_filter(self) -> bool:
        return len(self.config.exclusion_keywords) > 0
