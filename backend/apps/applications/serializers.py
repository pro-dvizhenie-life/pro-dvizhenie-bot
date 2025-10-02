"""Сериализаторы публичного и административного API заявок."""

from __future__ import annotations

from typing import Any, Dict

from config.constants import DEFAULT_COMMENTS_LIMIT, DEFAULT_CONSENT_TYPE
from rest_framework import serializers

from .models import (
    Application,
    ApplicationComment,
    ApplicationStatusHistory,
    DataConsent,
    Option,
    Question,
    Step,
    Survey,
)
from .services.form_runtime import build_answer_dict


class OptionSerializer(serializers.ModelSerializer):
    """Представление варианта ответа."""

    class Meta:
        model = Option
        fields = ("value", "label", "order")


class QuestionSerializer(serializers.ModelSerializer):
    """Представление вопроса с вариантами ответа."""

    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = (
            "id",
            "code",
            "type",
            "label",
            "required",
            "payload",
            "options",
        )


class StepSerializer(serializers.ModelSerializer):
    """Представление шага анкеты."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Step
        fields = ("id", "code", "title", "order", "questions")


class SurveySerializer(serializers.ModelSerializer):
    """Полная анкета с шагами."""

    steps = StepSerializer(many=True, read_only=True)

    class Meta:
        model = Survey
        fields = ("id", "code", "title", "version", "is_active", "steps")


class AnswerPatchItemSerializer(serializers.Serializer):
    """Элемент патча ответа пользователя."""

    question_code = serializers.SlugField()
    value = serializers.JSONField()


class DraftPatchSerializer(serializers.Serializer):
    """Входные данные для обновления черновика анкеты."""

    answers = AnswerPatchItemSerializer(many=True, required=False)
    step_code = serializers.CharField(required=False, allow_blank=True)


class CreateSessionRequestSerializer(serializers.Serializer):
    """Параметры создания сессии заполнения анкеты."""

    applicant_type = serializers.CharField(required=False, allow_blank=True)


class DraftOutSerializer(serializers.Serializer):
    """Снимок состояния черновика анкеты."""

    public_id = serializers.UUIDField()
    current_stage = serializers.IntegerField()
    current_step = StepSerializer(allow_null=True)
    answers = serializers.DictField(child=serializers.JSONField(), default=dict)


class NextOutSerializer(DraftOutSerializer):
    """Ответ при переходе к следующему шагу."""

    pass


class SubmitResponseSerializer(serializers.Serializer):
    """Ответ после успешной отправки анкеты."""

    public_id = serializers.UUIDField()
    status = serializers.CharField()


class ApplicationShortSerializer(serializers.ModelSerializer):
    """Краткая информация о заявке для списков."""

    survey_code = serializers.CharField(source="survey.code", read_only=True)

    class Meta:
        model = Application
        fields = (
            "public_id",
            "survey_code",
            "status",
            "applicant_type",
            "current_stage",
            "created_at",
            "submitted_at",
        )


class ApplicationCommentOutSerializer(serializers.ModelSerializer):
    """Комментарий заявки для отображения."""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ApplicationComment
        fields = (
            "id",
            "comment",
            "is_urgent",
            "user_id",
            "user_email",
            "created_at",
        )


class ApplicationCommentInSerializer(serializers.Serializer):
    """Входные данные для создания комментария."""

    comment = serializers.CharField()
    is_urgent = serializers.BooleanField(required=False, default=False)


class ApplicationStatusPatchSerializer(serializers.Serializer):
    """Изменение статуса заявки."""

    new_status = serializers.CharField()


class StatusResponseSerializer(serializers.Serializer):
    """Унифицированный ответ со статусом заявки."""

    status = serializers.CharField()


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    """Сериализатор истории статусов."""

    changed_by_id = serializers.IntegerField(source="changed_by.id", read_only=True)
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = ApplicationStatusHistory
        fields = (
            "id",
            "old_status",
            "new_status",
            "changed_by_id",
            "changed_by_email",
            "created_at",
        )


class DataConsentSerializer(serializers.ModelSerializer):
    """Сериализатор согласий."""

    class Meta:
        model = DataConsent
        fields = (
            "consent_type",
            "is_given",
            "given_at",
            "ip_address",
        )
        read_only_fields = ("given_at", "ip_address")
        extra_kwargs = {
            "consent_type": {"required": False, "default": DEFAULT_CONSENT_TYPE},
            "is_given": {"required": False, "default": True},
        }


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Полная информация о заявке."""

    survey_code = serializers.CharField(source="survey.code", read_only=True)
    answers = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    consents = DataConsentSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = (
            "public_id",
            "survey_code",
            "status",
            "applicant_type",
            "current_stage",
            "created_at",
            "submitted_at",
            "answers",
            "comments",
            "status_history",
            "consents",
        )

    def get_answers(self, obj: Application) -> Dict[str, Any]:
        """Возвращает ответы заявки в виде словаря по кодам вопросов."""

        return build_answer_dict(obj)

    def get_comments(self, obj: Application) -> list[dict[str, Any]]:
        """Загружает комментарии заявки с учётом лимита из запроса."""

        request = self.context.get("request")
        limit = int(request.query_params.get("comments_limit", DEFAULT_COMMENTS_LIMIT)) if request else DEFAULT_COMMENTS_LIMIT
        queryset = obj.comments.select_related("user").order_by("-created_at")[:limit]
        return ApplicationCommentOutSerializer(
            queryset,
            many=True,
            context=self.context,
        ).data


class TimelineEventSerializer(serializers.Serializer):
    """Элемент таймлайна заявки."""

    type = serializers.CharField()
    data = serializers.DictField()
    created_at = serializers.DateTimeField()


class TimelineResponseSerializer(serializers.Serializer):
    """Ответ для таймлайна заявки."""

    timeline = TimelineEventSerializer(many=True)
