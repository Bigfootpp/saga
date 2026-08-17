from filtering.base_filter import BaseFilter
from jackett.jackett_result import JackettResult
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LanguageFilter(BaseFilter[JackettResult]):
    def filter(self, data: list[JackettResult]) -> list[JackettResult]:
        if self.config.get_all_languages:
            logger.info(
                "Skipping language filtering because of 'getAllLanguages' setting."
            )
            return data

        filtered_languages = set(self.config.languages)
        filtered_data = []
        for torrent in data:
            if len(torrent.languages) == 0:
                continue

            if torrent.languages and any(
                language in filtered_languages for language in torrent.languages
            ):
                filtered_data.append(torrent)
                continue

            if "multi" in torrent.languages:
                filtered_data.append(torrent)

        return filtered_data

    def can_filter(self) -> bool:
        return self.config.get_all_languages is not None
