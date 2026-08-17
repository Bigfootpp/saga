from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from RTN import ParsedData

from saga.torrent.torrent_item import TorrentItem


class JackettResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    raw_title: str | None = Field(None, alias="rawTitle")
    size: str | None = Field(None, alias="size")
    link: str | None = Field(None, alias="link")
    indexer: str | None = Field(None, alias="indexer")
    seeders: str | None = Field(None, alias="seeders")
    magnet: str | None = Field(None, alias="magnet")
    info_hash: str | None = Field(None, alias="infoHash")
    privacy: str | None = Field(None, alias="privacy")
    languages: list[str] = Field(default_factory=list, alias="languages")
    type: str | None = Field(default=None, alias="type")
    parsed_data: ParsedData | None = Field(default=None, alias="parsedData")

    def convert_to_torrent_item(self) -> TorrentItem:
        return TorrentItem(
            rawTitle=self.raw_title or "",
            size=int(self.size) if self.size else 0,
            magnet=self.magnet or "",
            infoHash=self.info_hash or "",
            link=self.link or "",
            seeders=self.seeders or "0",
            languages=self.languages,
            indexer=self.indexer or "",
            privacy=self.privacy or "public",
            type=self.type,
            parsedData=self.parsed_data,
        )
