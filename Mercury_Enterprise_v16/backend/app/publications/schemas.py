from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PublicationTypeOut(BaseModel):
    id: str
    code: str
    name: str
    category: str
    description: str
    status: str


class StorageRefIn(BaseModel):
    kind: str = "none"
    uri: str = ""
    object_key: str = ""
    content_type: str = ""
    notes: str = ""


class PublicationCreate(BaseModel):
    organization_id: str | None = None
    publication_type_code: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    manufacturer_id: str | None = None
    aircraft_model_id: str | None = None
    aircraft_variant: str = ""
    ata_chapter_id: str | None = None
    publication_number: str = Field(min_length=1, max_length=120)
    authority: str = ""
    access_classification: str = "internal"
    supersedes_publication_id: str | None = None
    # Optional initial revision
    revision_number: str | None = None
    revision_date: datetime | None = None
    effective_date: datetime | None = None
    storage: StorageRefIn | None = None
    change_summary: str = ""
    activate_revision: bool = True


class PublicationUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    manufacturer_id: str | None = None
    aircraft_model_id: str | None = None
    aircraft_variant: str | None = None
    ata_chapter_id: str | None = None
    authority: str | None = None
    supersedes_publication_id: str | None = None


class AccessClassificationUpdate(BaseModel):
    access_classification: str = Field(pattern="^(public|internal|restricted|licensed)$")


class RevisionCreate(BaseModel):
    revision_number: str = Field(min_length=1, max_length=80)
    revision_date: datetime | None = None
    effective_date: datetime | None = None
    supersedes_revision_id: str | None = None
    storage: StorageRefIn = Field(default_factory=StorageRefIn)
    change_summary: str = ""
    activate: bool = False


class RevisionOut(BaseModel):
    id: str
    organization_id: str
    publication_id: str
    revision_number: str
    revision_date: datetime | None
    effective_date: datetime | None
    status: str
    supersedes_revision_id: str | None
    storage_kind: str
    storage_uri: str
    storage_object_key: str
    storage_content_type: str
    storage_notes: str
    change_summary: str
    created_at: datetime
    updated_at: datetime


class PublicationOut(BaseModel):
    id: str
    organization_id: str
    publication_type_id: str
    publication_code: str
    title: str
    description: str
    manufacturer_id: str | None
    aircraft_model_id: str | None
    aircraft_variant: str
    ata_chapter_id: str | None
    publication_number: str
    authority: str
    status: str
    access_classification: str
    supersedes_publication_id: str | None
    current_revision_id: str | None
    current_revision_number: str | None = None
    created_at: datetime
    updated_at: datetime


class LibraryNodeOut(BaseModel):
    id: str
    label: str
    node_type: str
    count: int = 0
    meta: dict[str, str | int | None] = Field(default_factory=dict)


class LibraryBrowseOut(BaseModel):
    path: list[str]
    nodes: list[LibraryNodeOut]


class ComponentPublicationOut(BaseModel):
    component_id: str
    serial_number: str
    catalog_item_id: str
    part_number: str
    ata_chapter_id: str | None
    publications: list[PublicationOut]
