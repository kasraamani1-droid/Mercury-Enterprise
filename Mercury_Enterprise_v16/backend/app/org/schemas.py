from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)


class CompanyOut(BaseModel):
    id: str
    name: str
    code: str
    status: str
    created_at: datetime | None = None


class OrganizationCreate(BaseModel):
    company_id: str
    organization_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)


class OrganizationOut(BaseModel):
    organization_id: str
    company_id: str
    name: str
    code: str
    status: str


class SiteCreate(BaseModel):
    organization_id: str
    site_id: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)
    timezone: str = "UTC"


class SiteOut(BaseModel):
    site_id: str
    organization_id: str
    name: str
    code: str
    status: str
    timezone: str = "UTC"


class DepartmentCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)
    site_id: str | None = None


class DepartmentOut(BaseModel):
    id: str
    organization_id: str
    site_id: str | None
    name: str
    code: str
    status: str


class TeamCreate(BaseModel):
    organization_id: str
    department_id: str
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=40)


class TeamOut(BaseModel):
    id: str
    organization_id: str
    department_id: str
    name: str
    code: str
    status: str


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=200)
    display_name: str = ""
    email: str = ""


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    email: str
    status: str


class MembershipCreate(BaseModel):
    username: str
    organization_id: str
    role: str = "Viewer"
    site_id: str | None = None
    department_id: str | None = None
    team_id: str | None = None
    notes: str = ""


class MembershipOut(BaseModel):
    id: str
    username: str
    organization_id: str
    role: str
    site_id: str | None = None
    department_id: str | None = None
    team_id: str | None = None
    status: str
