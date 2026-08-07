import os
import queue
import threading
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests
from RTN import parse as rtn_parse

from jackett.jackett_indexer import JackettIndexer
from jackett.jackett_result import JackettResult
from models.config import Config
from models.movie import Movie
from models.series import Series
from utils.detection import detect_languages
from utils.logger import setup_logger


class JackettService:
    def __init__(self, config: Config):
        self.logger = setup_logger(__name__)
        self._indexers: list[JackettIndexer] | None = None
        self._api_key = config.jackettApiKey
        self._base_url = f"{config.jackettHost}/api/v2.0"
        self._session = requests.Session()

    def search(self, media) -> list[JackettResult]:
        self.logger.info(f"Started Jackett search for {media.type} {media.titles[0]}")

        indexers = self.get_indexers()
        threads = []
        results_queue: queue.Queue[Any] = queue.Queue()

        def thread_target(media, indexer: JackettIndexer):
            self.logger.info(f"Searching on {indexer.title}")
            start_time = time.time()

            if isinstance(media, Movie):
                result = self._search_movie_indexer(media, indexer)
            elif isinstance(media, Series):
                result = self._search_series_indexer(media, indexer)
            else:
                raise TypeError("Only Movie and Series is allowed as media!")

            self.logger.info(
                f"Search on {indexer.title} took {time.time() - start_time} seconds and found {sum(len(sublist) for sublist in result)} results"
            )

            results_queue.put(result)

        for indexer in indexers:
            threads.append(
                threading.Thread(target=thread_target, args=(media, indexer))
            )

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        results = []

        while not results_queue.empty():
            results.extend(results_queue.get())

        flatten_results = [result for sublist in results for result in sublist]

        return self._post_process_results(flatten_results, media)

    def _search_movie_indexer(
        self, movie: Movie, indexer: JackettIndexer
    ) -> list[list[JackettResult]]:
        has_imdb_search_capability = (
            os.getenv("DISABLE_JACKETT_IMDB_SEARCH") != "true"
            and indexer.movie_search_capatabilities is not None
            and "imdbid" in indexer.movie_search_capatabilities
        )

        if has_imdb_search_capability:
            languages = ["en"]
            index_of_language = next(
                index for index, lang in enumerate(movie.languages) if lang == "en"
            )
            titles = [movie.titles[index_of_language]]
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

        results = []

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
                response = self._session.get(url)
                response.raise_for_status()
                results.append(self._get_torrent_links_from_xml(response.text))
            except Exception:
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
            and indexer.tv_search_capatabilities is not None
            and "imdbid" in indexer.tv_search_capatabilities
        )
        if has_imdb_search_capability:
            languages = ["en"]
            index_of_language = next(
                index for index, lang in enumerate(series.languages) if lang == "en"
            )
            titles = [series.titles[index_of_language]]
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

        results = []

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
                response_ep = self._session.get(url_ep)
                response_ep.raise_for_status()

                response_season = self._session.get(url_season)
                response_season.raise_for_status()

                data_ep = self._get_torrent_links_from_xml(response_ep.text)
                data_season = self._get_torrent_links_from_xml(response_season.text)

                if data_ep:
                    results.append(data_ep)
                if data_season:
                    results.append(data_season)

                if not data_ep and not data_season:
                    response_title = self._session.get(url_title)
                    response_title.raise_for_status()
                    data_title = self._get_torrent_links_from_xml(response_title.text)
                    if data_title:
                        results.append(data_title)
            except Exception:
                self.logger.exception(
                    f"An exception occurred while searching for a series on Jackett with indexer {indexer.title} and language {lang}."
                )

        return results

    def get_indexers(self) -> list[JackettIndexer]:
        if not self._indexers:
            self.logger.info("Indexer cache miss. Requesting API...")
            url = f"{self._base_url}/indexers/all/results/torznab/api?apikey={self._api_key}&t=indexers&configured=true"

            try:
                response = self._session.get(url)
                response.raise_for_status()
                self._indexers = self._get_indexer_from_xml(response.text)
                self.logger.info(
                    f"Successfully retrieved {len(self._indexers)} indexers from Jackett. Storing in cache..."
                )
            except Exception:
                self.logger.exception(
                    "An exception occurred while getting indexers from Jackett."
                )
                return []
        return self._indexers

    def _get_indexer_from_xml(self, xml_content: str) -> list[JackettIndexer]:
        xml_root = ET.fromstring(xml_content)

        indexer_list = []
        for item in xml_root.findall(".//indexer"):
            indexer = JackettIndexer()

            indexer.title = item.findtext("title")
            indexer.id = item.attrib.get("id")
            indexer.link = item.findtext("link")
            indexer.type = item.findtext("type")
            language_text = item.findtext("language")
            if language_text and language_text.split("-")[0] in ["pt"]:
                indexer.language = language_text
            elif language_text:
                indexer.language = language_text.split("-")[0]

            self.logger.info(
                f"Indexer: {indexer.title} - {indexer.link} - {indexer.type}"
            )

            movie_search = item.find('.//searching/movie-search[@available="yes"]')
            tv_search = item.find('.//searching/tv-search[@available="yes"]')

            if movie_search is not None:
                indexer.movie_search_capatabilities = movie_search.attrib[
                    "supportedParams"
                ].split(",")
            else:
                self.logger.info(f"Movie search not available for {indexer.title}")

            if tv_search is not None:
                indexer.tv_search_capatabilities = tv_search.attrib[
                    "supportedParams"
                ].split(",")
            else:
                self.logger.info(f"TV search not available for {indexer.title}")

            indexer_list.append(indexer)

        return indexer_list

    def _get_torrent_links_from_xml(self, xml_content: str) -> list[JackettResult]:
        xml_root = ET.fromstring(xml_content)

        result_list = []
        for item in xml_root.findall(".//item"):
            seeders_attr = item.find(
                './/torznab:attr[@name="seeders"]',
                namespaces={"torznab": "http://torznab.com/schemas/2015/feed"},
            )
            if seeders_attr is None:
                continue

            seeders = seeders_attr.attrib.get("value", "0")
            if int(seeders) <= 0:
                continue

            raw_title = item.findtext("title")
            size = item.findtext("size")
            link = item.findtext("link")
            indexer = item.findtext("jackettindexer")
            privacy = item.findtext("type")

            magnet = item.find(
                './/torznab:attr[@name="magneturl"]',
                namespaces={"torznab": "http://torznab.com/schemas/2015/feed"},
            )
            magnet_val = magnet.attrib["value"] if magnet is not None else None

            info_hash = item.find(
                './/torznab:attr[@name="infohash"]',
                namespaces={"torznab": "http://torznab.com/schemas/2015/feed"},
            )
            info_hash_val = info_hash.attrib["value"] if info_hash is not None else None

            result = JackettResult(
                rawTitle=raw_title,
                size=size,
                link=link,
                indexer=indexer,
                seeders=seeders,
                magnet=magnet_val,
                infoHash=info_hash_val,
                privacy=privacy,
                type=None,
            )

            result_list.append(result)

        return result_list

    def _post_process_results(
        self, results: list[JackettResult], media
    ) -> list[JackettResult]:
        for result in results:
            raw_title = result.raw_title or ""
            parsed_result = rtn_parse(raw_title)
            result.parsed_data = parsed_result
            result.languages = detect_languages(raw_title)
            result.type = media.type

        return results
