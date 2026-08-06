from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("MERCURY_APP_NAME", "Mercury Enterprise API")
    version: str = os.getenv("MERCURY_VERSION", "16.0.0")
    environment: str = os.getenv("MERCURY_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./mercury.db")
    cors_origins: list[str] = None  # type: ignore[assignment]
    api_key: str = os.getenv("MERCURY_API_KEY", "")
    seed_demo_data: bool = os.getenv("MERCURY_SEED_DEMO", "true").lower() == "true"

    def __post_init__(self) -> None:
        object.__setattr__(self, "cors_origins", _csv("MERCURY_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"))


settings = Settings()
