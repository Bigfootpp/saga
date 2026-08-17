from __future__ import annotations

from typing import Literal, TypedDict


class TorrentFile(TypedDict):
    path: list[str]
    length: int


class TorrentInfoDict(TypedDict):
    name: str
    pieces: str
    piece_length: int
    files: list[TorrentFile]
    private: int | None


class TorrentMetadata(TypedDict):
    info: TorrentInfoDict
    announce: str | list[str] | None
    announce_list: list[list[str]] | None


class FileEntryDict(TypedDict):
    file_index: int
    title: str
    size: int | str


class StreamEntry(TypedDict):
    name: str
    description: str
    url: str | None
    infoHash: str | None
    fileIdx: int | None
    behaviorHints: dict[str, str]


MediaType = Literal["movie", "series"]