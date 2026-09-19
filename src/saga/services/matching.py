from pathlib import Path
from typing import overload
from urllib.parse import parse_qs, urlparse

from saga.models.torrent import RawTorrent, ResolvedTorrent, TorrentFileEntry
from saga.utils.guessit import parse

VIDEO_EXTENSIONS: list[str] = [
    ".mkv",
    ".mp4",
    ".m4v",
    ".webm",
    ".avi",
    ".ts",
    ".m2ts",
    ".mts",
    ".mov",
    ".wmv",
    ".vob",
    ".flv",
    ".divx",
    ".mpg",
    ".mpeg",
    ".rm",
    ".rmvb",
    ".asf",
    ".ogv",
]


def _valid_extension(file: TorrentFileEntry) -> bool:
    ext = Path(file.file_name).suffix.lower()
    return ext in VIDEO_EXTENSIONS


def _valid_file(file: TorrentFileEntry, season: int) -> bool:
    if not _valid_extension(file):
        return False
    parsed_file_name_data = parse(file.file_name)
    if not parsed_file_name_data.seasons:
        return True
    return (
        len(parsed_file_name_data.seasons) == 1
        and season in parsed_file_name_data.seasons
    )


def _find_file_idx_series(
    torrent: ResolvedTorrent, season: int, episode: int
) -> int | None:
    # parsed_torrent_name = parse(torrent.title)
    for file in torrent.files:
        if not _valid_file(file, season):
            continue
        parsed_file_name = parse(file.file_name)
        if (
            parsed_file_name.episodes
            and len(parsed_file_name.episodes) == 1
            and episode in parsed_file_name.episodes
        ):
            return file.file_idx
            # return Stream(
            #     torrent_name=torrent.title,
            #     raw_name=file.file_name,
            #     info_hash=torrent.info_hash,
            #     dubs_language=parsed_torrent_name.audio_languages,
            #     sources=parse_trackers(torrent.magnet),
            #     file_idx=file.file_idx,
            # )

    return None


def _find_file_idx_movie(torrent: ResolvedTorrent) -> int:
    largest_file = max(torrent.files, key=lambda x: x.size)
    if not _valid_extension(largest_file):
        return largest_file.file_idx
    # parsed_name = parse(torrent.title)
    return largest_file.file_idx
    # return Stream(
    #     torrent_name=torrent.title,
    #     raw_name=largest_file.file_name,
    #     info_hash=torrent.info_hash,
    #     dubs_language=parsed_name.audio_languages,
    #     sources=parse_trackers(torrent.magnet),
    #     file_idx=largest_file.file_idx,
    # )


def check_torrent_coverage(raw_torrent: RawTorrent, season: int, episode: int) -> bool:
    parsed_data = parse(raw_torrent.title)
    return (
        (not parsed_data.seasons and not parsed_data.episodes)
        or (season in parsed_data.seasons and not parsed_data.episodes)
        or (season in parsed_data.seasons and episode in parsed_data.episodes)
    )


def _valid_raw_torrent_movie(raw_torrent: RawTorrent) -> bool:
    parsed_data = parse(raw_torrent.title)
    return not parsed_data.seasons and not parsed_data.episodes


def parse_trackers(magnet_uri: str) -> list[str]:
    parsed = urlparse(magnet_uri)
    parsed_query = parse_qs(parsed.query)
    return parsed_query.get("tr", [])


@overload
def find_file_idx(torrent: ResolvedTorrent) -> int | None: ...
@overload
def find_file_idx(
    torrent: ResolvedTorrent, season: int, episode: int
) -> int | None: ...


def find_file_idx(
    torrent: ResolvedTorrent, season: int | None = None, episode: int | None = None
) -> int | None:
    if season and episode:
        return _find_file_idx_series(torrent, episode=episode, season=season)
    else:
        return _find_file_idx_movie(torrent)


@overload
def valid_raw_torrent(raw_torrent: RawTorrent) -> bool: ...
@overload
def valid_raw_torrent(raw_torrent: RawTorrent, season: int, episode: int) -> bool: ...


def valid_raw_torrent(
    raw_torrent: RawTorrent, season: int | None = None, episode: int | None = None
) -> bool:
    if season and episode:
        return check_torrent_coverage(raw_torrent, season=season, episode=episode)
    else:
        return _valid_raw_torrent_movie(raw_torrent)


def get_dub_language(raw_torrent: RawTorrent) -> list[str]:
    parsed_name = parse(raw_torrent.title)
    return parsed_name.audio_languages


def extract_audio_languages(
    raw_torrent: RawTorrent, original_language: str | None = None
) -> list[str]:
    parsed_name = parse(raw_torrent.title)

    audio_langs = set(parsed_name.audio_languages)
    sub_langs = set(parsed_name.subtitle_languages)

    detected_audio = {lang for lang in audio_langs if lang not in {"mul"}}

    non_conflicting_dubs = set(detected_audio)
    if original_language:
        non_conflicting_dubs.add(original_language)

    is_multi = "mul" in audio_langs

    if is_multi:
        inferred_languages: set[str] = set(detected_audio)

        foreign_dubs = detected_audio - (
            {original_language} if original_language else set()
        )

        if len(foreign_dubs) == 0:
            usable_subs = {sub for sub in sub_langs if sub not in {"mul"}}
            inferred_languages.update(usable_subs)

        if not inferred_languages:
            return ["mul"]

        return sorted(inferred_languages)

    if detected_audio:
        return sorted(detected_audio)

    return []


def contain_dubs(
    raw_torrent: RawTorrent, dubs_list: list[str], original_language: str | None = None
) -> bool:
    if not dubs_list:
        return True

    resolved_languages = set(extract_audio_languages(raw_torrent, original_language))
    requested_languages = set(dubs_list)

    return not requested_languages.isdisjoint(resolved_languages)
