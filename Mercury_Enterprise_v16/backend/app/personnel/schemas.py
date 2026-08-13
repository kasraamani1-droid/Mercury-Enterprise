from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    organization_id: str | None = None
    employee_number: str = Field(min_length=1, max_length=80)
    full_name: str = Field(min_length=1, max_length=200)
    department_id: str | None = None
    position_title: str = ""
    email: str = ""
    status: str = "active"
    user_username: str | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    department_id: str | None = None
    position_title: str | None = None
    email: str | None = None
    status: str | None = None
    user_username: str | None = None


class EmployeeOut(BaseModel):
    id: str
    organization_id: str
    employee_number: str
    full_name: str
    department_id: str | None
    position_title: str
    email: str
    status: str
    user_username: str | None
    created_at: datetime
    updated_at: datetime


class QualificationCreate(BaseModel):
    qualification_type: str = Field(pattern="^(ame_license|rating|type_rating|aca|training|other)$")
    code: str = ""
    description: str = ""
    authority: str = ""
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    status: str = "active"


class QualificationOut(BaseModel):
    id: str
    employee_id: str
    qualification_type: str
    code: str
    description: str
    authority: str
    issued_at: datetime | None
    expires_at: datetime | None
    status: str
    created_at: datetime


class AuthorizationCreate(BaseModel):
    auth_type: str = Field(pattern="^(aca|independent_inspection|stamp)$")
    scope: str = ""
    aircraft_model_id: str | None = None
    ata_chapter_id: str | None = None
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    status: str = "active"


class AuthorizationOut(BaseModel):
    id: str
    employee_id: str
    auth_type: str
    scope: str
    aircraft_model_id: str | None
    ata_chapter_id: str | None
    issued_at: datetime | None
    expires_at: datetime | None
    status: str
    created_at: datetime


class StampCreate(BaseModel):
    stamp_code: str = Field(min_length=1, max_length=80)
    label: str = ""
    status: str = "active"


class StampOut(BaseModel):
    id: str
    employee_id: str
    stamp_code: str
    label: str
    status: str
    created_at: datetime
