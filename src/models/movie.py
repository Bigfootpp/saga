from models.media import Media


class Movie(Media):
    def __init__(self, id: str, titles: list[str], year: str, languages: list[str]):
        super().__init__(id, titles, languages, "movie")
        self.year = year
