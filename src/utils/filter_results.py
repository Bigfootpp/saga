from RTN import RTN, DefaultRanking, SettingsModel, sort_torrents, title_match

from utils.filter.language_filter import LanguageFilter
from utils.filter.max_size_filter import MaxSizeFilter
from utils.filter.quality_exclusion_filter import QualityExclusionFilter
from utils.filter.results_per_quality_filter import ResultsPerQualityFilter
from utils.filter.title_exclusion_filter import TitleExclusionFilter
from utils.logger import setup_logger

logger = setup_logger(__name__)

quality_order = {"4k": 0, "2160p": 0, "1080p": 1, "720p": 2, "480p": 3}


def sort_quality(item):
    if item.parsed_data.data.resolution is None:
        return float("inf"), True

    return quality_order.get(
        item.parsed_data.data.resolution, float("inf")
    ), item.parsed_data.data.resolution is None


def items_sort(items, config):
    # Filter out items with empty info_hash (RTN requires both title and infohash)
    valid_items = [item for item in items if item.info_hash]
    if len(valid_items) != len(items):
        logger.warning(f"Filtered out {len(items) - len(valid_items)} items with empty info_hash before sorting")

    settings = SettingsModel(
        require=[],
        exclude=config.exclusionKeywords + config.exclusion,
    )

    rtn = RTN(settings=settings, ranking_model=DefaultRanking())
    torrents = [rtn.rank(item.raw_title, item.info_hash) for item in valid_items]
    sorted_torrents = sort_torrents(set(torrents))
    for key, value in sorted_torrents.items():
        index = next((i for i, item in enumerate(valid_items) if item.info_hash == key), None)
        if index is not None:
            valid_items[index].parsed_data = value

    if config.sort == "quality":
        return sorted(valid_items, key=sort_quality)
    if config.sort == "sizeasc":
        return sorted(valid_items, key=lambda x: int(x.size))
    if config.sort == "seedsdesc":
        return sorted(valid_items, key=lambda x: int(x.seeders), reverse=True)
    if config.sort == "sizedesc":
        return sorted(valid_items, key=lambda x: int(x.size), reverse=True)
    if config.sort == "qualitythensize":
        return sorted(valid_items, key=lambda x: (sort_quality(x), -int(x.size)))
    return valid_items


def filter_out_non_matching(items, season, episode):
    filtered_items = []
    for item in items:
        logger.info(season)
        logger.info(episode)
        logger.info(item.parsed_data)
        clean_season = season.replace("S", "")
        clean_episode = episode.replace("E", "")
        numeric_season = int(clean_season)
        numeric_episode = int(clean_episode)
        try:
            if (
                len(item.parsed_data.seasons) == 0
                and len(item.parsed_data.episodes) == 0
            ):
                continue

            if (
                len(item.parsed_data.episodes) == 0
                and numeric_season in item.parsed_data.seasons
            ):
                filtered_items.append(item)
                continue
            if (
                numeric_season in item.parsed_data.seasons
                and numeric_episode in item.parsed_data.episodes
            ):
                filtered_items.append(item)
                continue
        except Exception as e:
            logger.error("Error while filtering out non matching torrents", exc_info=e)
    return filtered_items


def remove_non_matching_title(items, titles):
    logger.info(titles)
    filtered_items = []
    for item in items:
        for title in titles:
            if not title_match(title, item.parsed_data.parsed_title):
                continue

            filtered_items.append(item)
            break

    return filtered_items


def filter_items(items, media, config):
    filters = {
        "languages": LanguageFilter(config),
        "maxSize": MaxSizeFilter(config, media.type),
        "exclusionKeywords": TitleExclusionFilter(config),
        "exclusion": QualityExclusionFilter(config),
        "resultsPerQuality": ResultsPerQualityFilter(config),
    }

    logger.info(f"Item count before filtering: {len(items)}")
    if media.type == "series":
        logger.info("Filtering out non matching series torrents")
        items = filter_out_non_matching(items, media.season, media.episode)
        logger.info(f"Item count changed to {len(items)}")

    items = remove_non_matching_title(items, media.titles)

    for filter_name, filter_instance in filters.items():
        try:
            logger.info(
                f"Filtering by {filter_name}: {config.__dict__.get(filter_name)}"
            )
            items = filter_instance(items)
            logger.info(f"Item count changed to {len(items)}")
        except Exception as e:
            logger.error(f"Error while filtering by {filter_name}", exc_info=e)
    logger.info(f"Item count after filtering: {len(items)}")
    logger.info("Finished filtering torrents")

    return items


def sort_items(items, config):
    if config.sort is not None:
        return items_sort(items, config)
    else:
        return items
