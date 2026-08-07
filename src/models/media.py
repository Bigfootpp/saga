class Media:
    def __init__(self, id: str, titles: list[str], languages: list[str], type: str):
        self.id: str = id
        self.titles: list[str] = titles
        self.languages: list[str] = languages
        self.type: str = type
