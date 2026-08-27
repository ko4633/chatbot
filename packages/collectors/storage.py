"""Raw data lake. See docs/MASTER_SPEC.md §20 and docs/DATA_MODEL.md `raw_object`.

Content-hash addressed so re-fetching identical bytes never duplicates
storage. Two backends: local filesystem (default, zero external deps — used
in tests/dev) and MinIO (docker-compose service). Which one is used is a
config choice (`RAW_STORE_BACKEND`), never silently decided at runtime.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from packages.core.settings import Settings


@dataclass(frozen=True)
class RawObjectRef:
    content_hash: str
    mime_type: str
    byte_size: int
    storage_path: str


class RawObjectStore(ABC):
    @abstractmethod
    def put(self, content: bytes, mime_type: str) -> RawObjectRef: ...

    @staticmethod
    def hash_content(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()


class LocalFileStore(RawObjectStore):
    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes, mime_type: str) -> RawObjectRef:
        content_hash = self.hash_content(content)
        path = self._base / f"{content_hash}.bin"
        if not path.exists():
            path.write_bytes(content)
        return RawObjectRef(
            content_hash=content_hash,
            mime_type=mime_type,
            byte_size=len(content),
            storage_path=str(path),
        )


class MinIOStore(RawObjectStore):
    def __init__(
        self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool
    ) -> None:
        from minio import (
            Minio,  # imported lazily: only this backend needs the dependency at runtime
        )

        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self._bucket = bucket
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def put(self, content: bytes, mime_type: str) -> RawObjectRef:
        import io

        content_hash = self.hash_content(content)
        object_name = f"{content_hash[:2]}/{content_hash}.bin"
        try:
            self._client.stat_object(self._bucket, object_name)
        except Exception:  # noqa: BLE001 - minio raises a provider-specific NotFound
            self._client.put_object(
                self._bucket,
                object_name,
                io.BytesIO(content),
                length=len(content),
                content_type=mime_type,
            )
        return RawObjectRef(
            content_hash=content_hash,
            mime_type=mime_type,
            byte_size=len(content),
            storage_path=f"{self._bucket}/{object_name}",
        )


def get_raw_object_store(settings: Settings) -> RawObjectStore:
    if settings.raw_store_backend == "minio":
        return MinIOStore(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
    return LocalFileStore(settings.local_raw_store_path)
