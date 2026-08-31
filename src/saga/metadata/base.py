from abc import ABC, abstractmethod

from saga.models.metadata import Metadata, MetadataQuery


class BaseMetadataProvider(ABC):
    @abstractmethod
    async def get_metadata(self, query: MetadataQuery) -> Metadata: ...
