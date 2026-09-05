from urllib.parse import parse_qs, urlparse

from saga.models.query import MediaQuery, MovieQuery, SeriesQuery
from saga.models.stream import Stream
from saga.models.torrent import RawTorrent, ResolvedTorrent, TorrentFileEntry
from saga.utils.guessit import parse


class NoMatchError(Exception):
    pass


def _valid_file(file: TorrentFileEntry, season: int) -> bool:
    parsed_file_name_data = parse(file.file_name)
    if not parsed_file_name_data.seasons:
        return True
    return (
        len(parsed_file_name_data.seasons) == 1
        and season in parsed_file_name_data.seasons
    )


def _find_file_idx_series(torrent: ResolvedTorrent, query: SeriesQuery) -> Stream:
    parsed_torrent_name = parse(torrent.title)
    for file in torrent.files:
        if not _valid_file(file, query.season):
            continue
        parsed_file_name = parse(file.file_name)
        if (
            parsed_file_name.episodes
            and len(parsed_file_name.episodes) == 1
            and query.episode in parsed_file_name.episodes
        ):
            return Stream(
                raw_name=file.file_name,
                title=parsed_file_name.title or "",
                info_hash=torrent.info_hash,
                dubs_language=parsed_torrent_name.audio_languages,
                sources=parse_trackers(torrent.magnet),
                file_idx=file.file_idx,
            )

    raise NoMatchError("No matched file found")


def _find_file_idx_movie(torrent: ResolvedTorrent) -> Stream:
    largest_file = max(torrent.files, key=lambda x: x.size)
    parsed_name = parse(torrent.title)
    return Stream(
        raw_name=largest_file.file_name,
        title=parsed_name.title or "",
        info_hash=torrent.info_hash,
        dubs_language=parsed_name.audio_languages,
        sources=parse_trackers(torrent.magnet),
        file_idx=largest_file.file_idx,
    )


def _valid_raw_torrent_series(raw_torrent: RawTorrent, query: SeriesQuery) -> bool:
    parsed_data = parse(raw_torrent.title)
    episode = query.episode
    season = query.season
    return (
        (not parsed_data.seasons and not parsed_data.episodes)
        or (season in parsed_data.seasons and not parsed_data.episodes)
        or (season in parsed_data.seasons and episode in parsed_data.episodes)
    )


def _valid_raw_torrent_movie(raw_torrent: RawTorrent, query: MovieQuery) -> bool:
    parsed_data = parse(raw_torrent.title)
    return not parsed_data.seasons and not parsed_data.episodes


def parse_trackers(magnet_uri: str) -> list[str]:
    parsed = urlparse(magnet_uri)
    parsed_query = parse_qs(parsed.query)
    return parsed_query.get("tr", [])


def find_file_idx(torrent: ResolvedTorrent, query: MediaQuery) -> Stream:
    if isinstance(query, SeriesQuery):
        return _find_file_idx_series(torrent, query)
    else:
        return _find_file_idx_movie(torrent)


def valid_raw_torrent(raw_torrent: RawTorrent, query: MediaQuery) -> bool:
    if isinstance(query, SeriesQuery):
        return _valid_raw_torrent_series(raw_torrent, query)
    if isinstance(query, MovieQuery):
        return _valid_raw_torrent_movie(raw_torrent, query)
    return False
