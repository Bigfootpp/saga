import xml.etree.ElementTree as ET

import httpx
import requests

from saga.clients.jackett.jackett_item import JackettItem
from saga.clients.jackett.parser import parse_results
from saga.models.movie import Movie


class JackettClient:
    REQUEST_TIMEOUT = 15.0

    def __init__(self, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = f"{base_url}/api/v2.0"
        self._client = httpx.AsyncClient()

    async def search_serie(self, title: str, season: int, episode: int):
        all_results: list[JackettItem] = []
        seen_hashes: set[str] = set()

        def _add_if_new(results: list[JackettItem]):
            for r in results:
                if r.info_hash:
                    h = r.info_hash.lower().strip()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        all_results.append(r)

        base_params = {
            "apikey": self._api_key,
            "t": "tvsearch",
            "cat": "5000",
            "q": title,
        }

        # 1. Title + Season + Episode
        _add_if_new(await self._search_once(base_params, season, episode))

        # 2. Title + Season
        _add_if_new(await self._search_once(base_params, season, None))

        # 3. Title only
        _add_if_new(await self._search_once(base_params, None, None))

        return all_results

    # TODO: Refactor _search_movie to public search_movie method
    async def _search_movie(self, movie: Movie) -> list[JackettItem]:
        all_results: list[JackettItem] = []
        seen_hashes: set[str] = set()

        for title in movie.titles:
            params = {
                "apikey": self._api_key,
                "t": "movie",
                "cat": "2000",
                "q": title,
                "year": movie.year,
            }

            url = f"{self._base_url}/indexers/all/results/torznab/api"
            url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            try:
                response = await self._client.get(url, timeout=self.REQUEST_TIMEOUT)
                response.raise_for_status()
                results = parse_results(response.text)
                for r in results:
                    if r.info_hash and r.info_hash not in seen_hashes:
                        seen_hashes.add(r.info_hash)
                        all_results.append(r)
            except (requests.RequestException, ET.ParseError):
                pass

        return all_results

    async def _search_once(
        self, base_params: dict, season: int | None, episode: int | None
    ) -> list[JackettItem]:
        params = {**base_params}
        if season:
            params["season"] = season
        if episode:
            params["ep"] = episode

        url = f"{self._base_url}/indexers/all/results/torznab/api"
        url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

        try:
            response = await self._client.get(url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            return parse_results(response.text)
        except (requests.RequestException, ET.ParseError, ValueError):
            return []
