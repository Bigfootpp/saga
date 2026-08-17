import os
import queue
import threading
import time
import xml.etree.ElementTree as ET

import requests
from RTN import parse as rtn_parse

from saga.jackett.jackett_indexer import JackettIndexer
from saga.jackett.jackett_result import JackettResult
from saga.jackett.parser import parse_indexers, parse_results
from saga.models.config import Config
from saga.models.movie import Movie
from saga.models.series import Series
from saga.utils.detection import detect_languages
from saga.utils.logger import setup_logger


class JackettClient:
    REQUEST_TIMEOUT = 15.0

    def __init__(self, config: Config):
        self.logger = setup_logger(__name__)
        self._indexers: list[JackettIndexer] | None = None
        self._api_key = config.jackett_api_key
        self._base_url = f"{config.jackett_host}/api/v2.0"
        self._session = requests.Session()

    def search(self, media: Movie | Series) -> list[JackettResult]:
        self.logger.info(f"Started Jackett search for {media.type} {media.titles[0]}")

        indexers = self.get_indexers()

        results_queue: queue.Queue[list[list[JackettResult]]] = queue.Queue()

        def thread_target(indexer: JackettIndexer) -> None:
            self.logger.info(f"Searching on {indexer.title}")
            start_time = time.time()

            if isinstance(media, Movie):
                result = self._search_movie_indexer(media, indexer)
            elif isinstance(media, Series):
                result = self._search_series_indexer(media, indexer)
            else:
                raise TypeError("Only Movie and Series is allowed as media!")

            self.logger.info(
                f"Search on {indexer.title} took {time.time() - start_time} seconds "
                f"and found {sum(len(sublist) for sublist in result)} results"
            )

            results_queue.put(result)

        threads = []
        for indexer in indexers:
            thread = threading.Thread(target=thread_target, args=(indexer,))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        results: list[list[JackettResult]] = []
        while not results_queue.empty():
            results.extend(results_queue.get())

        flatten_results = [result for sublist in results for result in sublist]

        return self._post_process_results(flatten_results, media)

    def _search_movie_indexer(
        self, movie: Movie, indexer: JackettIndexer
    ) -> list[list[JackettResult]]:
        has_imdb_search_capability = (
            os.getenv("DISABLE_JACKETT_IMDB_SEARCH") != "true"
            and indexer.movie_search_capabilities is not None
            and "imdbid" in indexer.movie_search_capabilities
        )

        if has_imdb_search_capability:
            index_of_language = next(
                (index for index, lang in enumerate(movie.languages) if lang == "en"),
                None,
            )
            languages = ["en"]
            titles = (
                [movie.titles[index_of_language]]
                if index_of_language is not None
                else movie.titles
            )
        elif indexer.language == "en":
            languages = movie.languages
            titles = movie.titles
        else:
            index_of_language = [
                index
                for index, lang in enumerate(movie.languages)
                if lang == indexer.language or lang == "en"
            ]
            languages = [movie.languages[index] for index in index_of_language]
            titles = [movie.titles[index] for index in index_of_language]

        results: list[list[JackettResult]] = []

        for index, lang in enumerate(languages):
            params = {
                "apikey": self._api_key,
                "t": "movie",
                "cat": "2000",
                "q": titles[index],
                "year": movie.year,
            }

            if has_imdb_search_capability:
                params["imdbid"] = movie.id

            url = f"{self._base_url}/indexers/{indexer.id}/results/torznab/api"
            url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            try:
                response = self._session.get(url, timeout=self.REQUEST_TIMEOUT)
                response.raise_for_status()
                results.append(parse_results(response.text))
            except (requests.RequestException, ET.ParseError):
                self.logger.exception(
                    f"An exception occurred while searching for a movie on Jackett with indexer {indexer.title} and language {lang}."
                )

        return results

    def _search_series_indexer(
        self, series: Series, indexer: JackettIndexer
    ) -> list[list[JackettResult]]:
        season = str(int(series.season.replace("S", "")))
        episode = str(int(series.episode.replace("E", "")))

        has_imdb_search_capability = (
            os.getenv("DISABLE_JACKETT_IMDB_SEARCH") != "true"
            and indexer.tv_search_capabilities is not None
            and "imdbid" in indexer.tv_search_capabilities
        )
        if has_imdb_search_capability:
            index_of_language = next(
                (index for index, lang in enumerate(series.languages) if lang == "en"),
                None,
            )
            languages = ["en"] if index_of_language is not None else series.languages
            titles = (
                [series.titles[index_of_language]]
                if index_of_language is not None
                else series.titles
            )
        elif indexer.language == "en":
            languages = series.languages
            titles = series.titles
        else:
            index_of_language = [
                index
                for index, lang in enumerate(series.languages)
                if lang == indexer.language or lang == "en"
            ]
            languages = [series.languages[index] for index in index_of_language]
            titles = [series.titles[index] for index in index_of_language]

        results: list[list[JackettResult]] = []

        for index, lang in enumerate(languages):
            params = {
                "apikey": self._api_key,
                "t": "tvsearch",
                "cat": "5000",
                "q": titles[index],
            }

            if has_imdb_search_capability:
                params["imdbid"] = series.id

            url_title = f"{self._base_url}/indexers/{indexer.id}/results/torznab/api"
            url_title += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            url_season = f"{self._base_url}/indexers/{indexer.id}/results/torznab/api"
            params["season"] = season
            url_season += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            url_ep = f"{self._base_url}/indexers/{indexer.id}/results/torznab/api"
            params["ep"] = episode
            url_ep += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

            try:
                response_ep = self._session.get(url_ep, timeout=self.REQUEST_TIMEOUT)
                response_ep.raise_for_status()

                response_season = self._session.get(
                    url_season, timeout=self.REQUEST_TIMEOUT
                )
                response_season.raise_for_status()

                data_ep = parse_results(response_ep.text)
                data_season = parse_results(response_season.text)

                if data_ep:
                    results.append(data_ep)
                if data_season:
                    results.append(data_season)

                if not data_ep and not data_season:
                    response_title = self._session.get(
                        url_title, timeout=self.REQUEST_TIMEOUT
                    )
                    response_title.raise_for_status()
                    data_title = parse_results(response_title.text)
                    if data_title:
                        results.append(data_title)
            except (requests.RequestException, ET.ParseError):
                self.logger.exception(
                    f"An exception occurred while searching for a series on Jackett with indexer {indexer.title} and language {lang}."
                )

        return results

    def get_indexers(self) -> list[JackettIndexer]:
        if not self._indexers:
            self.logger.info("Indexer cache miss. Requesting API...")
            url = f"{self._base_url}/indexers/all/results/torznab/api?apikey={self._api_key}&t=indexers&configured=true"

            try:
                response = self._session.get(url, timeout=self.REQUEST_TIMEOUT)
                response.raise_for_status()
                self._indexers = parse_indexers(response.text)
                self.logger.info(
                    f"Successfully retrieved {len(self._indexers)} indexers from Jackett. Storing in cache..."
                )
            except (requests.RequestException, ET.ParseError):
                self.logger.exception(
                    "An exception occurred while getting indexers from Jackett."
                )
                return []
        return self._indexers

    def _post_process_results(
        self, results: list[JackettResult], media: Movie | Series
    ) -> list[JackettResult]:
        for result in results:
            raw_title = result.raw_title or ""
            parsed_result = rtn_parse(raw_title)
            result.parsed_data = parsed_result
            result.languages = detect_languages(raw_title)
            result.type = media.type

        return results
