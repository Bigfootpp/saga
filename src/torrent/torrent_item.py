from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator
from RTN import ParsedData

from models.series import Series

if TYPE_CHECKING:
    from models.media import Media


class TorrentItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    raw_title: str = Field(..., alias="rawTitle")
    size: int = Field(..., alias="size")
    magnet: str = Field(..., alias="magnet")
    info_hash: str = Field(..., alias="infoHash")
    link: str = Field(..., alias="link")
    seeders: str = Field(..., alias="seeders")
    languages: list[str] = Field(default_factory=list, alias="languages")
    indexer: str = Field(..., alias="indexer")
    privacy: str = Field(..., alias="privacy")
    type: str | None = Field(default=None, alias="type")
    file_name: str | None = Field(default=None, alias="fileName")
    files: list[dict[str, Any]] | None = Field(default=None, alias="files")
    torrent_download: str | None = Field(default=None, alias="torrentDownload")
    trackers: list[str] = Field(default_factory=list, alias="trackers")
    file_index: int | None = Field(default=None, alias="fileIdx")
    availability: bool = Field(default=False, alias="availability")
    parsed_data: ParsedData | None = Field(default=None, alias="parsedData")

    @field_validator("info_hash", mode="before")
    @classmethod
    def _normalize_info_hash(cls, v: str) -> str:
        return v.lower() if v else v

    def to_debrid_stream_query(self, media: Media) -> dict[str, Any]:
        return {
            "magnet": self.magnet,
            "type": self.type,
            "file_index": self.file_index,
            "season": media.season if isinstance(media, Series) else None,
            "episode": media.episode if isinstance(media, Series) else None,
            "torrent_download": quote(self.torrent_download)
            if self.torrent_download is not None
            else None,
        }
