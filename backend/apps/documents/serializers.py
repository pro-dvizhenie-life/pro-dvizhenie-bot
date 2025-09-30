"""Сериализаторы API для управления документами."""

from __future__ import annotations

from typing import Any, Dict, Optional

from applications.models import Application, DocumentRequirement
from django.utils import timezone
from rest_framework import serializers

from .models import Document, DocumentVersion


class UploadRequestSerializer(serializers.Serializer):
    """Параметры запроса на получение presigned-данных."""

    application_id = serializers.UUIDField()
    requirement_code = serializers.SlugField(required=False, allow_blank=True)
    document_id = serializers.UUIDField(required=False)
    filename = serializers.CharField()
    content_type = serializers.CharField()
    size = serializers.IntegerField(min_value=1)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        application_id = attrs.get("application_id")
        requirement_code = attrs.get("requirement_code")
        document_id = attrs.get("document_id")
        if not requirement_code and not document_id:
            raise serializers.ValidationError(
                "Нужно указать requirement_code или document_id для загрузки."
            )
        if requirement_code and document_id:
            raise serializers.ValidationError(
                "Укажите либо requirement_code, либо document_id, но не оба одновременно."
            )
        try:
            application = Application.objects.get(public_id=application_id)
        except Application.DoesNotExist as exc:  # pragma: no cover - валидация
            raise serializers.ValidationError({"application_id": "Заявка не найдена."}) from exc
        attrs["application"] = application
        if requirement_code:
            try:
                requirement = application.survey.doc_requirements.get(code=requirement_code)
            except DocumentRequirement.DoesNotExist as exc:  # pragma: no cover - валидация
                raise serializers.ValidationError(
                    {"requirement_code": "Требование с таким кодом не найдено для анкеты."}
                ) from exc
            attrs["requirement"] = requirement
        if document_id:
            try:
                document = application.documents.get(public_id=document_id, is_archived=False)
            except Document.DoesNotExist as exc:  # pragma: no cover - валидация
                raise serializers.ValidationError(
                    {"document_id": "Документ не найден или неактивен."}
                ) from exc
            attrs["document"] = document
            attrs["requirement"] = document.requirement
        return attrs


class PresignedUploadSerializer(serializers.Serializer):
    url = serializers.URLField()
    method = serializers.CharField()
    fields = serializers.DictField(child=serializers.CharField(), required=False)
    headers = serializers.DictField(child=serializers.CharField(), required=False)


class UploadResponseSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    version_id = serializers.UUIDField()
    upload = PresignedUploadSerializer()


class CompleteUploadSerializer(serializers.Serializer):
    etag = serializers.CharField(required=False, allow_blank=True)
    checksum = serializers.CharField(required=False, allow_blank=True)


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Представление версии документа для ответа API."""

    document_id = serializers.UUIDField(source="document.public_id", read_only=True)
    version_id = serializers.UUIDField(source="public_id", read_only=True)
    requirement_code = serializers.SerializerMethodField()
    requirement_label = serializers.SerializerMethodField()
    download_url = serializers.CharField(read_only=True, allow_null=True, required=False)
    uploaded_at = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = (
            "document_id",
            "version_id",
            "version",
            "status",
            "antivirus_status",
            "requirement_code",
            "requirement_label",
            "original_name",
            "mime_type",
            "size",
            "uploaded_at",
            "download_url",
        )

    def get_requirement_code(self, obj: DocumentVersion) -> Optional[str]:
        if obj.document.requirement:
            return obj.document.requirement.code
        return obj.document.code or None

    def get_requirement_label(self, obj: DocumentVersion) -> Optional[str]:
        if obj.document.requirement:
            return obj.document.requirement.label
        return obj.document.title or None

    def get_uploaded_at(self, obj: DocumentVersion) -> Optional[str]:
        if obj.uploaded_at:
            return timezone.localtime(obj.uploaded_at).isoformat()
        return None


class DocumentListResponseSerializer(serializers.Serializer):
    documents = DocumentVersionSerializer(many=True)


__all__ = [
    "CompleteUploadSerializer",
    "DocumentListResponseSerializer",
    "DocumentVersionSerializer",
    "PresignedUploadSerializer",
    "UploadRequestSerializer",
    "UploadResponseSerializer",
]
