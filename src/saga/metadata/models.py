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


class TMDBKeywordsItem(BaseModel):
    name: str
    id: int


class TMDBKeywordsBlock(BaseModel):
    results: list[TMDBKeywordsItem] = Field(default_factory=list)


class TMDBDetailResponse(BaseModel):
    id: int
    name: str | None = None
    title: str | None = None
    original_name: str | None = None
    original_title: str | None = None
    original_language: str
    translations: TMDBTranslationsBlock = Field(default_factory=TMDBTranslationsBlock)
    keywords: TMDBKeywordsBlock = Field(default_factory=TMDBKeywordsBlock)


class KitsuTitles(BaseModel):
    en: str | None = None
    en_jp: str | None = None
    ja_jp: str | None = None


class KitsuAnimeAttributes(BaseModel):
    canonicalTitle: str | None = None
    abbreviatedTitles: list[str] = Field(default_factory=list)
    titles: KitsuTitles = Field(default_factory=KitsuTitles)


class KitsuAnimeData(BaseModel):
    id: str
    attributes: KitsuAnimeAttributes


class KitsuCategoryAttributes(BaseModel):
    title: str | None = None


class KitsuIncludedItem(BaseModel):
    type: str
    attributes: KitsuCategoryAttributes = Field(
        default_factory=KitsuCategoryAttributes
    )


class KitsuAnimeResponse(BaseModel):
    data: KitsuAnimeData
    included: list[KitsuIncludedItem] = Field(default_factory=list)
