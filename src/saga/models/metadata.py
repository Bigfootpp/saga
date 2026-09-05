from enum import StrEnum

from pydantic import BaseModel
from typing_extensions import TypedDict


class MediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


class Titles(TypedDict, extra_items=str):
    original: str


class Metadata(BaseModel):
    titles: Titles


class MetadataQuery(BaseModel):
    type: MediaType
    id: str
