from abc import ABC

from saga.models.query import MetadataQuery


class BaseMetadataProvider(ABC):
    async def get_metadata(self, query: MetadataQuery): ...