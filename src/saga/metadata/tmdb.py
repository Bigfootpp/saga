import requests

from saga.metadata.base import MetadataProvider
from saga.models.movie import Movie
from saga.models.series import Series

TMDB_TIMEOUT = 15.0


class TMDB(MetadataProvider):
    def get_metadata(self, id: str, type: str) -> Movie | Series | None:
        self.logger.info(f"Getting metadata for {type} with id {id}")

        full_id = id.split(":")

        languages = [
            lang for lang in dict.fromkeys(self.config.languages or ["en"]) if lang
        ]

        if not languages:
            return None

        first_lang = languages[0]
        url = f"https://api.themoviedb.org/3/find/{full_id[0]}?api_key={self.config.tmdb_api}&external_source=imdb_id&language={first_lang}"
        data = requests.get(url, timeout=TMDB_TIMEOUT).json()

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
            url = f"https://api.themoviedb.org/3/find/{full_id[0]}?api_key={self.config.tmdb_api}&external_source=imdb_id&language={lang}"
            data = requests.get(url, timeout=TMDB_TIMEOUT).json()

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
