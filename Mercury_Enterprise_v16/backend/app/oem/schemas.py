from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

ORM = ConfigDict(from_attributes=True)


class ManufacturerOut(BaseModel):
    model_config = ORM

    id: str
    code: str
    name: str
    category: str
    country_code: str
    portal_status: str
    capabilities_json: str
    ai_metadata_json: str
    status: str
    created_at: datetime
