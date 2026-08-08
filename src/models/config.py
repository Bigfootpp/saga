from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Config(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    jackett_api_key: str | None = Field(None, alias="jackettApiKey")
    jackett_host: str | None = Field(None, alias="jackettHost")
    jackett: bool | None = Field(None, alias="jackett")
    metadata_provider: str = Field("cinemeta", alias="metadataProvider")
    tmdb_api: str | None = Field(None, alias="tmdbApi")
    languages: list[str] = Field(default_factory=list, alias="languages")
    get_all_languages: bool | None = Field(None, alias="getAllLanguages")
    cache: bool | None = Field(None, alias="cache")
    debrid: bool | None = Field(None, alias="debrid")
    service: str | None = Field(None, alias="service")
    debrid_key: str | None = Field(None, alias="debridKey")
    addon_host: str | None = Field(None, alias="addonHost")
    torrenting: bool | None = Field(None, alias="torrenting")
    max_results: int = Field(20, alias="maxResults")
    sort: str | None = Field(None, alias="sort")
    exclusion_keywords: list[str] = Field(
        default_factory=list, alias="exclusionKeywords"
    )
    exclusion: list[str] = Field(default_factory=list, alias="exclusion")
    results_per_quality: int | None = Field(None, alias="resultsPerQuality")
    max_size: int = Field(0, alias="maxSize")

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
