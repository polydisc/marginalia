from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. SQLite embedded by default (ADR 0001), separable
    by pointing ``LMS_DATABASE_URL`` at e.g. Postgres."""

    model_config = SettingsConfigDict(
        env_prefix="LMS_", env_file=".env", extra="ignore"
    )

    database_url: str = "sqlite:///./library.db"

    # Days a readied hold waits on the shelf before it expires (a library-wide
    # setting, not part of the per-(category x material) loan policy).
    hold_pickup_window_days: int = 7
