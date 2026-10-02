from pydantic import BaseModel


class ScrapeItemResult(BaseModel):
    info_hash: str
    seeders: int
    completed: int
    leechers: int
