from collections.abc import Mapping

import httpx

from saga.metadata.base import BaseMetadataProvider
from saga.metadata.exceptions import (
    MetadataError,
    MetadataStatusError,
    MetadataTimeoutError,
)
from saga.metadata.models import (
    KitsuAnimeAttributes,
    KitsuAnimeListResponse,
    KitsuAnimeResponse,
    KitsuIncludedItem,
)
from saga.models.metadata import (
    Metadata,
    MetadataIdQuery,
    MetadataQuery,
    MetadataTitleQuery,
    Titles,
)


class KitsuMetadataProvider(BaseMetadataProvider):
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        base_url: str = "https://kitsu.io/api/edge",
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.AsyncClient()
        self.timeout = timeout
        self.headers = {"Accept": "application/vnd.api+json"}

    async def get_metadata(self, query: MetadataQuery) -> Metadata:
        if isinstance(query, MetadataIdQuery):
            kitsu_id = query.id
            if not kitsu_id.isdigit():
                raise MetadataError(f"Invalid Kitsu ID: '{kitsu_id}'")

            url = f"{self.base_url}/anime/{kitsu_id}"
            params = {"include": "categories"}
            parsed = await self._fetch_single(url, params)
            return self._to_metadata(parsed.data.attributes, parsed.included)

        if isinstance(query, MetadataTitleQuery):
            title = query.title.strip()
            if not title:
                raise MetadataError("Title must not be empty")
            url = f"{self.base_url}/anime"
            params = {
                "filter[text]": title,
                "page[limit]": 1,
                "include": "categories",
            }
            parsed = await self._fetch_first(url, params, title)
            return self._to_metadata(parsed[0], parsed[1])

        raise MetadataError("Unsupported query type for Kitsu provider")

    async def _fetch_single(
        self, url: str, params: Mapping[str, str | int]
    ) -> KitsuAnimeResponse:
        try:
            response = await self.client.get(
                url, params=params, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
            return KitsuAnimeResponse.model_validate(response.json())
        except httpx.TimeoutException as e:
            raise MetadataTimeoutError("Kitsu took too long to respond") from e
        except httpx.HTTPStatusError as e:
            raise MetadataStatusError(
                f"Kitsu error: {e.response.status_code} with {e.request.url}"
            ) from e

    async def _fetch_first(
        self, url: str, params: Mapping[str, str | int], title: str
    ) -> tuple[KitsuAnimeAttributes, list[KitsuIncludedItem]]:
        try:
            response = await self.client.get(
                url, params=params, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
            parsed = KitsuAnimeListResponse.model_validate(response.json())
        except httpx.TimeoutException as e:
            raise MetadataTimeoutError("Kitsu took too long to respond") from e
        except httpx.HTTPStatusError as e:
            raise MetadataStatusError(
                f"Kitsu error: {e.response.status_code} with {e.request.url}"
            ) from e

        if not parsed.data:
            raise MetadataError(f"No Kitsu result for title: '{title}'")
        return parsed.data[0].attributes, parsed.included

    @staticmethod
    def _to_metadata(
        attr: KitsuAnimeAttributes, included: list[KitsuIncludedItem]
    ) -> Metadata:
        titles: Titles = {"original": "", "en": ""}

        en_title = attr.titles.en
        en_jp_title = attr.titles.en_jp
        ja_title = attr.titles.ja_jp
        if en_title and en_title.strip():
            titles["en"] = en_title
        if en_jp_title and en_jp_title.strip():
            titles["en_jp"] = en_jp_title
        if ja_title and ja_title.strip():
            titles["ja"] = ja_title
            titles["original"] = ja_title
        elif en_title:
            titles["original"] = en_title

        keywords = [
            item.attributes.title
            for item in included
            if item.type == "categories"
            and item.attributes.title
            and item.attributes.title.strip()
        ]

        return Metadata(
            titles=titles,
            original_language="ja",
            keywords=keywords,
        )
