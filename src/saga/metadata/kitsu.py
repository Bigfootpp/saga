import httpx

from saga.metadata.base import BaseMetadataProvider
from saga.metadata.exceptions import (
    MetadataError,
    MetadataStatusError,
    MetadataTimeoutError,
)
from saga.metadata.models import KitsuAnimeResponse
from saga.models.metadata import Metadata, MetadataIdQuery, MetadataQuery, Titles


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
        if not isinstance(query, MetadataIdQuery):
            raise MetadataError("Metadata fetching only available by id")

        kitsu_id = query.id
        if not kitsu_id.isdigit():
            raise MetadataError(f"Invalid Kitsu ID: '{kitsu_id}'")

        url = f"{self.base_url}/anime/{kitsu_id}"
        params = {"include": "categories"}

        try:
            response = await self.client.get(
                url, params=params, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
            parsed = KitsuAnimeResponse.model_validate(response.json())
        except httpx.TimeoutException as e:
            raise MetadataTimeoutError("Kitsu took too long to respond") from e
        except httpx.HTTPStatusError as e:
            raise MetadataStatusError(
                f"Kitsu error: {e.response.status_code} with {e.request.url}"
            ) from e

        attr = parsed.data.attributes
        titles: Titles = {"original": "", "en": ""}

        en_title = attr.titles.en or attr.titles.en_jp or attr.canonicalTitle
        ja_title = attr.titles.ja_jp
        if en_title and en_title.strip():
            titles["en"] = en_title
        if ja_title and ja_title.strip():
            titles["ja"] = ja_title
            titles["original"] = ja_title
        elif en_title:
            titles["original"] = en_title

        keywords = [
            item.attributes.title
            for item in parsed.included
            if item.type == "categories"
            and item.attributes.title
            and item.attributes.title.strip()
        ]

        return Metadata(
            titles=titles,
            original_language="ja",
            keywords=keywords,
        )
