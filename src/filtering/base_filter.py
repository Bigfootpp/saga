from typing import TypeVar

from models.config import Config

FilterItem = TypeVar("FilterItem")


class BaseFilter[FilterItem]:
    def __init__(self, config: Config, additional_config: str | None = None):
        self.config = config
        self.item_type = additional_config

    def filter(self, data: list[FilterItem]) -> list[FilterItem]:
        raise NotImplementedError

    def can_filter(self) -> bool:
        raise NotImplementedError

    def __call__(self, data: list[FilterItem]) -> list[FilterItem]:
        if self.config is not None and self.can_filter():
            return self.filter(data)
        return data
