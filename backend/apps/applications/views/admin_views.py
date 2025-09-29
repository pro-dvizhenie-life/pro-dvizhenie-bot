"""Административные API для работы с заявками."""

from __future__ import annotations

from typing import Any, Dict, List

from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..models import ApplicationComment, ApplicationStatusHistory
from ..serializers import (
    ApplicationCommentOutSerializer,
    ApplicationDetailSerializer,
    ApplicationShortSerializer,
    ApplicationStatusHistorySerializer,
    ApplicationStatusPatchSerializer,
    StatusResponseSerializer,
    TimelineResponseSerializer,
)
from ..services.application_service import audit, change_status
from .application_views import _get_application_queryset


class IsStaffOrAdmin(permissions.BasePermission):
    """Доступ только сотрудникам или администраторам."""

    allowed_roles = {"employee", "admin"}

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        role = getattr(user, "role", None)
        return role in self.allowed_roles


class AdminPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


def _admin_queryset():
    return _get_application_queryset().prefetch_related(
        "answers__question",
    )


@extend_schema(responses=ApplicationShortSerializer(many=True))
@api_view(["GET"])
@permission_classes([IsStaffOrAdmin])
def application_list(request) -> Response:
    queryset = _admin_queryset()
    status_param = request.query_params.get("status")
    if status_param:
        queryset = queryset.filter(status=status_param)
    survey_param = request.query_params.get("survey")
    if survey_param:
        queryset = queryset.filter(survey__code=survey_param)
    search = request.query_params.get("q")
    if search:
        queryset = queryset.filter(
            Q(user__email__icontains=search)
            | Q(user__phone__icontains=search)
            | Q(answers__value__icontains=search)
            | Q(public_id__icontains=search)
        ).distinct()
    ordering = request.query_params.get("ordering") or "-created_at"
    queryset = queryset.order_by(ordering)
    paginator = AdminPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = ApplicationShortSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(responses=ApplicationDetailSerializer)
@api_view(["GET"])
@permission_classes([IsStaffOrAdmin])
def application_detail(request, public_id) -> Response:
    application = get_object_or_404(
        _admin_queryset().prefetch_related(
            Prefetch("comments", queryset=ApplicationComment.objects.select_related("user")),
            Prefetch("status_history", queryset=ApplicationStatusHistory.objects.select_related("changed_by")),
            "consents",
        ),
        public_id=public_id,
    )
    serializer = ApplicationDetailSerializer(application, context={"request": request})
    return Response(serializer.data)


@extend_schema(
    request=ApplicationStatusPatchSerializer,
    responses=StatusResponseSerializer,
)
@api_view(["PATCH"])
@permission_classes([IsStaffOrAdmin])
def application_status_patch(request, public_id) -> Response:
    application = get_object_or_404(_admin_queryset(), public_id=public_id)
    serializer = ApplicationStatusPatchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    new_status = serializer.validated_data["new_status"]
    try:
        change_status(application, new_status, request.user, request=request)
    except ValidationError as exc:
        return Response(
            {"detail": "Validation error", "errors": [{"field": "status", "message": str(exc)}]},
            status=400,
        )
    audit(
        action="status_change",
        table_name="applications",
        record_id=application.public_id,
        user=request.user,
        request=request,
    )
    return Response({"status": application.status})


@extend_schema(responses=TimelineResponseSerializer)
@api_view(["GET"])
@permission_classes([IsStaffOrAdmin])
def application_timeline(request, public_id) -> Response:
    application = get_object_or_404(
        _admin_queryset().prefetch_related(
            Prefetch("comments", queryset=ApplicationComment.objects.select_related("user")),
            Prefetch("status_history", queryset=ApplicationStatusHistory.objects.select_related("changed_by")),
        ),
        public_id=public_id,
    )
    timeline: List[Dict[str, Any]] = []
    for history in application.status_history.all():
        timeline.append(
            {
                "type": "status",
                "data": ApplicationStatusHistorySerializer(history, context={"request": request}).data,
                "created_at": history.created_at,
            }
        )
    for comment in application.comments.all():
        timeline.append(
            {
                "type": "comment",
                "data": ApplicationCommentOutSerializer(comment, context={"request": request}).data,
                "created_at": comment.created_at,
            }
        )
    timeline.sort(key=lambda item: item["created_at"])
    return Response({"timeline": timeline})
