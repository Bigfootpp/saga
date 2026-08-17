from pydantic import BaseModel, ConfigDict, Field


class Config(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    jackett_api_key: str | None = Field(None, alias="jackettApiKey")
    jackett_host: str | None = Field(None, alias="jackettHost")
    metadata_provider: str = Field("cinemeta", alias="metadataProvider")
    tmdb_api: str | None = Field(None, alias="tmdbApi")
    languages: list[str] = Field(default_factory=list, alias="languages")
    get_all_languages: bool | None = Field(None, alias="getAllLanguages")
    addon_host: str | None = Field(None, alias="addonHost")
