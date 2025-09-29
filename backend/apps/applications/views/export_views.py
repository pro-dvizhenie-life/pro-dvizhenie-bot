"""Экспорт заявок в CSV для административных задач."""

from __future__ import annotations

import csv
from typing import Iterable, List

from django.http import StreamingHttpResponse
from django.utils.encoding import smart_str
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes

from ..models import Question
from ..services.form_runtime import build_answer_dict
from .admin_views import IsStaffOrAdmin
from .application_views import _get_application_queryset


class Echo:
    """Фейловый буфер для StreamingHttpResponse."""

    def write(self, value):  # type: ignore[override]
        return value


def _collect_question_codes(survey_ids: Iterable[int]) -> List[str]:
    survey_ids = list(survey_ids)
    if not survey_ids:
        return []
    questions = Question.objects.filter(step__survey_id__in=survey_ids).values_list("code", flat=True)
    return sorted(set(questions))


@extend_schema(responses={200: OpenApiResponse(description="CSV export of applications")})
@api_view(["GET"])
@permission_classes([IsStaffOrAdmin])
def export_csv(request) -> StreamingHttpResponse:
    queryset = _get_application_queryset()
    status_param = request.query_params.get("status")
    if status_param:
        queryset = queryset.filter(status=status_param)
    date_from = request.query_params.get("date_from")
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    date_to = request.query_params.get("date_to")
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    queryset = queryset.order_by("created_at")

    survey_ids = queryset.values_list("survey_id", flat=True).distinct()
    question_codes = _collect_question_codes(survey_ids)
    header = [
        "public_id",
        "created_at",
        "status",
        "applicant_type",
        *question_codes,
    ]

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)

    def rows():
        yield writer.write(header)
        for application in queryset.iterator():
            answers = build_answer_dict(application)
            row = [
                str(application.public_id),
                application.created_at.isoformat(),
                application.status,
                application.applicant_type,
            ]
            row.extend(smart_str(answers.get(code, "")) for code in question_codes)
            yield writer.write(row)

    response = StreamingHttpResponse(rows(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="applications_export.csv"'
    return response
