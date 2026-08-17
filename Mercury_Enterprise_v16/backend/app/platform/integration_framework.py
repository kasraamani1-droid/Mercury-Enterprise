"""Integration Framework — OEM, Authority, Marketplace, and external connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass
class IntegrationDescriptor:
    code: str
    name: str
    category: str  # oem | authority | marketplace | connector | scim | sso | ldap
    vendor: str = ""
    capabilities: list[str] = field(default_factory=list)
    status: str = "ready"  # ready | connected | disabled
    metadata: dict[str, Any] = field(default_factory=dict)


class IntegrationAdapter(Protocol):
    def descriptor(self) -> IntegrationDescriptor: ...

    def health(self) -> dict[str, Any]: ...


class IntegrationFramework:
    """Registry for future SSO/SCIM/LDAP/Okta/Azure AD and OEM/Authority portals.

    No live IdP calls in this release — adapters register readiness contracts only.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, IntegrationAdapter] = {}
        self._seed()

    def _seed(self) -> None:
        for item in (
            IntegrationDescriptor("sso.oidc", "OIDC / SSO", "sso", capabilities=["login", "logout"]),
            IntegrationDescriptor("sso.azure_ad", "Microsoft Azure AD", "sso", vendor="Microsoft"),
            IntegrationDescriptor("sso.okta", "Okta", "sso", vendor="Okta"),
            IntegrationDescriptor("dir.ldap", "LDAP Directory", "ldap", capabilities=["bind", "search"]),
            IntegrationDescriptor("dir.scim", "SCIM 2.0 Provisioning", "scim", capabilities=["users", "groups"]),
            IntegrationDescriptor("oem.bombardier", "Bombardier", "oem", vendor="Bombardier"),
            IntegrationDescriptor("oem.airbus", "Airbus", "oem", vendor="Airbus"),
            IntegrationDescriptor("oem.boeing", "Boeing", "oem", vendor="Boeing"),
            IntegrationDescriptor("oem.embraer", "Embraer", "oem", vendor="Embraer"),
            IntegrationDescriptor("oem.atr", "ATR", "oem", vendor="ATR"),
            IntegrationDescriptor("oem.textron", "Textron Aviation", "oem", vendor="Textron"),
            IntegrationDescriptor("oem.pw", "Pratt & Whitney", "oem", vendor="Pratt & Whitney"),
            IntegrationDescriptor("oem.ge", "GE Aerospace", "oem", vendor="GE Aerospace"),
            IntegrationDescriptor("oem.rr", "Rolls-Royce", "oem", vendor="Rolls-Royce"),
            IntegrationDescriptor("oem.honeywell", "Honeywell", "oem", vendor="Honeywell"),
            IntegrationDescriptor("oem.safran", "Safran", "oem", vendor="Safran"),
            IntegrationDescriptor("oem.collins", "Collins Aerospace", "oem", vendor="Collins Aerospace"),
            IntegrationDescriptor("oem.thales", "Thales", "oem", vendor="Thales"),
            IntegrationDescriptor("oem.garmin", "Garmin", "oem", vendor="Garmin"),
            IntegrationDescriptor("authority.tc", "Transport Canada", "authority", vendor="Transport Canada"),
            IntegrationDescriptor("authority.faa", "FAA", "authority", vendor="FAA"),
            IntegrationDescriptor("authority.easa", "EASA", "authority", vendor="EASA"),
            IntegrationDescriptor("authority.caa_uk", "CAA UK", "authority", vendor="CAA UK"),
            IntegrationDescriptor("authority.anac", "ANAC", "authority", vendor="ANAC"),
            IntegrationDescriptor("authority.casa", "CASA", "authority", vendor="CASA"),
            IntegrationDescriptor("authority.icao", "ICAO", "authority", vendor="ICAO"),
            IntegrationDescriptor(
                "marketplace.core",
                "Mercury Marketplace",
                "marketplace",
                capabilities=["parts", "suppliers", "tools", "calibration", "repairs", "training", "careers", "publications"],
            ),
        ):
            self.register(_StaticAdapter(item))

    def register(self, adapter: IntegrationAdapter) -> None:
        desc = adapter.descriptor()
        self._adapters[desc.code] = adapter

    def get(self, code: str) -> IntegrationAdapter | None:
        return self._adapters.get(code)

    def list(
        self, *, category: str | None = None, status: str | None = None
    ) -> list[IntegrationDescriptor]:
        out: list[IntegrationDescriptor] = []
        for adapter in self._adapters.values():
            d = adapter.descriptor()
            if category and d.category != category:
                continue
            if status and d.status != status:
                continue
            out.append(d)
        return sorted(out, key=lambda d: d.code)

    def health_report(self) -> dict[str, Any]:
        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "integrations": [
                {"code": a.descriptor().code, **a.health()} for a in self._adapters.values()
            ],
        }


class _StaticAdapter:
    def __init__(self, descriptor: IntegrationDescriptor) -> None:
        self._descriptor = descriptor

    def descriptor(self) -> IntegrationDescriptor:
        return self._descriptor

    def health(self) -> dict[str, Any]:
        return {"status": self._descriptor.status, "live": False, "message": "readiness contract only"}


integration_framework = IntegrationFramework()
