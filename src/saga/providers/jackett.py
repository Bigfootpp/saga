import httpx

from saga.models.query import MediaQuery
from saga.models.torrent import RawTorrent
from saga.providers.base import BaseProvider


class JackettProvider(BaseProvider):
    def __init__(self, base_url: str, api_key: str, client: httpx.AsyncClient | None):
        self.base_url = base_url
        self.api_key = api_key
        self.client = client or httpx.AsyncClient()

    async def search(self, query: MediaQuery) -> list[RawTorrent]:
        ...