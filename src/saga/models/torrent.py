from pydantic import BaseModel


class RawTorrent(BaseModel):
    title: str
    info_hash: str
    magnet: str
    torrent_link: str | None = None
    seeders: int
    peers: int
    distributed_copies: float | None = None


class TorrentFileEntry(BaseModel):
    file_idx: int
    file_name: str
    path: str
    size: int


class ResolvedTorrent(RawTorrent):
    files: list[TorrentFileEntry]
