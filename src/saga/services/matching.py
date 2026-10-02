from pathlib import Path
from statistics import median
from typing import overload
from urllib.parse import parse_qs, urlparse

from saga.models.torrent import ResolvedTorrent, TorrentFileEntry
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


def best_candidate(
    candidates: list[TorrentFileEntry], size_median: float
) -> TorrentFileEntry:
    final_candidates: list[TorrentFileEntry] = [
        candidate
        for candidate in candidates
        if size_median * 0.3 <= candidate.size <= size_median * 2.5
    ]
    if final_candidates:
        return max(final_candidates, key=lambda x: x.size)

    return min(candidates, key=lambda c: abs(c.size - size_median))


def _find_file_idx_series(
    torrent: ResolvedTorrent, season: int, episode: int, abs_episode: int | None = None
) -> int | None:
    all_videos_file: list[TorrentFileEntry] = []
    candidates: list[TorrentFileEntry] = []
    abs_candidates: list[TorrentFileEntry] = []
    for file in torrent.files:
        if not _valid_file(file, season):
            continue
        all_videos_file.append(file)

        parsed_file_name = parse(file.file_name)
        if len(parsed_file_name.episodes) == 1 and episode in parsed_file_name.episodes:
            candidates.append(file)
        elif (
            len(parsed_file_name.episodes) == 1
            and abs_episode in parsed_file_name.episodes
        ):
            abs_candidates.append(file)
    if len(candidates) == 0 and len(abs_candidates) == 0:
        return None

    size_median = median([file.size for file in all_videos_file])

    if abs_candidates:
        if len(abs_candidates) == 1:
            return abs_candidates[0].file_idx
        return best_candidate(abs_candidates, size_median).file_idx
    if len(candidates) == 1:
        return candidates[0].file_idx
    return best_candidate(candidates, size_median).file_idx


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


def check_torrent_coverage(torrent_name: str, season: int, episode: int) -> bool:
    parsed_data = parse(torrent_name)
    return (
        (not parsed_data.seasons and not parsed_data.episodes)
        or (season in parsed_data.seasons and not parsed_data.episodes)
        or (season in parsed_data.seasons and episode in parsed_data.episodes)
    )


def _valid_raw_torrent_movie(torrent_name: str) -> bool:
    parsed_data = parse(torrent_name)
    return not parsed_data.seasons and not parsed_data.episodes


def parse_trackers(magnet_uri: str) -> list[str]:
    parsed = urlparse(magnet_uri)
    parsed_query = parse_qs(parsed.query)
    return parsed_query.get("tr", [])


@overload
def find_file_idx(torrent: ResolvedTorrent) -> int | None: ...
@overload
def find_file_idx(
    torrent: ResolvedTorrent, season: int, episode: int, abs_episode: int | None = None
) -> int | None: ...


def find_file_idx(
    torrent: ResolvedTorrent,
    season: int | None = None,
    episode: int | None = None,
    abs_episode: int | None = None,
) -> int | None:
    if season and episode:
        return _find_file_idx_series(torrent, season, episode, abs_episode)
    else:
        return _find_file_idx_movie(torrent)


@overload
def valid_raw_torrent(torrent_name: str) -> bool: ...
@overload
def valid_raw_torrent(torrent_name: str, season: int, episode: int) -> bool: ...


def valid_raw_torrent(
    torrent_name: str, season: int | None = None, episode: int | None = None
) -> bool:
    if season and episode:
        return check_torrent_coverage(torrent_name, season=season, episode=episode)
    else:
        return _valid_raw_torrent_movie(torrent_name)


def get_dub_language(torrent_name: str) -> list[str]:
    parsed_name = parse(torrent_name)
    return parsed_name.audio_languages


def extract_audio_languages(
    torrent_name: str, original_language: str | None = None
) -> list[str]:
    ignore_languages = {"mul", "dual"}
    parsed_name = parse(torrent_name)

    audio_langs = set(parsed_name.audio_languages)
    sub_langs = set(parsed_name.subtitle_languages)

    detected_audio = {lang for lang in audio_langs if lang not in ignore_languages}

    is_multi = "mul" in audio_langs
    is_dual = "dual" in audio_langs

    if is_multi:
        inferred_languages: set[str] = set(detected_audio)

        foreign_dubs = detected_audio - (
            {original_language} if original_language else set()
        )

        if len(foreign_dubs) == 0:
            usable_subs = {sub for sub in sub_langs if sub not in ignore_languages}
            inferred_languages.update(usable_subs)

        if not inferred_languages:
            return ["mul"]

        return sorted(inferred_languages)

    if is_dual:
        return sorted(detected_audio) if detected_audio else ["en"]

    if detected_audio:
        return sorted(detected_audio)

    return []


def contain_dubs(
    torrent_name: str, dubs_list: list[str], original_language: str | None = None
) -> bool:
    if not dubs_list:
        return True

    resolved_languages = set(extract_audio_languages(torrent_name, original_language))
    requested_languages = set(dubs_list)

    return not requested_languages.isdisjoint(resolved_languages)


def matches_titles(torrent_name: str, titles: list[str]) -> bool:
    titles_set = {title.strip().lower() for title in titles}
    parsed_name = parse(torrent_name)
    if parsed_name.title is None:
        return False
    normalized_title = parsed_name.title.strip().lower()
    for title in titles_set:
        if title in normalized_title:
            return True
    return False

    # return parsed_name.title.strip().lower() in titles_set
