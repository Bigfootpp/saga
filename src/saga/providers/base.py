from abc import ABC, abstractmethod

from saga.models.query import MediaQuery
from saga.models.torrent import RawTorrent


class BaseProvider(ABC):
    @abstractmethod
    async def search(self, query: MediaQuery) -> list[RawTorrent]: ...