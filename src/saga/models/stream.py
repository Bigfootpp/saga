from pydantic import BaseModel, Field


class StreamEntry(BaseModel):
    name: str
    description: str
    info_hash: str = Field(..., alias="infoHash")
    file_idx: int = Field(..., alias="fileIdx")
    sources: list[str]
