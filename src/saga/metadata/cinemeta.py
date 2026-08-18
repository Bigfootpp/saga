import asyncio
import re

import requests

from saga.metadata.base import MetadataProvider
from saga.models.media import Media
from saga.models.movie import Movie
from saga.models.series import Series

CINEMETA_TIMEOUT = 15.0


class MetadataNotFoundError(Exception):
    pass


class Cinemeta(MetadataProvider):
    async def get_metadata(self, id: str, type: str) -> Media | None:
        self.logger.info(f"Getting metadata for {type} with id {id}")
        full_id = id.split(":")
        url = f"https://v3-cinemeta.strem.io/meta/{type}/{full_id[0]}.json"

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.get(url, timeout=CINEMETA_TIMEOUT)
                data: dict = response.json()

                if not data or not data.get("meta"):
                    retry_count += 1
                    if retry_count == max_retries:
                        raise ValueError(
                            f"Empty response after {max_retries} retries for {id}"
                        )
                    await asyncio.sleep(1)
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
                        titles=[data["meta"]["name"]],
                        year=year,
                        type="movie",
                    )
                else:
                    result = Series(
                        id=id,
                        titles=[data["meta"]["name"]],
                        season=f"S{int(full_id[1]):02d}",
                        episode=f"E{int(full_id[2]):02d}",
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
                await asyncio.sleep(1)

        return None
