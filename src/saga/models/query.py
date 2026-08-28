from pydantic import BaseModel


class MovieQuery(BaseModel):
    title: str
    year: int | None

class SeriesQuery(BaseModel):
    title: str
    season: int
    episode: int

MediaQuery = MovieQuery | SeriesQuery