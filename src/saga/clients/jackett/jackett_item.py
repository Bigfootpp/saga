from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class JackettItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    raw_title: str
    size: int
    info_hash: str
    link: str | None = None
    magnet: str | None = None
    privacy: str | None = None
    type: str | None = None
    indexer: str | None