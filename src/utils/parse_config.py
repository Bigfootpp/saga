import json

from models.config import Config
from utils.string_encoding import decodeb64


def parse_config(b64config: str) -> Config:
    config_dict = json.loads(decodeb64(b64config))

    # For backwards compatibility
    if "languages" not in config_dict:
        config_dict["languages"] = [config_dict["language"]]

    return Config(**config_dict)
