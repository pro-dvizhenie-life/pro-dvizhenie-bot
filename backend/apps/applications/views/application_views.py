"""Публичные API-эндпоинты работы с анкетей и черновиком заявки."""

import uuid
from typing import Any, Dict, List

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models_data import Answer, Application
from ..models_form import Question, Step, Survey
from ..serializers import (
    AnswerPatchItemSerializer,
    DraftOutSerializer,
    NextOutSerializer,
)
from ..services.form_runtime import (
    build_answer_dict,
    next_step,
    validate_documents,
    validate_required,
    visible_questions,
)


def _serialize_step(step: Step | None, answers: Dict[str, Any]) -> Step | None:
    """Подготавливает шаг с отфильтрованными вопросами для сериализации."""

    if step is None:
        return None
    questions = visible_questions(step, answers)
    step._prefetched_objects_cache = {"questions": questions}
    return step


def _serialize_application(application: Application, answers: Dict[str, Any]) -> Dict[str, Any]:
    """Формирует полезную нагрузку для ответов Draft/Next."""

    step = _serialize_step(application.current_step, answers)
    payload = {
        "public_id": application.public_id,
        "current_step": step,
        "answers": answers,
    }
    serializer = DraftOutSerializer(instance=payload)
    return serializer.data


def _get_application(public_id: uuid.UUID) -> Application:
    """Возвращает заявку по публичному идентификатору или 404."""

    return get_object_or_404(
        Application.objects.select_related("survey", "current_step").prefetch_related(
            "answers__question"
        ),
        public_id=public_id,
    )


def _apply_answer_patch(application: Application, items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Сохраняет ответы пользователя и возвращает найденные ошибки."""

    if not items:
        return []

    serializer = AnswerPatchItemSerializer(data=items, many=True)
    serializer.is_valid(raise_exception=True)
    validated = serializer.validated_data

    codes = {entry["question_code"] for entry in validated}
    questions = Question.objects.filter(step__survey=application.survey, code__in=codes)
    question_map = {question.code: question for question in questions}

    errors: List[Dict[str, str]] = []
    for entry in validated:
        question = question_map.get(entry["question_code"])
        if question is None:
            errors.append(
                {
                    "question": entry["question_code"],
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


def _set_current_step(application: Application, step_code: str | None) -> None:
    """Обновляет текущий шаг заявки при явном указании кода."""

    if not step_code:
        return
    step = get_object_or_404(Step, survey=application.survey, code=step_code)
    application.current_step = step
    application.save(update_fields=["current_step"])


@api_view(["POST"])
@permission_classes([AllowAny])
def create_session(request, survey_code: str) -> Response:
    """Создаёт заявку-черновик и возвращает стартовый шаг анкеты."""

    survey = get_object_or_404(Survey, code=survey_code, is_active=True)
    current_step = survey.steps.first()

    application = Application.objects.create(
        survey=survey,
        user=request.user if request.user.is_authenticated else None,
        current_step=current_step,
    )
    answers: Dict[str, Any] = {}
    data = _serialize_application(application, answers)

    response = Response(data, status=status.HTTP_201_CREATED)
    response.set_cookie(
        "session_token",
        str(uuid.uuid4()),
        httponly=True,
        samesite="Lax",
    )
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def get_draft(request, public_id: uuid.UUID) -> Response:
    """Возвращает текущее состояние черновика заявки."""

    application = _get_application(public_id)
    answers = build_answer_dict(application)
    data = _serialize_application(application, answers)
    return Response(data)


@api_view(["PATCH"])
@permission_classes([AllowAny])
def patch_draft(request, public_id: uuid.UUID) -> Response:
    """Сохраняет изменения черновика и, при необходимости, переключает шаг."""

    application = _get_application(public_id)

    items = request.data.get("answers", []) if isinstance(request.data, dict) else []
    errors = _apply_answer_patch(application, items)
    if errors:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    step_code = request.data.get("step_code") if isinstance(request.data, dict) else None
    if step_code:
        _set_current_step(application, step_code)
        application.refresh_from_db(fields=["current_step"])

    answers = build_answer_dict(application)
    data = _serialize_application(application, answers)
    return Response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
def post_next(request, public_id: uuid.UUID) -> Response:
    """Фиксирует ответы шага и вычисляет следующий шаг анкеты."""

    application = _get_application(public_id)

    if isinstance(request.data, dict) and request.data.get("answers"):
        errors = _apply_answer_patch(application, request.data["answers"])
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    answers = build_answer_dict(application)
    upcoming = next_step(application.survey, application.current_step, answers)
    application.current_step = upcoming
    application.save(update_fields=["current_step"])

    payload = {
        "public_id": application.public_id,
        "current_step": _serialize_step(upcoming, answers),
        "answers": answers,
    }
    serializer = NextOutSerializer(instance=payload)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([AllowAny])
def post_submit(request, public_id: uuid.UUID) -> Response:
    """Выполняет финальную отправку заявки с проверкой обязательных данных."""

    application = _get_application(public_id)

    if isinstance(request.data, dict) and request.data.get("answers"):
        errors = _apply_answer_patch(application, request.data["answers"])
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    answers = build_answer_dict(application)

    step_errors: List[Dict[str, str]] = []
    if application.current_step:
        step_errors = validate_required(application.current_step, answers)
    document_errors = validate_documents(application.survey, answers)

    if step_errors or document_errors:
        return Response(
            {
                "errors": step_errors,
                "document_errors": document_errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    application.status = Application.Status.SUBMITTED
    application.submitted_at = timezone.now()
    application.save(update_fields=["status", "submitted_at"])

    return Response(
        {
            "public_id": str(application.public_id),
            "status": application.status,
        }
    )
