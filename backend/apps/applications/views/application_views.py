"""Публичные API-эндпоинты для работы с заявками."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from ..models import Answer, Application, Question, Step, Survey
from ..serializers import (
    AnswerPatchItemSerializer,
    ApplicationCommentInSerializer,
    ApplicationCommentOutSerializer,
    DataConsentSerializer,
    DraftOutSerializer,
    DraftPatchSerializer,
    NextOutSerializer,
    SubmitResponseSerializer,
    CreateSessionRequestSerializer,
)
from ..services.application_service import (
    add_comment,
    audit,
    change_status,
    record_consent,
)
from ..services.form_runtime import (
    build_answer_dict,
    next_step,
    validate_documents,
    validate_required,
    visible_questions,
)

ALLOWED_APPLICANT_TYPES = ('self', 'parent', 'guardian', 'relative')


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """Заглушка для совместимости, доступ всем к GET."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


def _user_can_access(request, application: Application) -> bool:
    """Проверяет, может ли пользователь или сессия управлять заявкой."""

    if request.user.is_authenticated:
        if request.user.is_staff or request.user == application.user:
            return True
    token = request.COOKIES.get("session_token")
    if token and token == str(application.public_id):
        return True
    return False


def _serialize_step(step: Optional[Step], answers: Dict[str, Any]) -> Optional[Step]:
    if step is None:
        return None
    questions = visible_questions(step, answers)
    step._prefetched_objects_cache = {"questions": questions}
    return step


def _serialize_application(application: Application, answers: Dict[str, Any]) -> Dict[str, Any]:
    step = _serialize_step(application.current_step, answers)
    return {
        "public_id": application.public_id,
        "current_stage": application.current_stage,
        "current_step": step,
        "answers": answers,
    }


def _get_application_queryset():
    return Application.objects.select_related("survey", "current_step", "user").prefetch_related(
        "answers__question",
    )


def _get_application(public_id: uuid.UUID) -> Application:
    return get_object_or_404(_get_application_queryset(), public_id=public_id)


def _apply_answer_patch(
    application: Application,
    items: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    if not items:
        return []
    serializer = AnswerPatchItemSerializer(data=items, many=True)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data
    codes = {entry["question_code"] for entry in validated}
    questions = {
        question.code: question
        for question in Question.objects.filter(step__survey=application.survey, code__in=codes)
    }
    errors: List[Dict[str, str]] = []
    for entry in validated:
        question = questions.get(entry["question_code"])
        if question is None:
            errors.append(
                {
                    "field": entry["question_code"],
                    "message": "Неизвестный код вопроса.",
                }
            )
            continue
        Answer.objects.update_or_create(
            application=application,
            question=question,
            defaults={"value": entry["value"]},
        )
    return errors


def _set_current_step(application: Application, step_code: Optional[str]) -> None:
    if not step_code:
        return
    step = get_object_or_404(Step, survey=application.survey, code=step_code)
    application.current_step = step
    application.current_stage = step.order
    application.save(update_fields=["current_step", "current_stage", "updated_at"])


def _update_stage_from_step(application: Application) -> None:
    if application.current_step:
        application.current_stage = application.current_step.order
    else:
        application.current_stage = 0
    application.save(update_fields=["current_step", "current_stage", "updated_at"])


def _validation_error(errors: List[Dict[str, str]]):
    return Response(
        {
            "detail": "Validation error",
            "errors": errors,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@extend_schema(
    request=CreateSessionRequestSerializer,
    responses={201: DraftOutSerializer},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def create_session(request, survey_code: str) -> Response:
    survey = get_object_or_404(Survey.objects.filter(is_active=True), code=survey_code)
    current_step = survey.steps.order_by("order", "id").first()
    applicant_type = (request.data or {}).get("applicant_type") if isinstance(request.data, dict) else None
    if applicant_type and applicant_type not in ALLOWED_APPLICANT_TYPES:
        return _validation_error([{"field": "applicant_type", "message": "Недопустимое значение"}])
    application = Application.objects.create(
        survey=survey,
        user=request.user if request.user.is_authenticated else None,
        current_step=current_step,
        current_stage=current_step.order if current_step else 0,
        applicant_type=applicant_type or "",
    )
    answers: Dict[str, Any] = {}
    payload = _serialize_application(application, answers)
    serializer = DraftOutSerializer(payload)
    response = Response(serializer.data, status=status.HTTP_201_CREATED)
    response.set_cookie(
        "session_token",
        str(application.public_id),
        httponly=True,
        samesite="Lax",
    )
    audit(
        action="create",
        table_name="applications",
        record_id=application.public_id,
        user=request.user if request.user.is_authenticated else None,
        request=request,
    )
    return response


@extend_schema(responses=DraftOutSerializer)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_draft(request, public_id: uuid.UUID) -> Response:
    application = _get_application(public_id)
    if not _user_can_access(request, application):
        return Response(status=status.HTTP_403_FORBIDDEN)
    answers = build_answer_dict(application)
    payload = _serialize_application(application, answers)
    serializer = DraftOutSerializer(payload)
    return Response(serializer.data)


@extend_schema(request=DraftPatchSerializer, responses=DraftOutSerializer)
@api_view(["PATCH"])
@permission_classes([permissions.AllowAny])
def patch_draft(request, public_id: uuid.UUID) -> Response:
    application = _get_application(public_id)
    if not _user_can_access(request, application):
        return Response(status=status.HTTP_403_FORBIDDEN)
    items = request.data.get("answers", []) if isinstance(request.data, dict) else []
    errors = _apply_answer_patch(application, items)
    if errors:
        return _validation_error(errors)
    step_code = request.data.get("step_code") if isinstance(request.data, dict) else None
    if step_code:
        _set_current_step(application, step_code)
    answers = build_answer_dict(application)
    payload = _serialize_application(application, answers)
    serializer = DraftOutSerializer(payload)
    return Response(serializer.data)


@extend_schema(request=DraftPatchSerializer, responses=NextOutSerializer)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def post_next(request, public_id: uuid.UUID) -> Response:
    application = _get_application(public_id)
    if not _user_can_access(request, application):
        return Response(status=status.HTTP_403_FORBIDDEN)
    if isinstance(request.data, dict) and request.data.get("answers"):
        errors = _apply_answer_patch(application, request.data["answers"])
        if errors:
            return _validation_error(errors)
    answers = build_answer_dict(application)
    upcoming = next_step(application.survey, application.current_step, answers)
    application.current_step = upcoming
    _update_stage_from_step(application)
    payload = {
        "public_id": application.public_id,
        "current_stage": application.current_stage,
        "current_step": _serialize_step(upcoming, answers),
        "answers": answers,
    }
    serializer = NextOutSerializer(payload)
    return Response(serializer.data)


@extend_schema(request=DraftPatchSerializer, responses=SubmitResponseSerializer)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def post_submit(request, public_id: uuid.UUID) -> Response:
    application = _get_application(public_id)
    if not _user_can_access(request, application):
        return Response(status=status.HTTP_403_FORBIDDEN)
    if isinstance(request.data, dict) and request.data.get("answers"):
        errors = _apply_answer_patch(application, request.data["answers"])
        if errors:
            return _validation_error(errors)
    answers = build_answer_dict(application)
    step_errors: List[Dict[str, str]] = []
    if application.current_step:
        step_errors = validate_required(application.current_step, answers)
    document_errors = validate_documents(application.survey, answers)
    errors: List[Dict[str, str]] = []
    errors.extend(step_errors)
    errors.extend(document_errors)
    if errors:
        return _validation_error(errors)
    change_status(
        application,
        Application.Status.SUBMITTED,
        request.user if request.user.is_authenticated else None,
        request=request,
    )
    audit(
        action="submit",
        table_name="applications",
        record_id=application.public_id,
        user=request.user if request.user.is_authenticated else None,
        request=request,
    )
    return Response(
        {
            "public_id": str(application.public_id),
            "status": application.status,
        }
    )


@extend_schema(
    request=DataConsentSerializer,
    responses={201: DataConsentSerializer},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def post_consent(request, public_id: uuid.UUID) -> Response:
    application = _get_application(public_id)
    if not _user_can_access(request, application):
        return Response(status=status.HTTP_403_FORBIDDEN)
    serializer = DataConsentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = request.user if request.user.is_authenticated else application.user
    if not user:
        return Response(status=status.HTTP_403_FORBIDDEN)
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip_address = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    consent = record_consent(
        user=user,
        application=application,
        consent_type=serializer.validated_data.get("consent_type", "pdn_152"),
        is_given=serializer.validated_data.get("is_given", True),
        ip_address=ip_address,
    )
    audit(
        action="consent",
        table_name="consents",
        record_id=application.public_id,
        user=user,
        request=request,
    )
    return Response(DataConsentSerializer(consent).data, status=status.HTTP_201_CREATED)


class CommentPagination(PageNumberPagination):
    """Пагинация для комментариев."""

    page_size = 20
    max_page_size = 100


@extend_schema_view(
    get=extend_schema(responses=ApplicationCommentOutSerializer(many=True)),
    post=extend_schema(
        request=ApplicationCommentInSerializer,
        responses={201: ApplicationCommentOutSerializer},
    ),
)
@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
def application_comments(request, public_id: uuid.UUID) -> Response:
    application = _get_application(public_id)
    if not _user_can_access(request, application):
        return Response(status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        queryset = application.comments.select_related("user").order_by("-created_at")
        paginator = CommentPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ApplicationCommentOutSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = ApplicationCommentInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comment = add_comment(
        application,
        request.user if request.user.is_authenticated else None,
        serializer.validated_data["comment"],
        is_urgent=serializer.validated_data.get("is_urgent", False),
        request=request,
    )
    output = ApplicationCommentOutSerializer(comment)
    return Response(output.data, status=status.HTTP_201_CREATED)
