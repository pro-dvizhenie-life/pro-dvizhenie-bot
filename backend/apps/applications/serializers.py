"""Сериализаторы публичной анкеты и её черновиков."""

from rest_framework import serializers

from .models_form import Option, Question, Step, Survey


class OptionSerializer(serializers.ModelSerializer):
    """Представление варианта ответа."""

    class Meta:
        model = Option
        fields = ("value", "label", "order")


class QuestionSerializer(serializers.ModelSerializer):
    """Представление вопроса с возможными вариантами ответа."""

    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "code", "type", "label", "required", "payload", "options")


class StepSerializer(serializers.ModelSerializer):
    """Последовательность вопросов, сгруппированных в шаг анкеты."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Step
        fields = ("id", "code", "title", "order", "questions")


class SurveySerializer(serializers.ModelSerializer):
    """Полная анкета с шагами и вопросами."""

    steps = StepSerializer(many=True, read_only=True)

    class Meta:
        model = Survey
        fields = ("id", "code", "title", "version", "is_active", "steps")


class AnswerPatchItemSerializer(serializers.Serializer):
    """Элемент патча ответа пользователя."""

    question_code = serializers.SlugField()
    value = serializers.JSONField()


class DraftOutSerializer(serializers.Serializer):
    """Снимок состояния черновика анкеты."""

    public_id = serializers.UUIDField()
    current_step = StepSerializer(allow_null=True)
    answers = serializers.DictField(child=serializers.JSONField(), default=dict)


class NextOutSerializer(DraftOutSerializer):
    """Ответ при переходе к следующему шагу."""

    pass
