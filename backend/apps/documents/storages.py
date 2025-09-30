"""Вспомогательные классы для работы с хранилищем документов."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class DocumentStorageError(RuntimeError):
    """Ошибка при работе с хранилищем документов."""


@dataclass(slots=True)
class PresignedUpload:
    url: str
    method: str
    fields: Dict[str, Any]
    headers: Dict[str, Any]


@dataclass(slots=True)
class PresignedDownload:
    url: str
    method: str
    headers: Dict[str, Any]


class AbstractDocumentStorage:
    """Минимальный интерфейс хранилища документов."""

    def generate_upload(
        self,
        *,
        key: str,
        content_type: str,
        max_size: int,
    ) -> PresignedUpload:
        raise NotImplementedError

    def generate_download(self, *, key: str, expires_in: Optional[int] = None) -> PresignedDownload:
        raise NotImplementedError

    def delete_object(self, *, key: str) -> None:
        raise NotImplementedError


class S3DocumentStorage(AbstractDocumentStorage):
    """Простейшая реализация presigned-подписей для S3/MinIO."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        session_token: Optional[str] = None,
        upload_expiration: int = 900,
        download_expiration: int = 900,
        signature_version: Optional[str] = None,
        addressing_style: Optional[str] = None,
    ) -> None:
        if not bucket:
            raise DocumentStorageError("Не указан bucket для документохранилища")
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - зависит от окружения
            raise DocumentStorageError(
                "Требуется установить зависимость 'boto3' для работы с хранилищем"
            ) from exc

        session = boto3.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region_name,
        )
        self._bucket = bucket
        config_kwargs: Dict[str, Any] = {}
        if signature_version or addressing_style:
            s3_options: Dict[str, Any] = {}
            if addressing_style:
                s3_options["addressing_style"] = addressing_style
            config_kwargs["config"] = Config(
                signature_version=signature_version,
                s3=s3_options or None,
            )
        self._client = session.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            **config_kwargs,
        )
        self._upload_expiration = upload_expiration
        self._download_expiration = download_expiration

    def generate_upload(
        self,
        *,
        key: str,
        content_type: str,
        max_size: int,
    ) -> PresignedUpload:
        fields = {"Content-Type": content_type}
        conditions = [
            {"bucket": self._bucket},
            ["eq", "$Content-Type", content_type],
            ["content-length-range", 1, max_size],
        ]
        response = self._client.generate_presigned_post(
            Bucket=self._bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=self._upload_expiration,
        )
        headers: Dict[str, Any] = {}
        return PresignedUpload(
            url=response["url"],
            method="POST",
            fields=response.get("fields", {}),
            headers=headers,
        )

    def generate_download(self, *, key: str, expires_in: Optional[int] = None) -> PresignedDownload:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in or self._download_expiration,
        )
        return PresignedDownload(url=url, method="GET", headers={})

    def delete_object(self, *, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


__all__ = [
    "AbstractDocumentStorage",
    "DocumentStorageError",
    "PresignedDownload",
    "PresignedUpload",
    "S3DocumentStorage",
]
