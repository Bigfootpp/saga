from typing import Literal
from urllib.parse import urljoin

import httpx

from saga.metadata.base import BaseMetadataProvider
from saga.metadata.exceptions import (
    MetadataError,
    MetadataStatusError,
    MetadataTimeoutError,
)
from saga.metadata.models import TMDBDetailResponse, TMDBFindResponse
from saga.models.metadata import MediaType, Metadata, MetadataQuery, Titles


class IMDbIDNotFoundError(MetadataError):
    pass


class InvalidIMDbIDError(MetadataError, ValueError):
    pass


class TMDBMetadataProvider(BaseMetadataProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.themoviedb.org",
        timeout: float = 15.0,
    ):
        self.api_key = api_key
        self.base_url = (
            urljoin(base_url, "/3")
            if not base_url.endswith(("3", "3/"))
            else base_url.rstrip("/")
        )
        self.client = httpx.AsyncClient()
        self.timeout = timeout

    async def imdbid_to_tmdbid(self, imdb_id: str) -> int:
        if not imdb_id.startswith("tt"):
            raise InvalidIMDbIDError(
                f"Invalid IMDb ID format: '{imdb_id}'. It must start with 'tt'."
            )

        url = f"{self.base_url}/find/{imdb_id}"
        params = {"api_key": self.api_key, "external_source": "imdb_id"}

        try:
            response = await self.client.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            parsed_find = TMDBFindResponse.model_validate(response.json())

            if parsed_find.tv_results:
                return parsed_find.tv_results[0].id
            if parsed_find.movie_results:
                return parsed_find.movie_results[0].id

            raise IMDbIDNotFoundError(f"Could not find TMDB ID for IMDb ID: {imdb_id}")

        except httpx.TimeoutException as e:
            raise MetadataTimeoutError("TMDB took too long to respond") from e
        except httpx.HTTPStatusError as e:
            raise MetadataStatusError(
                f"TMDB error: {e.response.status_code} with {e.request.url}"
            ) from e

    async def _get_all_titles(self, tmdb_id: int, media_type: MediaType) -> Titles:
        tmdb_type: Literal["tv", "movie"] = "tv" if media_type == "series" else "movie"

        url = f"{self.base_url}/{tmdb_type}/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "translations",
        }

        try:
            response = await self.client.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            detail = TMDBDetailResponse.model_validate(response.json())

            titles: Titles = {"original": ""}

            main_title = detail.name or detail.title
            if main_title:
                titles["en"] = main_title

            original_title = detail.original_name or detail.original_title
            if original_title:
                titles[detail.original_language] = original_title
                titles["original"] = original_title

            for item in detail.translations.translations:
                lang = item.iso_639_1.strip()
                translated_title = item.data.name or item.data.title

                if lang and translated_title and translated_title.strip():
                    titles[lang] = translated_title

            return titles

        except httpx.TimeoutException as e:
            raise MetadataTimeoutError("TMDB took too long to respond") from e
        except httpx.HTTPStatusError as e:
            raise MetadataStatusError(f"TMDB error: {e.response.status_code}") from e

    async def get_metadata(self, query: MetadataQuery) -> Metadata:
        tmdb_id = await self.imdbid_to_tmdbid(query.id)
        titles_dict = await self._get_all_titles(tmdb_id=tmdb_id, media_type=query.type)
        return Metadata(titles=titles_dict)
