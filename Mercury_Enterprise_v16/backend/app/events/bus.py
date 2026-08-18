"""Compatibility shim — canonical Event Framework lives in platform."""

from __future__ import annotations

from ..platform.event_framework import EventFramework, event_framework

# Historical import path used by connectors
event_bus = event_framework
EventBus = EventFramework

__all__ = ["EventBus", "event_bus"]
