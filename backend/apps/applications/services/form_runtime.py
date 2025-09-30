"""Рантайм-утилиты для работы с динамическими анкетами."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from ..models import Application, Condition, Question, Step, Survey


def build_answer_dict(application: Application) -> Dict[str, Any]:
    """Возвращает словарь ответов по кодам вопросов."""

    answers: Dict[str, Any] = {}
    queryset = application.answers.select_related("question")
    for answer in queryset:
        answers[answer.question.code] = answer.value
    return answers


def _resolve_operand(value: Any, ctx: Dict[str, Any]) -> Any:
    if isinstance(value, dict) and value.keys() == {"var"}:
        return ctx.get(value["var"])
    if isinstance(value, dict):
        return eval_expr(value, ctx)
    if isinstance(value, list):
        return [_resolve_operand(item, ctx) for item in value]
    if isinstance(value, str) and value.startswith("$"):
        return ctx.get(value[1:])
    return value


def eval_expr(expr: Any, ctx: Dict[str, Any]) -> bool:
    """Вычисляет JSON-logic подобное выражение."""

    if expr is None:
        return True
    if isinstance(expr, bool):
        return expr
    if isinstance(expr, dict):
        if "all" in expr:
            return all(eval_expr(item, ctx) for item in expr["all"])
        if "any" in expr:
            return any(eval_expr(item, ctx) for item in expr["any"])
        if "and" in expr:
            return all(eval_expr(item, ctx) for item in expr["and"])
        if "or" in expr:
            return any(eval_expr(item, ctx) for item in expr["or"])
        if "not" in expr:
            operands = expr["not"]
            if not isinstance(operands, list):
                operands = [operands]
            return not any(eval_expr(item, ctx) for item in operands)
        if "var" in expr and len(expr) == 1:
            return bool(ctx.get(expr["var"]))
        if len(expr) == 1:
            op, operands = next(iter(expr.items()))
            if not isinstance(operands, Iterable) or isinstance(operands, (str, bytes)):
                operands = [operands]
            resolved = [_resolve_operand(item, ctx) for item in operands]
            op = op.lower()
            if op in {"==", "eq"}:
                return resolved[0] == resolved[1]
            if op in {"!=", "neq"}:
                return resolved[0] != resolved[1]
            if op == "in":
                try:
                    return resolved[0] in resolved[1]
                except TypeError:
                    return False
            if op in {">", "gt"}:
                return resolved[0] > resolved[1]
            if op in {">=", "gte"}:
                return resolved[0] >= resolved[1]
            if op in {"<", "lt"}:
                return resolved[0] < resolved[1]
            if op in {"<=", "lte"}:
                return resolved[0] <= resolved[1]
            if op == "contains":  # вспомогательная операция
                try:
                    return resolved[1] in resolved[0]
                except TypeError:
                    return False
    if isinstance(expr, list):
        return all(eval_expr(item, ctx) for item in expr)
    return bool(_resolve_operand(expr, ctx))


def visible_questions(step: Step, answers: Dict[str, Any]) -> List[Question]:
    """Возвращает список вопросов, которые должны быть показаны."""

    conditions = (
        Condition.objects.filter(scope="question", question__step=step)
        .select_related("question")
        .all()
    )
    condition_map: Dict[int, List[Condition]] = {}
    for condition in conditions:
        condition_map.setdefault(condition.question_id, []).append(condition)
    questions = list(step.questions.prefetch_related("options"))
    questions.sort(key=lambda item: item.payload.get("order", item.id))
    visible: List[Question] = []
    for question in questions:
        required_conditions = condition_map.get(question.id)
        if not required_conditions:
            visible.append(question)
            continue
        if all(eval_expr(cond.expression, answers) for cond in required_conditions):
            visible.append(question)
    visible.sort(key=lambda item: item.payload.get("order", item.id))
    return visible


def next_step(
    survey: Survey,
    current_step: Optional[Step],
    answers: Dict[str, Any],
) -> Optional[Step]:
    """Возвращает следующий шаг анкеты согласно условиям."""

    steps = list(survey.steps.order_by("order", "id"))
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
    if idx + 1 < len(steps):
        return steps[idx + 1]
    return None


def validate_required(step: Step, answers: Dict[str, Any]) -> List[Dict[str, str]]:
    """Проверяет обязательные вопросы шага."""

    errors: List[Dict[str, str]] = []
    for question in visible_questions(step, answers):
        if not question.required:
            continue
        value = answers.get(question.code)
        if value in (None, "", [], {}):
            errors.append({"field": question.code, "message": "Обязательное поле"})
    return errors


def validate_documents(survey: Survey, answers: Dict[str, Any]) -> List[Dict[str, str]]:
    """Заглушка проверки документов."""

    return []


__all__ = [
    "build_answer_dict",
    "eval_expr",
    "visible_questions",
    "next_step",
    "validate_required",
    "validate_documents",
]
