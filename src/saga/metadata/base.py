import httpx

from saga.models.config import Config
from saga.models.media import Media
from saga.utils.logger import setup_logger


class MetadataProvider:
    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.AsyncClient()
        self.logger = setup_logger(__name__)

    async def get_metadata(self, id: str, type: str) -> Media | None:
        raise NotImplementedError
