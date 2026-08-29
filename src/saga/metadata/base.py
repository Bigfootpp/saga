from abc import ABC, abstractmethod

from saga.models.query import MetadataQuery


class BaseMetadataProvider(ABC):
    @abstractmethod
    async def get_metadata(self, query: MetadataQuery): ...