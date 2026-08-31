from pydantic import BaseModel, Field


class TMDBFindResult(BaseModel):
    id: int


class TMDBFindResponse(BaseModel):
    tv_results: list[TMDBFindResult] = Field(default_factory=list)
    movie_results: list[TMDBFindResult] = Field(default_factory=list)


class TMDBTranslationData(BaseModel):
    name: str | None = None
    title: str | None = None


class TMDBTranslationItem(BaseModel):
    iso_639_1: str
    data: TMDBTranslationData


class TMDBTranslationsBlock(BaseModel):
    translations: list[TMDBTranslationItem] = Field(default_factory=list)


class TMDBDetailResponse(BaseModel):
    id: int
    name: str | None = None
    title: str | None = None
    original_name: str | None = None
    original_title: str | None = None
    original_language: str
    translations: TMDBTranslationsBlock = Field(default_factory=TMDBTranslationsBlock)
