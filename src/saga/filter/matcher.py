from RTN import parse

from saga.models.query import MediaQuery, SeriesQuery
from saga.models.torrent import MediaFile, ResolvedTorrent, TorrentFileEntry


class NoMatchError(Exception):
    pass


def _filter_files(files: list[TorrentFileEntry], season: int) -> list[TorrentFileEntry]:
    result: list[TorrentFileEntry] = []
    for i, file in enumerate(files):
        parsed_file_name_data = parse(file.file_name)
        if not parsed_file_name_data.seasons:
            result.append(file)
            continue
        if (
            len(parsed_file_name_data.seasons) == 1
            and season in parsed_file_name_data.seasons
        ):
            result.append(file)

    return result


def _find_file_idx_series(torrent: ResolvedTorrent, query: SeriesQuery) -> MediaFile:
    files = _filter_files(torrent.files, query.season)
    for file in files:
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


def find_file_idx(torrent: ResolvedTorrent, query: MediaQuery) -> MediaFile:
    if isinstance(query, SeriesQuery):
        return _find_file_idx_series(torrent, query)
    else:
        return _find_file_idx_movie(torrent)
