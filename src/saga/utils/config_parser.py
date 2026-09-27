import base64

from saga.models.config import UserConfig


def parse_config(b64config: str) -> UserConfig:
    decoded_config = base64.b64decode(b64config).decode()
    config = UserConfig.model_validate_json(decoded_config)
    return config
