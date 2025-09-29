"""Рантайм-утилиты для расчёта логики анкет и валидации ответов."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from ..models_data import Application
from ..models_form import Condition, Question, Step, Survey


def build_answer_dict(application: Application) -> Dict[str, Any]:
    """Собирает словарь ответов по кодам вопросов для быстрой выборки."""

    answers: Dict[str, Any] = {}
    for answer in application.answers.select_related("question"):
        answers[answer.question.code] = answer.value
    return answers


def _resolve_operand(value: Any, ctx: Dict[str, Any]) -> Any:
    """Преобразует операнд JSON-logic в конкретное значение контекста."""

    if isinstance(value, dict) and set(value.keys()) == {"var"}:
        return ctx.get(value["var"])
    if isinstance(value, dict):
        return eval_expr(value, ctx)
    if isinstance(value, list):
        return [
            _resolve_operand(item, ctx) if isinstance(item, (dict, list)) else item
            for item in value
        ]
    return value


def eval_expr(expr: Any, ctx: Dict[str, Any]) -> bool:
    """Вычисляет подмножество JSON-logic для проверки условий показа."""

    if expr is None:
        return True

    if isinstance(expr, bool):
        return expr

    if isinstance(expr, dict):
        if "all" in expr:
            return all(eval_expr(item, ctx) for item in expr["all"])
        if "any" in expr:
            return any(eval_expr(item, ctx) for item in expr["any"])

        if "var" in expr and len(expr) == 1:
            return ctx.get(expr["var"])

        if len(expr) == 1:
            op, operands = next(iter(expr.items()))
            if not isinstance(operands, Iterable) or isinstance(operands, (str, bytes)):
                operands = [operands]
            resolved = [_resolve_operand(item, ctx) for item in operands]

            if op == "==":
                left, right = resolved
                return left == right
            if op == "!=":
                left, right = resolved
                return left != right
            if op == "in":
                left, right = resolved
                try:
                    return left in right
                except TypeError:
                    return False
            if op == ">":
                left, right = resolved
                return left > right
            if op == ">=":
                left, right = resolved
                return left >= right
            if op == "<":
                left, right = resolved
                return left < right
            if op == "<=":
                left, right = resolved
                return left <= right

    if isinstance(expr, list):
        return all(eval_expr(item, ctx) for item in expr)

    return bool(_resolve_operand(expr, ctx))


def visible_questions(step: Step, answers: Dict[str, Any]) -> List[Question]:
    """Возвращает вопросы шага, которые следует показать пользователю."""

    conditions = (
        Condition.objects.filter(scope="question", question__step=step)
        .select_related("question")
        .all()
    )
    condition_map: Dict[int, List[Condition]] = {}
    for condition in conditions:
        condition_map.setdefault(condition.question_id, []).append(condition)

    questions = list(step.questions.prefetch_related("options"))

    visible: List[Question] = []
    for question in questions:
        requirement = condition_map.get(question.id)
        if not requirement:
            visible.append(question)
            continue
        if all(eval_expr(cond.expression, answers) for cond in requirement):
            visible.append(question)
    return visible


def next_step(
    survey: Survey,
    current_step: Optional[Step],
    answers: Dict[str, Any],
) -> Optional[Step]:
    """Определяет следующий шаг анкеты с учётом условий перехода."""

    steps = list(survey.steps.all())
    if not steps:
        return None

    if current_step is None:
        return steps[0]

    step_conditions = Condition.objects.filter(scope="step", from_step=current_step)
    for condition in step_conditions:
        if eval_expr(condition.expression, answers):
            return condition.goto_step

    try:
        idx = steps.index(current_step)
    except ValueError:
        return None

    next_idx = idx + 1
    if next_idx < len(steps):
        return steps[next_idx]
    return None


def validate_required(step: Step, answers: Dict[str, Any]) -> List[Dict[str, str]]:
    """Проверяет обязательные вопросы шага и возвращает ошибки."""

    errors: List[Dict[str, str]] = []
    for question in visible_questions(step, answers):
        if not question.required:
            continue
        value = answers.get(question.code)
        if value in (None, "") or value == [] or value == {}:
            errors.append({"question": question.code, "message": "Это обязательный вопрос."})
    return errors


def validate_documents(survey: Survey, answers: Dict[str, Any]) -> List[Dict[str, str]]:
    """Заглушка проверки документов, будет расширена позже."""

    return []
