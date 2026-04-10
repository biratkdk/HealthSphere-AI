from __future__ import annotations

import json
import mimetypes
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import Settings, get_settings
from backend.app.models import ReportArtifact

try:
    from vercel.blob import BlobClient
except ImportError:  # pragma: no cover - optional until dependency is installed
    BlobClient = None  # type: ignore[assignment]


@dataclass(slots=True)
class StoredObject:
    content: bytes
    content_type: str
    filename: str
    storage_uri: str


class StorageService(ABC):
    backend_name = "local"

    @abstractmethod
    def ensure_ready(self) -> None: ...

    @abstractmethod
    def store_imaging_upload(
        self,
        patient_id: int,
        filename: str,
        payload: bytes,
        *,
        content_type: str | None = None,
    ) -> str: ...

    @abstractmethod
    def store_report_artifact(self, job_id: str, artifact: ReportArtifact) -> str: ...

    @abstractmethod
    def fetch_object(self, storage_uri: str) -> StoredObject: ...

    def _sanitize_name(self, filename: str, default: str) -> str:
        candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-")
        return candidate or default


class LocalStorageService(StorageService):
    backend_name = "local"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def ensure_ready(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def store_imaging_upload(
        self,
        patient_id: int,
        filename: str,
        payload: bytes,
        *,
        content_type: str | None = None,
    ) -> str:
        safe_name = self._sanitize_name(filename, default="image.bin")
        relative_path = Path("imaging") / f"patient-{patient_id}" / safe_name
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return self._uri_for(relative_path)

    def store_report_artifact(self, job_id: str, artifact: ReportArtifact) -> str:
        relative_path = Path("reports") / f"{job_id}.json"
        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(artifact.model_dump(mode="json"), indent=2), encoding="utf-8")
        return self._uri_for(relative_path)

    def fetch_object(self, storage_uri: str) -> StoredObject:
        path = self.resolve_uri(storage_uri)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".json":
            content_type = "application/json"
        return StoredObject(
            content=path.read_bytes(),
            content_type=content_type,
            filename=path.name,
            storage_uri=storage_uri,
        )

    def resolve_uri(self, storage_uri: str) -> Path:
        prefix = "local://"
        if not storage_uri.startswith(prefix):
            raise ValueError(f"Unsupported storage uri: {storage_uri}")
        relative = storage_uri[len(prefix) :]
        return self.root / relative

    def _uri_for(self, relative_path: Path) -> str:
        normalized = relative_path.as_posix().lstrip("/")
        return f"local://{normalized}"


class VercelBlobStorageService(StorageService):
    backend_name = "vercel_blob"

    def __init__(self, settings: Settings) -> None:
        if BlobClient is None:  # pragma: no cover - dependency guard
            raise RuntimeError("vercel package is required for vercel_blob storage.")
        self.settings = settings
        self.client = BlobClient()

    def ensure_ready(self) -> None:
        if not self.client.token:
            raise RuntimeError("BLOB_READ_WRITE_TOKEN is not configured.")

    def store_imaging_upload(
        self,
        patient_id: int,
        filename: str,
        payload: bytes,
        *,
        content_type: str | None = None,
    ) -> str:
        safe_name = self._sanitize_name(filename, default="image.bin")
        blob = self.client.put(
            self._blob_path("imaging", f"patient-{patient_id}", safe_name),
            payload,
            access=self.settings.blob_access,
            content_type=content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream",
            add_random_suffix=self.settings.blob_add_random_suffix,
        )
        return blob.url

    def store_report_artifact(self, job_id: str, artifact: ReportArtifact) -> str:
        payload = json.dumps(artifact.model_dump(mode="json"), indent=2).encode("utf-8")
        blob = self.client.put(
            self._blob_path("reports", f"{job_id}.json"),
            payload,
            access=self.settings.blob_access,
            content_type="application/json",
            add_random_suffix=False,
            overwrite=True,
        )
        return blob.url

    def fetch_object(self, storage_uri: str) -> StoredObject:
        result = self.client.get(storage_uri, access=self.settings.blob_access)
        if result is None or result.status_code != 200:
            raise FileNotFoundError(storage_uri)
        filename = Path(result.pathname).name
        return StoredObject(
            content=bytes(result.content),
            content_type=result.content_type or "application/octet-stream",
            filename=filename,
            storage_uri=storage_uri,
        )

    def _blob_path(self, *parts: str) -> str:
        normalized = [self.settings.blob_prefix.strip("/")] if self.settings.blob_prefix.strip("/") else []
        normalized.extend(part.strip("/") for part in parts if part.strip("/"))
        return "/".join(normalized)


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        settings = get_settings()
        if settings.resolved_storage_backend == "vercel_blob":
            _storage_service = VercelBlobStorageService(settings)
        else:
            _storage_service = LocalStorageService(Path(settings.resolved_storage_root).resolve())
    return _storage_service
