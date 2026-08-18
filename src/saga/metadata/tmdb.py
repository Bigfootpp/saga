from typing import Literal

from saga.metadata.base import MetadataProvider
from saga.models.media import Media
from saga.models.movie import Movie
from saga.models.series import Series

TMDB_TIMEOUT = 15.0

class TMDB(MetadataProvider):
    async def imdbid_to_tmdbid(self, imdb_id: str) -> int:
        url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={self.config.tmdb_api}&external_source=imdb_id"
        data: dict[str, list[dict]] = (await self.client.get(url, timeout=TMDB_TIMEOUT)).json()
        results = data.get("tv_results") or data.get("movie_results")
        if results:
            tmdbid = results[0].get("id")
            if tmdbid:
                return tmdbid
        raise ValueError(f"Could not find TMDB ID for IMDb ID: {imdb_id}")

    async def get_all_titles(self, imdb_id: str, type: Literal["tv", "movie"]) -> dict[str, str]:
        tmdb_id = await self.imdbid_to_tmdbid(imdb_id)
        url = f"https://api.themoviedb.org/3/{type}/{tmdb_id}/translations?api_key={self.config.tmdb_api}"
        data: dict[str, list[dict]] = (await self.client.get(url, timeout=TMDB_TIMEOUT)).json()
        result = {}
        if data and data.get("translations"):
            translations = data["translations"]
            for el in translations:
                lang = el["iso_639_1"]
                if type == "tv":
                    title = el["data"]["name"]
                else:
                    title = el["data"]["title"]
                if not lang or not title:
                    continue
                result[lang] = title
        return result

    async def get_release_year(self, imdb_id: str) -> str:
        url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={self.config.tmdb_api}&external_source=imdb_id"
        data: dict[str, list[dict]] = (await self.client.get(url, timeout=TMDB_TIMEOUT)).json()
        results = data.get("tv_results") or data.get("movie_results")
        if results:
            year = results[0].get("release_date") or results[0].get("first_air_date")
            if year and isinstance(year, str):
                return year[:4]
        raise ValueError(f"Could not find TMDB ID for IMDb ID: {imdb_id}")


    async def get_metadata(self, id: str, type: str) -> Media | None:
        if self.config.tmdb_api is None:
            return None

        self.logger.info(f"Getting metadata for {type} with id {id}")

        languages = list(set(self.config.languages + ["en"]))
        full_id = id.split(":")
        imdb_id = full_id[0]

        if type == "movie":
            titles = await self.get_all_titles(imdb_id, "movie")
            selected_titles = list({title for lang, title in titles.items() if lang in languages})
            result = Movie(
                id=id,
                titles=selected_titles,
                year=await self.get_release_year(imdb_id),
                type="movie",
            )
        else:
            season = int(full_id[1])
            episode = int(full_id[2])
            titles = await self.get_all_titles(imdb_id, "tv")
            selected_titles = list({title for lang, title in titles.items() if lang in languages})
            result = Series(
                id=id,
                titles=selected_titles,
                season=f"S{season:02d}",
                episode=f"E{episode:02d}",
                type="series",
                seasonfile=False,
            )

        self.logger.info(f"Got metadata for {type} with id {id}")
        return result
