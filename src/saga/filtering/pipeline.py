from RTN import RTN, DefaultRanking, SettingsModel, sort_torrents, title_match

from saga.filtering.language_filter import LanguageFilter
from saga.jackett.jackett_result import JackettResult
from saga.models.config import Config
from saga.models.media import Media
from saga.models.series import Series
from saga.torrent.torrent_item import TorrentItem
from saga.utils.logger import setup_logger

logger = setup_logger(__name__)

quality_order: dict[str, int] = {
    "4k": 0,
    "2160p": 0,
    "1080p": 1,
    "720p": 2,
    "480p": 3,
}


def sort_quality(item: TorrentItem) -> tuple[float, bool]:
    if item.parsed_data is None or item.parsed_data.resolution is None:
        return float("inf"), True
    return quality_order.get(item.parsed_data.resolution, float("inf")), False


def items_sort(items: list[TorrentItem], config: Config) -> list[TorrentItem]:
    valid_items = [item for item in items if item.info_hash]
    if len(valid_items) != len(items):
        logger.warning(
            f"Filtered out {len(items) - len(valid_items)} items with empty info_hash before sorting"
        )

    settings = SettingsModel(
        require=[],
        exclude=[],
    )

    rtn = RTN(settings=settings, ranking_model=DefaultRanking())
    torrents = [rtn.rank(item.raw_title, item.info_hash) for item in valid_items]
    sorted_torrents = sort_torrents(set(torrents))
    for key, rank in sorted_torrents.items():
        index = next(
            (i for i, item in enumerate(valid_items) if item.info_hash == key), None
        )
        if index is not None:
            valid_items[index].parsed_data = rank.data

    # Sort by quality (default), no other sort options
    return sorted(valid_items, key=sort_quality)


def sort_items(items: list[TorrentItem], config: Config) -> list[TorrentItem]:
    return items_sort(items, config)


def filter_out_non_matching(
    items: list[JackettResult], season: str, episode: str
) -> list[JackettResult]:
    filtered_items = []
    numeric_season = int(season.replace("S", ""))
    numeric_episode = int(episode.replace("E", ""))
    for item in items:
        parsed_data = item.parsed_data
        if parsed_data is None:
            continue
        try:
            if len(parsed_data.seasons) == 0 and len(parsed_data.episodes) == 0:
                continue

            if len(parsed_data.episodes) == 0 and numeric_season in parsed_data.seasons:
                filtered_items.append(item)
                continue
            if (
                numeric_season in parsed_data.seasons
                and numeric_episode in parsed_data.episodes
            ):
                filtered_items.append(item)
                continue
        except Exception:
            logger.exception("Error while filtering out non matching torrents")
    return filtered_items


def remove_non_matching_title(
    items: list[JackettResult], titles: list[str]
) -> list[JackettResult]:
    filtered_items = []
    for item in items:
        if item.parsed_data is None:
            continue
        for title in titles:
            if not title_match(title, item.parsed_data.parsed_title):
                continue
            filtered_items.append(item)
            break

    return filtered_items


def filter_items(
    items: list[JackettResult], media: Media, config: Config
) -> list[JackettResult]:
    logger.info(f"Item count before filtering: {len(items)}")

    if isinstance(media, Series):
        logger.info("Filtering out non matching series torrents")
        items = filter_out_non_matching(items, media.season, media.episode)
        items = remove_non_matching_title(items, media.titles)
        logger.info(f"Item count changed to {len(items)}")

    # Language filter only
    language_filter = LanguageFilter(config)
    try:
        logger.info(f"Filtering by languages: {config.languages}")
        items = language_filter(items)
        logger.info(f"Item count changed to {len(items)}")
    except Exception:
        logger.exception("Error while filtering by languages")

    logger.info(f"Item count after filtering: {len(items)}")
    logger.info("Finished filtering torrents")

    return items
