from typing import Any

from RTN import parse

video_formats = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".flv",
    ".wmv",
    ".webm",
    ".mpg",
    ".mpeg",
    ".m4v",
    ".3gp",
    ".3g2",
    ".ogv",
    ".ogg",
    ".drc",
    ".gif",
    ".gifv",
    ".mng",
    ".qt",
    ".yuv",
    ".rm",
    ".rmvb",
    ".asf",
    ".amv",
    ".m4p",
    ".mp2",
    ".mpe",
    ".mpv",
    ".m2v",
    ".svi",
    ".mxf",
    ".roq",
    ".nsv",
    ".f4v",
    ".f4p",
    ".f4a",
    ".f4b",
}


def is_video_file(filename: Any) -> bool:
    extension_idx = filename.rfind(".")
    if extension_idx == -1:
        return False

    return filename[extension_idx:] in video_formats


def _parse_season_episode(season: str | int, episode: str | int) -> tuple[int, int]:
    season_int = int(str(season).replace("S", "").replace("s", ""))
    episode_int = int(str(episode).replace("E", "").replace("e", ""))
    return season_int, episode_int


def season_episode_in_filename(
    filename: str, season: str | int, episode: str | int
) -> bool:
    if not is_video_file(filename):
        return False
    parsed_name = parse(filename)
    season_int, episode_int = _parse_season_episode(season, episode)
    return season_int in parsed_name.seasons and episode_int in parsed_name.episodes
