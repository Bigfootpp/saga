import xml.etree.ElementTree as ET

import httpx
import requests
from RTN import parse as rtn_parse

from saga.jackett.jackett_result import JackettResult
from saga.jackett.parser import parse_results
from saga.models.config import Config
from saga.models.media import Media
from saga.models.movie import Movie
from saga.models.series import Series
from saga.utils.detection import detect_languages


class JackettClient:
    REQUEST_TIMEOUT = 15.0

    def __init__(self, config: Config):
        self._api_key = config.jackett_api_key
        self._base_url = f"{config.jackett_host}/api/v2.0"
        self._client = httpx.AsyncClient()

    async def search(self, media: Media) -> list[JackettResult]:

        all_results: list[JackettResult] = []
        seen_hashes: set[str] = set()

        if isinstance(media, Movie):
            raw_results = await self._search_movie(media)
        elif isinstance(media, Series):
            raw_results = await self._search_series(media)
        else:
            return []

        for result in raw_results:
            if result.info_hash and result.info_hash not in seen_hashes:
                seen_hashes.add(result.info_hash)
                all_results.append(result)

        return self._post_process_results(all_results, media)

    async def _search_movie(self, movie: Movie) -> list[JackettResult]:
        all_results: list[JackettResult] = []
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

    async def _search_series(self, series: Series) -> list[JackettResult]:
        all_results: list[JackettResult] = []
        seen_hashes: set[str] = set()

        season = str(int(series.season.replace("S", "")))
        episode = str(int(series.episode.replace("E", "")))

        def _add_if_new(results: list[JackettResult]):
            for r in results:
                if r.info_hash:
                    h = r.info_hash.lower().strip()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        all_results.append(r)

        for title in series.titles:
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

    async def _search_once(
        self, base_params: dict, season: str | None, episode: str | None
    ) -> list[JackettResult]:
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
        except (requests.RequestException, ET.ParseError):
            return []

    def _post_process_results(
        self, results: list[JackettResult], media: Media
    ) -> list[JackettResult]:
        for result in results:
            raw_title = result.raw_title or ""
            parsed_result = rtn_parse(raw_title)
            result.parsed_data = parsed_result
            result.languages = detect_languages(raw_title)
            result.type = media.type

        return results
