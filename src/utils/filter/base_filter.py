from typing import Any

from models.config import Config


class BaseFilter:
    def __init__(self, config: Config, additional_config: str | None = None):
        self.config = config
        self.item_type = additional_config

    def filter(self, data: list[Any]) -> list[Any]:
        raise NotImplementedError

    def can_filter(self) -> bool:
        raise NotImplementedError

    def __call__(self, data: list[Any]) -> list[Any]:
        if self.config is not None and self.can_filter():
            return self.filter(data)
        return data
