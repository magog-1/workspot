"""MinIO client for storing space photos."""

from __future__ import annotations

import io
import os
import uuid
from datetime import timedelta
from urllib.parse import urlparse

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    Minio = None  # type: ignore[assignment]
    S3Error = Exception  # type: ignore[assignment, misc]


DEFAULT_BUCKET = "workspot-media"


def _parse_endpoint(url: str) -> tuple[str, bool]:
    parsed = urlparse(url)
    secure = parsed.scheme == "https"
    netloc = parsed.netloc or parsed.path
    return netloc, secure


class MinIOClient:
    """Thin wrapper around the official minio SDK.

    Reads configuration from environment variables:
      - MINIO_URL (default: http://minio:9000)
      - MINIO_ACCESS_KEY (default: workspot)
      - MINIO_SECRET_KEY (default: changeme123)
      - MINIO_BUCKET (default: workspot-media)
    """

    def __init__(
        self,
        url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
    ) -> None:
        if Minio is None:
            raise RuntimeError("minio package is not installed")

        self.url = url or os.environ.get("MINIO_URL", "http://minio:9000")
        self.access_key = access_key or os.environ.get("MINIO_ACCESS_KEY", "workspot")
        self.secret_key = secret_key or os.environ.get("MINIO_SECRET_KEY", "changeme123")
        self.bucket = bucket or os.environ.get("MINIO_BUCKET", DEFAULT_BUCKET)

        endpoint, secure = _parse_endpoint(self.url)
        self._client = Minio(
            endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=secure,
        )

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self.bucket):
            self._client.make_bucket(self.bucket)

    def upload_photo(self, file_bytes: bytes, filename: str, space_id: int | str) -> str:
        """Upload bytes to MinIO and return a public/presigned URL."""
        self.ensure_bucket()
        object_name = f"spaces/{space_id}/{uuid.uuid4().hex}_{filename}"
        self._client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type="application/octet-stream",
        )
        return self.get_photo_url(object_name)

    def get_photo_url(self, object_name: str) -> str:
        return self._client.presigned_get_object(
            self.bucket, object_name, expires=timedelta(hours=1)
        )

    def delete_photo(self, object_name: str) -> None:
        self._client.remove_object(self.bucket, object_name)
