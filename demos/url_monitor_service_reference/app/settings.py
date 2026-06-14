from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_path: str = "url_monitor.db"
    coordinator_tick_seconds: int = 5
    default_check_interval_seconds: int = 60
    default_timeout_seconds: int = 10
    default_failure_threshold: int = 3
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
