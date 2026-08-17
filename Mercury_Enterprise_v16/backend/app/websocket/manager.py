from __future__ import annotations

import asyncio
from fastapi import WebSocket


class ConnectionManager:
    """WebSocket fan-out scoped by organization and site.

    Heartbeats may omit tenant filters (broadcast to all authenticated sockets).
    Incident and timeline events must pass organization_id and site_id so
    cross-tenant subscribers never receive another tenant's payloads.
    """

    def __init__(self) -> None:
        self._connections: dict[WebSocket, dict[str, str]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        *,
        organization_id: str,
        site_id: str,
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = {
                "organization_id": str(organization_id),
                "site_id": str(site_id),
            }

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    async def broadcast(
        self,
        payload: dict,
        *,
        organization_id: str | None = None,
        site_id: str | None = None,
    ) -> None:
        stale: list[WebSocket] = []
        async with self._lock:
            items = list(self._connections.items())
        for websocket, scope in items:
            if organization_id is not None and scope.get("organization_id") != str(organization_id):
                continue
            if site_id is not None and scope.get("site_id") != str(site_id):
                continue
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(websocket)

    def connection_count(
        self,
        *,
        organization_id: str | None = None,
        site_id: str | None = None,
    ) -> int:
        """Test/ops helper: count sockets, optionally filtered by tenant."""
        count = 0
        for scope in self._connections.values():
            if organization_id is not None and scope.get("organization_id") != str(organization_id):
                continue
            if site_id is not None and scope.get("site_id") != str(site_id):
                continue
            count += 1
        return count


manager = ConnectionManager()
