from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from RTN import parse as rtn_parse

from torrent.torrent_item import TorrentItem
from utils.logger import setup_logger

logger = setup_logger(__name__)


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
    type: str | None = Field(None, alias="type")
    parsed_data: Any = Field(default=None, alias="parsedData")

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

    def from_cached_item(self, cached_item: dict, media) -> JackettResult:
        if not isinstance(cached_item, dict):
            logger.error(f"Expected dict, got {type(cached_item)}: {cached_item}")

        parsed_result = rtn_parse(cached_item.get("title", ""))

        self.raw_title = cached_item.get("title", "")
        self.indexer = "Cache"
        self.magnet = cached_item.get("magnet", "")
        self.link = cached_item.get("magnet", "")
        self.info_hash = cached_item.get("hash", "")
        language_str = cached_item.get("language")
        self.languages = language_str.split(";") if language_str else []
        self.seeders = str(cached_item.get("seeders", 0))
        self.size = str(cached_item.get("size", 0))
        self.type = media.type
        self.parsed_data = parsed_result

        return self
