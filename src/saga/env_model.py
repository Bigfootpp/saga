from pathlib import Path

import platformdirs
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    jackett_base_url: str = "http://localhost:9117"
    jackett_api_key: str = Field(default=...)
    tmdb_api_key: str = Field(default=...)
    saga_data_dir: Path = Field(
        default_factory=lambda: Path(platformdirs.user_data_dir("saga"))
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


env = EnvSettings()
