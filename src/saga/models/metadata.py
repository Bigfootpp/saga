from enum import StrEnum

from pydantic import BaseModel
from typing_extensions import TypedDict


class MediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


class Titles(TypedDict, extra_items=str):
    original: str
    en: str


class Metadata(BaseModel):
    original_language: str
    titles: Titles
    keywords: list[str]


class MetadataQuery(BaseModel):
    type: MediaType


class MetadataIdQuery(MetadataQuery):
    type: MediaType
    id: str
