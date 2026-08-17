"""Program 11 — Mercury Universal Data Fabric.

Enterprise knowledge-graph substrate over relational domain tables.
Every Mercury product connects entities through Digital Passports,
universal relationships, fabric events, and governance — without
duplicating domain schemas.
"""

from .service import FabricService

__all__ = ["FabricService"]
