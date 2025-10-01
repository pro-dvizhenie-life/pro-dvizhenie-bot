"""Тесты для сервисов экспорта заявок."""

from __future__ import annotations

import importlib.util
from io import BytesIO
from unittest import skipIf

from django.test import TestCase

from ..models import Answer, Application, Question, Step, Survey
from ..services.exporting import (
    build_export_dataset,
    export_applications_csv,
    export_applications_xlsx,
)

OPENPYXL_AVAILABLE = importlib.util.find_spec("openpyxl") is not None


class ApplicationExportTests(TestCase):
    """Проверки формирования выгрузок по заявкам."""

    def setUp(self):
        self.survey = Survey.objects.create(code="main", title="Main", version="1", is_active=True)
        self.step = Step.objects.create(survey=self.survey, code="step1", title="Step 1", order=1)
        self.question = Question.objects.create(
            step=self.step,
            code="q_fullname",
            label="ФИО",
            type="text",
            required=True,
        )
        self.application = Application.objects.create(survey=self.survey, status=Application.Status.SUBMITTED)
        Answer.objects.create(application=self.application, question=self.question, value="Иван Иванов")

    def test_build_export_dataset_contains_answers(self):
        queryset = Application.objects.filter(pk=self.application.pk).select_related("survey")
        dataset = build_export_dataset(queryset)
        self.assertIn("q_fullname", dataset.headers)
        rows = list(dataset.rows)
        self.assertEqual(len(rows), 1)
        self.assertIn("Иван Иванов", rows[0])

    def test_build_export_dataset_handles_prefetched_queryset(self):
        queryset = (
            Application.objects.filter(pk=self.application.pk)
            .select_related("survey")
            .prefetch_related("answers")
        )
        dataset = build_export_dataset(queryset)
        rows = list(dataset.rows)
        self.assertEqual(len(rows), 1)
        self.assertIn("Иван Иванов", rows[0])

    def test_export_applications_csv_returns_stream(self):
        queryset = Application.objects.filter(pk=self.application.pk)
        response = export_applications_csv(queryset, filename="apps_test")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="apps_test.csv"')
        content = b"".join(response.streaming_content)
        self.assertIn(b"q_fullname", content)
        self.assertIn("Иван Иванов".encode("utf-8"), content)

    @skipIf(not OPENPYXL_AVAILABLE, "openpyxl не установлен")
    def test_export_applications_xlsx_contains_data(self):
        queryset = Application.objects.filter(pk=self.application.pk)
        response = export_applications_xlsx(queryset, filename="apps_test")
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        with BytesIO(response.content) as buffer:
            from openpyxl import load_workbook

            workbook = load_workbook(buffer)
            sheet = workbook.active
            headers = [cell.value for cell in sheet[1]]
            self.assertIn("q_fullname", headers)
            values = [cell.value for cell in sheet[2]]
            self.assertIn("Иван Иванов", values)
