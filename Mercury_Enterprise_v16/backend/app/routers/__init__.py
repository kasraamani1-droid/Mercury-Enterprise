from .connectors import router as connectors_router
from .ops import router as ops_router
from .admin import router as admin_router

__all__ = ["connectors_router", "ops_router", "admin_router"]
