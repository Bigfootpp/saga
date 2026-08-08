from pydantic import BaseModel, ConfigDict, Field


class JackettIndexer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(default=None, alias="title")
    id: str | None = Field(default=None, alias="id")
    link: str | None = Field(default=None, alias="link")
    type: str | None = Field(default=None, alias="type")
    language: str | None = Field(default=None, alias="language")
    tv_search_capabilities: list[str] | None = Field(
        default=None, alias="tvSearchCapabilities"
    )
    movie_search_capabilities: list[str] | None = Field(
        default=None, alias="movieSearchCapabilities"
    )
