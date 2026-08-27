from pydantic import BaseModel


class RawTorrent(BaseModel):
    title: str
    info_hash: str
    magnet: str
    torrent_link: str | None = None