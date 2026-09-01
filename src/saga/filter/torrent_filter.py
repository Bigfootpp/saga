from RTN import parse

from saga.models.query import MediaQuery, MovieQuery, SeriesQuery
from saga.models.torrent import RawTorrent


def _filter_raw_torrents_series(
    raw_torrent: list[RawTorrent], query: SeriesQuery
) -> list[RawTorrent]:
    result: list[RawTorrent] = []
    for torrent in raw_torrent:
        parsed_data = parse(torrent.title)
        episode = query.episode
        season = query.season
        if not parsed_data.seasons and not parsed_data.episodes:
            result.append(torrent)
            continue
        if season in parsed_data.seasons and not parsed_data.episodes:
            result.append(torrent)
            continue
        if season in parsed_data.seasons and episode in parsed_data.episodes:
            result.append(torrent)
            continue

    return result


def _filter_raw_torrents_movie(
    raw_torrents: list[RawTorrent], query: MovieQuery
) -> list[RawTorrent]:
    result: list[RawTorrent] = []
    for torrent in raw_torrents:
        parsed_data = parse(torrent.title)
        if not parsed_data.seasons and not parsed_data.episodes:
            result.append(torrent)
            continue

    return result


def filter_raw_torrents(
    raw_torrents: list[RawTorrent], query: MediaQuery
) -> list[RawTorrent]:
    if isinstance(query, SeriesQuery):
        return _filter_raw_torrents_series(raw_torrents, query)
    if isinstance(query, MovieQuery):
        return _filter_raw_torrents_movie(raw_torrents, query)
    return []
