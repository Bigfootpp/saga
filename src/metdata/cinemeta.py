import re
import time

import requests

from metdata.metadata_provider_base import MetadataProvider
from models.movie import Movie
from models.series import Series


class MetadataNotFoundError(Exception):
    pass


class Cinemeta(MetadataProvider):
    def get_metadata(self, id: str, type: str):
        self.logger.info(f"Getting metadata for {type} with id {id}")
        full_id = id.split(":")
        url = f"https://v3-cinemeta.strem.io/meta/{type}/{full_id[0]}.json"

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.get(url)
                data: dict = response.json()

                if not data or not data.get("meta"):
                    retry_count += 1
                    if retry_count == max_retries:
                        raise ValueError(
                            f"Empty response after {max_retries} retries for {id}"
                        )
                    time.sleep(1)
                    continue

                if type == "movie":
                    year = data["meta"].get("year")
                    if not year:
                        release_info = data["meta"].get("releaseInfo")
                        re_result = re.search(r"\d{4}", release_info)
                        if re_result:
                            year = re_result.group()

                    result = Movie(
                        id=id,
                        titles=[self.replace_weird_characters(data["meta"]["name"])],
                        year=year,
                        languages=["en"],
                        type="movie",
                    )
                else:
                    result = Series(
                        id=id,
                        titles=[self.replace_weird_characters(data["meta"]["name"])],
                        season=f"S{int(full_id[1]):02d}",
                        episode=f"E{int(full_id[2]):02d}",
                        languages=["en"],
                        type="series",
                        seasonfile=False,
                    )

                self.logger.info(f"Got metadata for {type} with id {id}")
                return result

            except (requests.RequestException, ValueError, KeyError) as e:
                retry_count += 1
                if retry_count == max_retries:
                    raise MetadataNotFoundError(
                        f"Failed to get metadata after {max_retries} retries: {e!s}"
                    )
                time.sleep(1)
