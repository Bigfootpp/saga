from saga.models.query import MediaQuery, MovieQuery, SeriesQuery
from saga.models.torrent import MediaFile, RawTorrent, ResolvedTorrent, TorrentFileEntry
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


def _find_file_idx_series(torrent: ResolvedTorrent, query: SeriesQuery) -> MediaFile:
    for file in torrent.files:
        if not _valid_file(file, query.season):
            continue
        parsed_file_name = parse(file.file_name)
        if (
            parsed_file_name.episodes
            and len(parsed_file_name.episodes) == 1
            and query.episode in parsed_file_name.episodes
        ):
            return MediaFile(
                file_name=file.file_name,
                info_hash=torrent.info_hash,
                magnet=torrent.magnet,
                file_idx=file.file_idx,
            )

    raise NoMatchError("No matched file found")


def _find_file_idx_movie(torrent: ResolvedTorrent) -> MediaFile:
    largest_file = max(torrent.files, key=lambda x: x.size)
    return MediaFile(
        file_name=largest_file.file_name,
        info_hash=torrent.info_hash,
        magnet=torrent.magnet,
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


def find_file_idx(torrent: ResolvedTorrent, query: MediaQuery) -> MediaFile:
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
