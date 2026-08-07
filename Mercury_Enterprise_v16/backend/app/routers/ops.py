from fastapi import APIRouter, Depends

from ..ops import ResponseOrchestrationEngine
from ..ops.service import ResponseOrchestrationService

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])
_service = ResponseOrchestrationService()


@router.get("/health")
def ops_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/coordinate")
def coordinate(payload: dict, orchestrator: ResponseOrchestrationEngine = Depends(lambda: _service.orchestrator)) -> dict:
    decision = orchestrator.coordinate(
        event_type=payload.get("event_type", "unknown"),
        payload=payload.get("payload", {}),
        source="api",
    )
    return decision.to_dict()
