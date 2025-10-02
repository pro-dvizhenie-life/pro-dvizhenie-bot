"""Проверки ограничений на загрузку документов."""

from __future__ import annotations

from applications.models import Application, DocumentRequirement, Survey
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from documents.models import Document
from documents.services import request_upload


class RequestUploadValidationTests(TestCase):
    """Тесты валидации запросов на загрузку документов."""

    def setUp(self) -> None:
        self.survey = Survey.objects.create(code="test-survey", title="Test Survey")
        self.requirement = DocumentRequirement.objects.create(
            survey=self.survey,
            code="passport",
            label="Passport",
        )
        self.application = Application.objects.create(survey=self.survey)

    def test_rejects_size_above_limit(self) -> None:
        with self.assertRaises(ValidationError) as exc:
            request_upload(
                application=self.application,
                requirement=self.requirement,
                document=None,
                filename="oversized.pdf",
                content_type="application/pdf",
                size=settings.DOCUMENTS_MAX_FILE_SIZE + 1,
            )
        self.assertIn("size", exc.exception.message_dict)

    def test_rejects_disallowed_mime_type(self) -> None:
        with self.assertRaises(ValidationError) as exc:
            request_upload(
                application=self.application,
                requirement=self.requirement,
                document=None,
                filename="document.pdf",
                content_type="application/octet-stream",
                size=1024,
            )
        self.assertIn("content_type", exc.exception.message_dict)

    def test_rejects_disallowed_extension(self) -> None:
        with self.assertRaises(ValidationError) as exc:
            request_upload(
                application=self.application,
                requirement=self.requirement,
                document=None,
                filename="malicious.exe",
                content_type="application/pdf",
                size=1024,
            )
        self.assertIn("filename", exc.exception.message_dict)

    @override_settings(DOCUMENTS_MAX_DOCUMENTS_PER_APPLICATION=1)
    def test_rejects_when_documents_limit_reached(self) -> None:
        Document.objects.create(
            application=self.application,
            requirement=self.requirement,
            code="initial",
            title="Initial",
        )

        with self.assertRaises(ValidationError) as exc:
            request_upload(
                application=self.application,
                requirement=self.requirement,
                document=None,
                filename="new.pdf",
                content_type="application/pdf",
                size=1024,
            )
        self.assertIn("documents", exc.exception.message_dict)
