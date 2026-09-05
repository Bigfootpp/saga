from enum import StrEnum
from typing import TypedDict

from pydantic import BaseModel


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
