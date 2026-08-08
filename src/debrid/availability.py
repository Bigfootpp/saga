from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict, cast


class FileEntryDict(TypedDict):
    file_index: int
    title: str
    size: int | str


@dataclass(frozen=True)
class FileEntry:
    """A single candidate file inside a cached torrent."""

    file_index: int
    title: str
    size: int | str


@dataclass
class AvailabilityResult:
    """Normalized availability data produced by a debrid provider."""

    files: dict[str, list[FileEntry]] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)


DebridFolderItem = dict[str, object]


def explore_nested_files(
    folder: list[DebridFolderItem] | None,
    type_: str,
    season: str | None = None,
    episode: str | None = None,
) -> list[FileEntry]:
    """Flatten a debrid provider folder structure into FileEntries.

    Matches the original _explore_folders behavior:
    - Handles both "n"/"s"/"e" (AllDebrid) and "name"/"size"/"e"|"files" (TorBox) keys
    - For series: matches season/episode, file_index increments globally
    - For movie: file_index resets to 1, then increments globally
    """
    from torrent.matching import season_episode_in_filename

    matches: list[FileEntry] = []
    if folder is None:
        return matches

    def traverse(
        folder_: list[DebridFolderItem], file_index: int, type_local: str
    ) -> int:
        if type_local == "movie":
            file_index = 1
        for file in folder_:
            if "e" in file or "files" in file:
                sub_folder = file.get("e") or file.get("files")
                if isinstance(sub_folder, list):
                    file_index = traverse(sub_folder, file_index, type_local)
                continue

            file_name = cast(str, file.get("n") or file.get("name") or "")
            file_size = cast(int | str, file.get("s") or file.get("size", 0))
            if not file_name:
                continue

            if type_local == "series":
                if season is None or episode is None:
                    return file_index
                if season_episode_in_filename(file_name, season, episode):
                    matches.append(
                        FileEntry(
                            file_index=file_index,
                            title=file_name,
                            size=file_size,
                        )
                    )
            else:
                matches.append(
                    FileEntry(
                        file_index=file_index,
                        title=file_name,
                        size=file_size,
                    )
                )
            file_index += 1
        return file_index

    matches: list[FileEntry] = []
    traverse(folder, 1, type_)
    return matches
