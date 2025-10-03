"""Публичные API-эндпоинты для работы с заявками."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from config.constants import (
    ALLOWED_APPLICANT_TYPES,
    COOKIE_SESSION_TOKEN,
    DEFAULT_CONSENT_TYPE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
)

from ..models import Answer, Application, Question, Step, Survey
from ..permissions import IsEmployeeOrAdmin, IsOwnerOrEmployee
from ..serializers import (
    AnswerPatchItemSerializer,
    ApplicationCommentInSerializer,
    ApplicationCommentOutSerializer,
    CreateSessionRequestSerializer,
    DataConsentSerializer,
    DraftOutSerializer,
    DraftPatchSerializer,
    NextOutSerializer,
    SubmitResponseSerializer,
)
from ..services.application_service import (
    CONSENT_DECLINED_MESSAGE,
    add_comment,
    audit,
    change_status,
    ensure_applicant_account,
    handle_consent_decline,
    record_consent,
)
from ..services.form_runtime import (
    build_answer_dict,
    next_step,
    validate_answer_value,
    validate_documents,
    validate_required,
    visible_questions,
)


def _serialize_step(step: Optional[Step], answers: Dict[str, Any]) -> Optional[Step]:
    """Формирует объект шага с подсчитанными видимыми вопросами."""

    if step is None:
        return None
    questions = [
        question
        for question in visible_questions(step, answers)
        if not (question.payload or {}).get("hidden")
    ]
    step._prefetched_objects_cache = {"questions": questions}
    return step


def _serialize_application(application: Application, answers: Dict[str, Any]) -> Dict[str, Any]:
    """Готовит словарь с данными заявки и текущего шага."""

    step = _serialize_step(application.current_step, answers)
    return {
        "public_id": application.public_id,
        "current_stage": application.current_stage,
        "current_step": step,
        "answers": answers,
        "restart_available": step is None,
    }


def _ensure_default_answers(application: Application) -> None:
    for code in AUTO_FILL_DATE_CODES:
        if application.answers.filter(question__code=code).exists():
            continue
        question = Question.objects.filter(step__survey=application.survey, code=code).first()
        if not question:
            continue
        Answer.objects.update_or_create(
            application=application,
            question=question,
            defaults={"value": date.today().isoformat()},
        )


def _get_application_queryset():
    """Возвращает базовый queryset заявок с необходимыми связями."""

    return Application.objects.select_related("survey", "current_step", "user").prefetch_related(
        "answers__question",
    )


def _get_application(public_id: uuid.UUID) -> Application:
    """Ищет заявку по публичному идентификатору или отдаёт 404."""

    return get_object_or_404(_get_application_queryset(), public_id=public_id)


def _get_application_by_token_or_session(public_id: uuid.UUID, request: HttpRequest) -> Optional[Application]:
    """Пытается получить Application по public_id и session_token из куки."""
    session_token = request.COOKIES.get(COOKIE_SESSION_TOKEN) # Получаем токен из куки
    if not session_token:
        return None # Если токен не найден, возвращаем None

    # Пробуем найти Application по public_id и session_token
    # Предполагаем, что session_token хранится в поле public_id, как в create_session
    # ВАЖНО: В текущей модели Application НЕТ отдельного поля session_token.
    # Мы используем тот факт, что в create_session токен устанавливается как public_id.
    # Поэтому нам нужно найти Application с public_id, который совпадает с переданным public_id,
    # и убедиться, что session_token (из куки) совпадает с public_id (из модели).
    try:
        application = _get_application_queryset().get(public_id=public_id)
        # В текущей модели session_token не является отдельным полем, он совпадает с public_id
        if str(application.public_id) == session_token:
            return application
        else:
            return None # Токен из куки не совпадает с public_id модели
    except Application.DoesNotExist:
        return None


def _apply_answer_patch(
    application: Application,
    items: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Применяет патч с ответами и возвращает ошибки валидации."""

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
    to_update: List[tuple[Question, Any]] = []
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
        normalized, validation_error = validate_answer_value(question, entry["value"])
        if validation_error:
            errors.append(
                {
                    "field": question.code,
                    "message": validation_error,
                }
            )
            continue
        if question.code == CONSENT_QUESTION_CODE and normalized is False:
            handle_consent_decline(application)
            raise ConsentDeclinedError(CONSENT_DECLINED_MESSAGE)
        to_update.append((question, normalized))
    if errors:
        return errors
    for question, value in to_update:
        Answer.objects.update_or_create(
            application=application,
            question=question,
            defaults={"value": value},
        )
    return []


def _set_current_step(application: Application, step_code: Optional[str]) -> None:
    """Обновляет текущий шаг заявки по коду шага."""

    if not step_code:
        return
    step = get_object_or_404(Step, survey=application.survey, code=step_code)
    application.current_step = step
    application.current_stage = step.order
    application.save(update_fields=["current_step", "current_stage", "updated_at"])


def _update_stage_from_step(application: Application) -> None:
    """Синхронизирует текущую стадию заявки с выбранным шагом."""

    if application.current_step:
        application.current_stage = application.current_step.order
    else:
        application.current_stage = 0
    application.save(update_fields=["current_step", "current_stage", "updated_at"])


def _validation_error(errors: List[Dict[str, str]]):
    """Формирует ответ API с ошибками валидации."""

    return Response(
        {
            "detail": "Validation error",
            "errors": errors,
        },
        status=HTTP_400_BAD_REQUEST,
    )


@extend_schema(
    request=CreateSessionRequestSerializer,
    responses={201: DraftOutSerializer},
)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def create_session(request, survey_code: str) -> Response:
    """Создаёт черновик заявки и выдаёт cookie для продолжения."""

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
    _ensure_default_answers(application)
    answers = build_answer_dict(application)
    payload = _serialize_application(application, answers)
    serializer = DraftOutSerializer(payload)
    response = Response(serializer.data, status=HTTP_201_CREATED)
    response.set_cookie(
        COOKIE_SESSION_TOKEN,
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
    """Возвращает заполненный черновик заявки по публичному ID."""

    application = None
    if request.user.is_authenticated:
        # Логика для аутентифицированных пользователей
        application = _get_application(public_id)
        if not IsOwnerOrEmployee().has_object_permission(request, None, application):
            raise PermissionDenied()
    else:
        # Логика для анонимных пользователей - по сессионной куке
        application = _get_application_by_token_or_session(public_id, request)
        if not application:
            # Если не найдена по куке или кука отсутствует/некорректна
            raise PermissionDenied()

    # Теперь application получена, сериализуем как обычно
    answers = build_answer_dict(application)
    payload = _serialize_application(application, answers)
    serializer = DraftOutSerializer(payload)
    return Response(serializer.data)


@extend_schema(request=DraftPatchSerializer, responses=DraftOutSerializer)
@api_view(["PATCH"])
@permission_classes([permissions.AllowAny])
def patch_draft(request, public_id: uuid.UUID) -> Response:
    """Обновляет ответы черновика и при необходимости меняет шаг."""

    application = None
    if request.user.is_authenticated:
        application = _get_application(public_id)
        if not IsOwnerOrEmployee().has_object_permission(request, None, application):
            raise PermissionDenied()
    else:
        application = _get_application_by_token_or_session(public_id, request)
        if not application:
            raise PermissionDenied()

    # Остальная логика как есть
    items = request.data.get("answers", []) if isinstance(request.data, dict) else []
    try:
        errors = _apply_answer_patch(application, items)
    except ConsentDeclinedError as exc:
        return Response(
            {"detail": exc.message, "consent_declined": True},
            status=HTTP_400_BAD_REQUEST,
        )
    if errors:
        return _validation_error(errors)
    step_code = request.data.get("step_code") if isinstance(request.data, dict) else None
    if step_code:
        _set_current_step(application, step_code)
    _ensure_default_answers(application)
    answers = build_answer_dict(application)
    ensure_applicant_account(application, answers, request=request)
    payload = _serialize_application(application, answers)
    serializer = DraftOutSerializer(payload)
    return Response(serializer.data)


@extend_schema(request=DraftPatchSerializer, responses=NextOutSerializer)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def post_next(request, public_id: uuid.UUID) -> Response:
    """Переходит к следующему шагу анкеты с сохранением ответов."""

    application = None
    if request.user.is_authenticated:
        application = _get_application(public_id)
        if not IsOwnerOrEmployee().has_object_permission(request, None, application):
            raise PermissionDenied()
    else:
        application = _get_application_by_token_or_session(public_id, request)
        if not application:
            raise PermissionDenied()

    # Остальная логика как есть
    if isinstance(request.data, dict) and request.data.get("answers"):
        try:
            errors = _apply_answer_patch(application, request.data["answers"])
        except ConsentDeclinedError as exc:
            return Response(
                {"detail": exc.message, "consent_declined": True},
                status=HTTP_400_BAD_REQUEST,
            )
        if errors:
            return _validation_error(errors)
    _ensure_default_answers(application)
    answers = build_answer_dict(application)
    ensure_applicant_account(application, answers, request=request)
    if application.current_step:
        required_errors = validate_required(application.current_step, answers)
        if required_errors:
            return _validation_error(required_errors)
    upcoming = next_step(application.survey, application.current_step, answers)
    application.current_step = upcoming
    _update_stage_from_step(application)
    restart_url = None
    if upcoming is None:
        restart_url = request.build_absolute_uri(
            reverse("applications:create_session", kwargs={"survey_code": application.survey.code})
        )
    payload = {
        "public_id": application.public_id,
        "current_stage": application.current_stage,
        "current_step": _serialize_step(upcoming, answers),
        "answers": answers,
        "restart_available": upcoming is None,
        "restart_url": restart_url,
    }
    serializer = NextOutSerializer(payload)
    return Response(serializer.data)


@extend_schema(request=DraftPatchSerializer, responses=SubmitResponseSerializer)
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def post_submit(request, public_id: uuid.UUID) -> Response:
    """Проверяет ответы и отправляет заявку на рассмотрение."""

    application = None
    if request.user.is_authenticated:
        application = _get_application(public_id)
        if not IsOwnerOrEmployee().has_object_permission(request, None, application):
            raise PermissionDenied()
    else:
        application = _get_application_by_token_or_session(public_id, request)
        if not application:
            raise PermissionDenied()

    # Остальная логика как есть
    if isinstance(request.data, dict) and request.data.get("answers"):
        try:
            errors = _apply_answer_patch(application, request.data["answers"])
        except ConsentDeclinedError as exc:
            return Response(
                {"detail": exc.message, "consent_declined": True},
                status=HTTP_400_BAD_REQUEST,
            )
        if errors:
            return _validation_error(errors)
    _ensure_default_answers(application)
    answers = build_answer_dict(application)
    ensure_applicant_account(application, answers, request=request)
    step_errors: List[Dict[str, str]] = []
    if application.current_step:
        step_errors = validate_required(application.current_step, answers)
    document_errors = validate_documents(application, answers)
    errors: List[Dict[str, str]] = []
    errors.extend(step_errors)
    errors.extend(document_errors)
    if errors:
        return _validation_error(errors)
    change_status(
        application,
        Application.Status.SUBMITTED,
        request.user, # или None, если анонимный
        request=request,
    )
    audit(
        action="submit",
        table_name="applications",
        record_id=application.public_id,
        user=request.user, # или None, если анонимный
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
    """Фиксирует согласие пользователя на обработку персональных данных."""

    application = None
    if request.user.is_authenticated:
        application = _get_application(public_id)
        if not IsOwnerOrEmployee().has_object_permission(request, None, application):
            raise PermissionDenied()
    else:
        application = _get_application_by_token_or_session(public_id, request)
        if not application:
            raise PermissionDenied()

    # Остальная логика как есть
    serializer = DataConsentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip_address = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    consent = record_consent(
        user=request.user, # или None, если анонимный
        application=application,
        consent_type=serializer.validated_data.get("consent_type", DEFAULT_CONSENT_TYPE),
        is_given=serializer.validated_data.get("is_given", True),
        ip_address=ip_address,
    )
    audit(
        action="consent",
        table_name="consents",
        record_id=application.public_id,
        user=request.user, # или None, если анонимный
        request=request,
    )
    return Response(DataConsentSerializer(consent).data, status=HTTP_201_CREATED)


class CommentPagination(PageNumberPagination):
    """Пагинация для комментариев."""

    page_size = DEFAULT_PAGE_SIZE
    max_page_size = MAX_PAGE_SIZE


@extend_schema_view(
    get=extend_schema(responses=ApplicationCommentOutSerializer(many=True)),
    post=extend_schema(
        request=ApplicationCommentInSerializer,
        responses={201: ApplicationCommentOutSerializer},
    ),
)
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def application_comments(request, public_id: uuid.UUID) -> Response:
    """Возвращает список комментариев или создаёт новый комментарий к заявке."""

    application = _get_application(public_id)

    if request.method == "GET":
        if not IsOwnerOrEmployee().has_object_permission(request, None, application):
            raise PermissionDenied()
        queryset = application.comments.select_related("user").order_by("-created_at")
        paginator = CommentPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ApplicationCommentOutSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    if not IsEmployeeOrAdmin().has_permission(request, None):
        raise PermissionDenied()

    serializer = ApplicationCommentInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comment = add_comment(
        application,
        request.user,
        serializer.validated_data["comment"],
        is_urgent=serializer.validated_data.get("is_urgent", False),
        request=request,
    )
    output = ApplicationCommentOutSerializer(comment)
    return Response(output.data, status=HTTP_201_CREATED)
