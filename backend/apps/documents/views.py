"""API-эндпоинты управления документами."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable

from applications.models import Application
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
)

from .models import Document, DocumentVersion
from .serializers import (
    CompleteUploadSerializer,
    DocumentListResponseSerializer,
    DocumentVersionSerializer,
    UploadRequestSerializer,
    UploadResponseSerializer,
)
from .services import (
    UploadBundle,
    archive_document,
    build_download,
    list_versions,
    request_upload,
)
from .services import (
    complete_upload as mark_upload_complete,
)
from .storages import DocumentStorageError


def _user_can_access(request: HttpRequest, application: Application) -> bool:
    """Проверка доступа к заявке (копия логики из модуля заявок)."""

    if request.user.is_authenticated:
        if request.user.is_staff or request.user == application.user:
            return True
    token = request.COOKIES.get("session_token")
    if token and token == str(application.public_id):
        return True
    return False


def _serialize_validation_error(exc: ValidationError) -> Dict[str, Any]:
    if hasattr(exc, "message_dict"):
        return exc.message_dict  # type: ignore[return-value]
    if hasattr(exc, "messages"):
        return {"detail": list(exc.messages)}  # type: ignore[arg-type]
    return {"detail": str(exc)}


def _prepare_upload_response(bundle: UploadBundle) -> Dict[str, Any]:
    upload = {
        "url": bundle.upload.url,
        "method": bundle.upload.method,
        "fields": {key: str(value) for key, value in bundle.upload.fields.items()},
        "headers": {key: str(value) for key, value in bundle.upload.headers.items()},
    }
    return {
        "document_id": bundle.document.public_id,
        "version_id": bundle.version.public_id,
        "upload": upload,
    }


def _latest_versions(versions: Iterable[DocumentVersion]) -> list[DocumentVersion]:
    seen: set[int] = set()
    latest: list[DocumentVersion] = []
    for version in versions:
        if version.document_id in seen:
            continue
        seen.add(version.document_id)
        latest.append(version)
    return latest


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def create_upload(request) -> Response:
    serializer = UploadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    application = serializer.validated_data["application"]
    if not _user_can_access(request, application):
        return Response(status=HTTP_403_FORBIDDEN)
    requirement = serializer.validated_data.get("requirement")
    document = serializer.validated_data.get("document")
    try:
        bundle = request_upload(
            application=application,
            requirement=requirement,
            document=document,
            filename=serializer.validated_data["filename"],
            content_type=serializer.validated_data["content_type"],
            size=serializer.validated_data["size"],
            user=request.user,
        )
    except ValidationError as exc:
        return Response(_serialize_validation_error(exc), status=HTTP_400_BAD_REQUEST)
    except DocumentStorageError as exc:  # pragma: no cover - зависит от инфраструктуры
        return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)
    payload = _prepare_upload_response(bundle)
    response_serializer = UploadResponseSerializer(payload)
    return Response(response_serializer.data, status=HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def complete_upload(request, version_id: uuid.UUID) -> Response:
    version = get_object_or_404(
        DocumentVersion.objects.select_related("document", "document__application", "document__requirement"),
        public_id=version_id,
    )
    application = version.document.application
    if not _user_can_access(request, application):
        return Response(status=HTTP_403_FORBIDDEN)
    serializer = CompleteUploadSerializer(data=request.data or {})
    serializer.is_valid(raise_exception=True)
    mark_upload_complete(
        version,
        checksum=serializer.validated_data.get("checksum"),
        etag=serializer.validated_data.get("etag"),
    )
    version.refresh_from_db()
    download = build_download(version)
    setattr(version, "download_url", download.url if download else None)
    response_serializer = DocumentVersionSerializer(version)
    return Response(response_serializer.data, status=HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def list_application_documents(request, public_id: uuid.UUID) -> Response:
    application = get_object_or_404(
        Application.objects.select_related("survey"),
        public_id=public_id,
    )
    if not _user_can_access(request, application):
        return Response(status=HTTP_403_FORBIDDEN)
    versions = list_versions(application)
    latest = _latest_versions(versions)
    for version in latest:
        download = build_download(version)
        setattr(version, "download_url", download.url if download else None)
    response_serializer = DocumentListResponseSerializer({"documents": latest})
    return Response(response_serializer.data, status=HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.AllowAny])
def delete_document(request, document_id: uuid.UUID) -> Response:
    document = get_object_or_404(
        Document.objects.select_related("application"),
        public_id=document_id,
        is_archived=False,
    )
    if not _user_can_access(request, document.application):
        return Response(status=HTTP_403_FORBIDDEN)
    archive_document(document)
    return Response(status=HTTP_204_NO_CONTENT)


__all__ = [
    "complete_upload",
    "create_upload",
    "delete_document",
    "list_application_documents",
]
