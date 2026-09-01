from pydantic import BaseModel


class RawTorrent(BaseModel):
    title: str
    info_hash: str
    magnet: str
    torrent_link: str | None = None


class TorrentFileEntry(BaseModel):
    file_idx: int
    file_name: str
    path: str


class ResolvedTorrent(BaseModel):
    title: str
    info_hash: str
    magnet: str
    files: list[TorrentFileEntry]


class EpisodeFile(BaseModel):
    file_name: str
    info_hash: str
    magnet: str
    file_idx: int
