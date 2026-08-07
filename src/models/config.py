from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Config(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    jackettApiKey: str | None = Field(None, alias="jackettApiKey")
    jackettHost: str | None = Field(None, alias="jackettHost")
    jackett: bool | None = Field(None, alias="jackett")
    metadataProvider: str = Field("cinemeta", alias="metadataProvider")
    tmdbApi: str | None = Field(None, alias="tmdbApi")
    languages: list[str] = Field(default_factory=list, alias="languages")
    getAllLanguages: bool | None = Field(None, alias="getAllLanguages")
    cache: bool | None = Field(None, alias="cache")
    debrid: bool | None = Field(None, alias="debrid")
    service: str | None = Field(None, alias="service")
    debridKey: str | None = Field(None, alias="debridKey")
    addonHost: str | None = Field(None, alias="addonHost")
    torrenting: bool | None = Field(None, alias="torrenting")
    maxResults: int = Field(20, alias="maxResults")
    sort: str | None = Field(None, alias="sort")
    exclusionKeywords: list[str] = Field(
        default_factory=list, alias="exclusionKeywords"
    )
    exclusion: list[str] = Field(default_factory=list, alias="exclusion")
    resultsPerQuality: int | None = Field(None, alias="resultsPerQuality")
    maxSize: int = Field(0, alias="maxSize")

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class StreamQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    magnet: str = Field(..., alias="magnet")
    type: str | None = Field(None, alias="type")
    file_index: int | None = Field(None, alias="fileIdx")
    season: str | None = Field(None, alias="season")
    episode: str | None = Field(None, alias="episode")
    torrent_download: str | None = Field(None, alias="torrentDownload")
