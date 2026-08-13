"""License-safe publication storage abstraction.

OEM manual binaries are never committed to the repository. Callers store only
references (external URL, object-store key, or future ingestion handle). Actual
copyrighted content may be indexed only when the organization holds authorization.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

StorageKind = Literal["external_url", "object_storage", "none", "future_ingestion"]


@dataclass(frozen=True)
class StorageReference:
    kind: StorageKind
    uri: str = ""
    # Optional opaque key for object stores / future ingest pipelines.
    object_key: str = ""
    content_type: str = ""
    # Never store OEM binary payloads here — metadata / locator only.
    notes: str = ""

    def validate(self) -> None:
        if self.kind == "none":
            return
        if self.kind == "external_url" and not (self.uri or "").strip():
            raise ValueError("external_url storage requires uri")
        if self.kind == "object_storage" and not ((self.object_key or self.uri) or "").strip():
            raise ValueError("object_storage storage requires object_key or uri")
        if self.kind == "future_ingestion" and not (self.uri or self.object_key or "").strip():
            raise ValueError("future_ingestion storage requires a locator")


class PublicationStorageBackend(ABC):
    """Pluggable backend — resolve / register references without embedding files."""

    kind: StorageKind

    @abstractmethod
    def register(self, reference: StorageReference) -> StorageReference:
        raise NotImplementedError

    @abstractmethod
    def resolve(self, reference: StorageReference) -> StorageReference:
        raise NotImplementedError


class ExternalUrlStorage(PublicationStorageBackend):
    kind: StorageKind = "external_url"

    def register(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        return reference

    def resolve(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        return reference


class ObjectStorageReferenceBackend(PublicationStorageBackend):
    """Metadata-only object-store locator (S3/Azure/GCS key). No upload in this sprint."""

    kind: StorageKind = "object_storage"

    def register(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        return reference

    def resolve(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        return reference


class FutureIngestionBackend(PublicationStorageBackend):
    """Placeholder for authorized document ingestion pipelines (not AI/OCR in this sprint)."""

    kind: StorageKind = "future_ingestion"

    def register(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        return reference

    def resolve(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        return reference


class NullStorageBackend(PublicationStorageBackend):
    kind: StorageKind = "none"

    def register(self, reference: StorageReference) -> StorageReference:
        return StorageReference(kind="none")

    def resolve(self, reference: StorageReference) -> StorageReference:
        return StorageReference(kind="none")


_BACKENDS: dict[StorageKind, PublicationStorageBackend] = {
    "external_url": ExternalUrlStorage(),
    "object_storage": ObjectStorageReferenceBackend(),
    "future_ingestion": FutureIngestionBackend(),
    "none": NullStorageBackend(),
}


def get_storage_backend(kind: str) -> PublicationStorageBackend:
    normalized = (kind or "none").strip().lower()
    if normalized not in _BACKENDS:
        raise ValueError(f"Unsupported storage kind: {kind}")
    return _BACKENDS[normalized]  # type: ignore[index]


def normalize_storage(
    *,
    kind: str | None,
    uri: str | None = None,
    object_key: str | None = None,
    content_type: str | None = None,
    notes: str | None = None,
) -> StorageReference:
    ref = StorageReference(
        kind=(kind or "none").strip().lower(),  # type: ignore[arg-type]
        uri=(uri or "").strip(),
        object_key=(object_key or "").strip(),
        content_type=(content_type or "").strip(),
        notes=(notes or "").strip(),
    )
    backend = get_storage_backend(ref.kind)
    return backend.register(ref)
