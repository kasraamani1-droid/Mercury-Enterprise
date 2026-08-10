from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..connectors.manager import connector_manager
from ..core.health import build_ops_health
from ..database import get_db
from ..ops import ResponseOrchestrationEngine
from ..ops.service import ResponseOrchestrationService

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])
_service = ResponseOrchestrationService()


@router.get("/health")
def ops_health(db: Session = Depends(get_db)) -> dict:
    return build_ops_health(db, connector_manager)


@router.post("/coordinate")
def coordinate(payload: dict, orchestrator: ResponseOrchestrationEngine = Depends(lambda: _service.orchestrator)) -> dict:
    decision = orchestrator.coordinate(
        event_type=payload.get("event_type", "unknown"),
        payload=payload.get("payload", {}),
        source="api",
    )
    return decision.to_dict()
