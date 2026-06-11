from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MonitorConfig(BaseSettings):
    model_config = SettingsConfigDict()

    urls: list[str] = Field(min_length=1)
    failure_threshold: int = Field(default=3, ge=1)
    interval: int = Field(default=30, ge=1)
    timeout: int = Field(default=10, ge=1)
    log_file: str | None = None

    @field_validator("urls")
    @classmethod
    def urls_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one URL is required")
        return v


def from_cli(
    urls: tuple[str, ...],
    failure_threshold: int,
    interval: int,
    timeout: int,
    log_file: str | None,
) -> MonitorConfig:
    return MonitorConfig(
        urls=list(urls),
        failure_threshold=failure_threshold,
        interval=interval,
        timeout=timeout,
        log_file=log_file,
    )
