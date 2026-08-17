"""License-safe publication storage abstraction.

OEM manual binaries are never committed to the repository. Callers store only
references (external URL, object-store key, local filesystem path under the
configured publications root, or future ingestion handle). Actual copyrighted
content may be indexed only when the organization holds authorization.
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from ..core.config import settings

logger = logging.getLogger("mercury.publications.storage")

StorageKind = Literal[
    "external_url",
    "object_storage",
    "local_filesystem",
    "none",
    "future_ingestion",
]

_SAFE = re.compile(r"[^A-Za-z0-9._\-]+")


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
        if self.kind == "local_filesystem" and not ((self.object_key or self.uri) or "").strip():
            raise ValueError("local_filesystem storage requires object_key or uri")
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


class LocalFilesystemStorage(PublicationStorageBackend):
    """Pilot local disk locator under MERCURY_PUBLICATIONS_STORAGE_ROOT.

    Registers a path/key relative to the publications root. Does not write OEM
    binaries into the repository tree — only ensures the org folder exists and
    returns a file:// URI for authorized local content the operator supplies.
    """

    kind: StorageKind = "local_filesystem"

    @staticmethod
    def root() -> Path:
        configured = (
            getattr(settings, "publications_storage_root", None)
            or os.getenv("MERCURY_PUBLICATIONS_STORAGE_ROOT")
            or ""
        ).strip()
        root = Path(configured) if configured else Path.cwd() / "data" / "publications"
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve()

    def register(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        key = (reference.object_key or Path(reference.uri).name or uuid4().hex).strip()
        key = _SAFE.sub("_", key)[:180] or uuid4().hex
        folder = self.root() / "refs"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / key
        # Touch placeholder marker only when neither uri nor existing file is provided.
        if not path.exists() and not (reference.uri or "").startswith("file:"):
            path.write_text("", encoding="utf-8")
        uri = path.resolve().as_uri() if path.exists() else (reference.uri or path.resolve().as_uri())
        return StorageReference(
            kind="local_filesystem",
            uri=uri,
            object_key=key,
            content_type=reference.content_type,
            notes=reference.notes or "local_filesystem",
        )

    def resolve(self, reference: StorageReference) -> StorageReference:
        reference.validate()
        root = self.root()
        if reference.object_key:
            path = (root / "refs" / reference.object_key).resolve()
            if root not in path.parents and path != root:
                raise ValueError("local_filesystem object_key escapes storage root")
            if path.is_file():
                return StorageReference(
                    kind="local_filesystem",
                    uri=path.as_uri(),
                    object_key=reference.object_key,
                    content_type=reference.content_type,
                    notes=reference.notes,
                )
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
    "local_filesystem": LocalFilesystemStorage(),
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
