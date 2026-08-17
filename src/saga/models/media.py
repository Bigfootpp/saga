from pydantic import BaseModel, ConfigDict, Field


class Media(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="id")
    titles: list[str] = Field(..., alias="titles")
    languages: list[str] = Field(..., alias="languages")
    type: str = Field(..., alias="type")


class Movie(Media):
    model_config = ConfigDict(populate_by_name=True)

    year: str = Field(..., alias="year")


class Series(Media):
    model_config = ConfigDict(populate_by_name=True)

    season: str = Field(..., alias="season")
    episode: str = Field(..., alias="episode")
    seasonfile: bool | None = Field(None, alias="seasonfile")
