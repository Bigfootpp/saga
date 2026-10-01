from pydantic import BaseModel


class ScrapeItem(BaseModel):
    info_hash: str
    seeders: int
    completed: int
    leechers: int
