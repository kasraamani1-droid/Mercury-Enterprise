"""Local-disk object store for platform file metadata (pilot / RC).

Metadata remains in `platform_file_objects`; bytes live under
`MERCURY_FILE_STORAGE_ROOT` (default: `<cwd>/data/platform_files`).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from uuid import uuid4

from ..core.config import settings

logger = logging.getLogger("mercury.platform.file_storage")

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\-]+")


def storage_root() -> Path:
    configured = (getattr(settings, "file_storage_root", None) or os.getenv("MERCURY_FILE_STORAGE_ROOT") or "").strip()
    if configured:
        root = Path(configured)
    else:
        root = Path.cwd() / "data" / "platform_files"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _safe_filename(name: str) -> str:
    base = Path(name).name.strip() or "upload.bin"
    cleaned = _SAFE_NAME.sub("_", base)
    return cleaned[:180] or "upload.bin"


class LocalDiskObjectStore:
    """Writes opaque blobs and returns a file:// URI under the storage root."""

    def put_bytes(
        self,
        *,
        organization_id: str,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> tuple[str, str, int]:
        org = _SAFE_NAME.sub("_", organization_id.strip()) or "org"
        folder = storage_root() / org
        folder.mkdir(parents=True, exist_ok=True)
        object_name = f"{uuid4().hex}_{_safe_filename(filename)}"
        path = folder / object_name
        path.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        uri = path.resolve().as_uri()
        logger.info(
            "stored platform file org=%s bytes=%s content_type=%s",
            organization_id,
            len(content),
            content_type,
        )
        return uri, digest, len(content)

    def resolve_path(self, storage_uri: str) -> Path | None:
        text = (storage_uri or "").strip()
        if not text.startswith("file:"):
            return None
        try:
            if hasattr(Path, "from_uri"):
                path = Path.from_uri(text)  # type: ignore[attr-defined]
            else:
                # Python <3.13 fallback
                path = Path(text.replace("file:///", "").replace("file://", ""))
            resolved = path.resolve()
            root = storage_root()
            if resolved != root and root not in resolved.parents:
                return None
            return resolved if resolved.is_file() else None
        except Exception:
            logger.exception("failed to resolve storage_uri")
            return None


local_disk_store = LocalDiskObjectStore()
