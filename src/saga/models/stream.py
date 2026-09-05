from pydantic import BaseModel, Field


class Stream(BaseModel):
    raw_name: str
    title: str
    dubs_language: list[str]
    info_hash: str
    file_idx: int
    sources: list[str]


class StreamResult(BaseModel):
    dubs_stream: list[Stream]
    others: list[Stream]


class StremioStream(BaseModel):
    name: str
    description: str
    info_hash: str = Field(..., alias="infoHash")
    file_idx: int = Field(..., alias="fileIdx")
    sources: list[str]
