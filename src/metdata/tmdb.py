import requests

from jackett.jackett_indexer import JackettIndexer
from metdata.metadata_provider_base import MetadataProvider
from models.movie import Movie
from models.series import Series


class TMDB(MetadataProvider):
    def __init__(self, config):
        super().__init__(config)
        self._indexers: list[JackettIndexer] | None = None

    @property
    def indexers(self):
        return self._indexers

    @indexers.setter
    def indexers(self, indexers_):
        self._indexers = indexers_

    def get_metadata(self, id: str, type: str):
        self.logger.info(f"Getting metadata for {type} with id {id}")

        full_id = id.split(":")
        result = None

        if (
            self.config.get("getAllLanguages", None)
            and self._indexers
            and len(self._indexers) > 0
        ):
            languages = [
                lang
                for lang in {indexer.language for indexer in self._indexers}
                if lang
            ]
        else:
            languages = [
                lang
                for lang in dict.fromkeys(self.config.get("languages", ["en"]))
                if lang
            ]

        if not languages:
            return None

        first_lang = languages[0]
        url = f"https://api.themoviedb.org/3/find/{full_id[0]}?api_key={self.config.get('tmdbApi')}&external_source=imdb_id&language={first_lang}"
        data = requests.get(url).json()

        if type == "movie":
            result = Movie(
                id=id,
                titles=[
                    self.replace_weird_characters(data["movie_results"][0]["title"])
                ],
                year=data["movie_results"][0]["release_date"][:4],
                languages=languages,
                type="movie",
            )
        else:
            result = Series(
                id=id,
                titles=[self.replace_weird_characters(data["tv_results"][0]["name"])],
                season=f"S{int(full_id[1]):02d}",
                episode=f"E{int(full_id[2]):02d}",
                languages=list(languages),
                type="series",
                seasonfile=False,
            )

        for lang in languages[1:]:
            url = f"https://api.themoviedb.org/3/find/{full_id[0]}?api_key={self.config.get('tmdbApi')}&external_source=imdb_id&language={lang}"
            data = requests.get(url).json()

            if type == "movie":
                result.titles.append(
                    self.replace_weird_characters(data["movie_results"][0]["title"])
                )
            else:
                result.titles.append(
                    self.replace_weird_characters(data["tv_results"][0]["name"])
                )

        self.logger.info(f"Got metadata for {type} with id {id}")
        return result
