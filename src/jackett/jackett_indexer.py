class JackettIndexer:
    def __init__(self):
        self.title: str | None = None
        self.id: str | None = None
        self.link: str | None = None
        self.type: str | None = None
        self.language: str | None = None
        self.tv_search_capatabilities: list[str] | None = None
        self.movie_search_capatabilities: list[str] | None = None
