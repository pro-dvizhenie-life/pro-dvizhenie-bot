"""Экспорт заявок в CSV для административных задач."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes

from ..permissions import IsEmployeeOrAdmin
from ..services.exporting import export_applications_csv
from .application_views import _get_application_queryset


@extend_schema(responses={200: OpenApiResponse(description="CSV export of applications")})
@api_view(["GET"])
@permission_classes([IsEmployeeOrAdmin])
def export_csv(request):
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

    filename = "applications_export"
    return export_applications_csv(queryset, filename=filename)
