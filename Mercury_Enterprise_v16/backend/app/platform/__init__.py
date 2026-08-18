"""Mercury Enterprise Platform Foundation (Program A).

Reusable services shared by every Mercury product: identity, organization
extensions, RBAC extensions, workflow engine, notifications, files, search,
configuration. Domain modules must not duplicate these concerns.
"""

from .service import PlatformService
from .event_framework import event_framework
from .integration_framework import integration_framework

__all__ = ["PlatformService", "event_framework", "integration_framework"]
