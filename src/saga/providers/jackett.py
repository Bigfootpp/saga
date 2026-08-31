from urllib.parse import urljoin

import httpx

from saga.models.query import MediaQuery, MovieQuery, SeriesQuery
from saga.models.torrent import RawTorrent
from saga.providers.base import BaseProvider
from saga.providers.exceptions import ProviderStatusError, ProviderTimeoutError
from saga.utils.torznab import parse


class JackettProvider(BaseProvider):
    def __init__(
            self,
            base_url: str,
            api_key: str,
            client: httpx.AsyncClient | None = None,
            timeout: float = 15.0
    ):
        self.base_url = urljoin(base_url, "api/v2.0") if not base_url.endswith("api/v2.0") else base_url
        self.api_key = api_key
        self.client = client or httpx.AsyncClient()
        self.timeout = timeout

    async def search(self, query: MediaQuery) -> list[RawTorrent]:
        match query:
            case SeriesQuery():
                return await self._search_series(query=query)
            case MovieQuery():
                return await self._search_movie(query=query)

    async def _search_series(self, query: SeriesQuery) -> list[RawTorrent]:
        result: list[RawTorrent] = []

        base_url = f"{self.base_url}/indexers/all/results/torznab/api"

        param = {
            "apikey": self.api_key,
            "t": "tvsearch",
            "q": query.title,
            "season": query.season,
            "ep": query.episode
        }

        try:
            result.extend(await self._search(base_url, param))
            param.pop("ep")
            result.extend(await self._search(base_url, param))
            param.pop("season")
            result.extend(await self._search(base_url, param))
        except httpx.TimeoutException:
            raise ProviderTimeoutError("Jackett take too long to respond")
        except httpx.HTTPStatusError as e:
            raise ProviderStatusError(f"Jackett: error {e.response.status_code}")

        result = list({t.info_hash.lower(): t for t in result}.values())

        return result

    async def _search_movie(self, query: MovieQuery) -> list[RawTorrent]:
        result: list[RawTorrent] = []

        base_url = f"{self.base_url}/indexers/all/results/torznab/api"

        param = {
            "apikey": self.api_key,
            "t": "movie",
            "q": query.title,
        }

        try:
            result.extend(await self._search(base_url, param))
        except httpx.TimeoutException:
            raise ProviderTimeoutError()
        except httpx.HTTPStatusError:
            raise ProviderStatusError()

        result = list({t.info_hash.lower(): t for t in result}.values())

        return result


    async def _search(self, url: str, params: dict[str, str]) -> list[RawTorrent]:
        response = await self.client.get(url=url, timeout=self.timeout, params=params)
        response.raise_for_status()
        return parse(response.text)