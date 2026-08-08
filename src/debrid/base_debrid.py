import time
from typing import Any

import requests

from models.config import Config
from utils.logger import setup_logger

HTTP_TIMEOUT = 15.0


class BaseDebrid:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(__name__)
        self._session = requests.Session()

    def get_json_response(
        self,
        url: str,
        method: str = "get",
        data: dict | bytes | None = None,
        headers: dict | None = None,
        files: dict | None = None,
        **kwargs: Any,
    ) -> dict | None:
        if method == "get":
            response = self._session.get(url, headers=headers, **kwargs)
        elif method == "post":
            response = self._session.post(
                url, data=data, headers=headers, files=files, **kwargs
            )
        elif method == "put":
            response = self._session.put(url, data=data, headers=headers, **kwargs)
        elif method == "delete":
            response = self._session.delete(url, headers=headers, **kwargs)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.ok:
            try:
                return response.json()
            except ValueError:
                self.logger.error(f"Failed to parse response as JSON: {response.text}")
                return None
        else:
            self.logger.error(f"Request failed with status code {response.status_code}")
            return None

    def wait_for_ready_status(
        self, check_status_func, timeout: int = 30, interval: int = 5
    ) -> bool:
        self.logger.info(f"Waiting for {timeout} seconds to cache.")
        start_time = time.time()
        while time.time() - start_time < timeout:
            if check_status_func():
                self.logger.info("File is ready!")
                return True
            time.sleep(interval)
        self.logger.info("Waiting timed out.")
        return False

    def download_torrent_file(self, download_url: str) -> bytes:
        response = self._session.get(download_url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.content

    def get_stream_link(self, query_string: str, ip: str | None = None) -> str:
        raise NotImplementedError

    def add_magnet(self, magnet: str, ip: str | None = None) -> dict | None:
        raise NotImplementedError

    def get_availability_bulk(
        self, hashes_or_magnets: list[str], ip: str | None = None
    ) -> dict:
        raise NotImplementedError
