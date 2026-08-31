from enum import StrEnum

from pydantic import BaseModel


class MediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


class Metadata(BaseModel):
    titles: dict[str, str]


class MetadataQuery(BaseModel):
    type: MediaType
    id: str
