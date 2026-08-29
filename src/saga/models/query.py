from enum import StrEnum

from pydantic import BaseModel


class MediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"

class MovieQuery(BaseModel):
    title: str
    year: int | None = None

class SeriesQuery(BaseModel):
    title: str
    season: int
    episode: int

class MetadataQuery(BaseModel):
    type: MediaType
    id: str

MediaQuery = MovieQuery | SeriesQuery