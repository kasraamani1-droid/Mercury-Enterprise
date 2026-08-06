from __future__ import annotations

from collections.abc import Callable

from .base import BaseConnector
from .models import ConnectorRecord

ConnectorFactory = Callable[[ConnectorRecord], BaseConnector]


class ConnectorRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, ConnectorFactory] = {}

    def register(self, provider: str, factory: ConnectorFactory) -> None:
        key = provider.strip().lower()
        if not key:
            raise ValueError("provider cannot be empty")
        self._factories[key] = factory

    def create(self, record: ConnectorRecord) -> BaseConnector:
        try:
            factory = self._factories[record.provider.lower()]
        except KeyError as exc:
            raise ValueError(f"Unknown connector provider: {record.provider}") from exc
        return factory(record)

    def providers(self) -> list[str]:
        return sorted(self._factories)


registry = ConnectorRegistry()
