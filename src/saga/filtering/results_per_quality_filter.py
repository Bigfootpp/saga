from saga.filtering.base_filter import BaseFilter
from saga.jackett.jackett_result import JackettResult


class ResultsPerQualityFilter(BaseFilter[JackettResult]):
    def filter(self, data: list[JackettResult]) -> list[JackettResult]:
        filtered_items = []
        resolution_count: dict[str, int] = {}
        max_per_quality = int(self.config.results_per_quality or 0)
        for item in data:
            resolution = item.parsed_data.resolution if item.parsed_data else "unknown"
            if resolution not in resolution_count:
                resolution_count[resolution] = 1
                filtered_items.append(item)
            else:
                if resolution_count[resolution] < max_per_quality:
                    resolution_count[resolution] += 1
                    filtered_items.append(item)
        return filtered_items

    def can_filter(self) -> bool:
        return (
            self.config.results_per_quality is not None
            and int(self.config.results_per_quality) > 0
        )
