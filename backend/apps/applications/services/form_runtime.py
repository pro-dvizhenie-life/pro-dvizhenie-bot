"""Рантайм-утилиты для работы с динамическими анкетами."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..models import Application, Condition, Question, Step, Survey


def build_answer_dict(application: Application) -> Dict[str, Any]:
    """Возвращает словарь ответов по кодам вопросов."""

    answers: Dict[str, Any] = {}
    prefetched = getattr(application, "_prefetched_answers", None)
    if prefetched is not None:
        iterable = prefetched
    else:
        iterable = application.answers.select_related("question")
    for answer in iterable:
        if not answer.question:
            continue
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


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+7\d{10}$")


def _option_values(question: Question) -> Sequence[str]:
    return list(question.options.values_list("value", flat=True))


def _validate_select(question: Question, raw_value: Any) -> Tuple[Optional[Any], Optional[str]]:
    if raw_value in (None, ""):
        return raw_value, None
    if not isinstance(raw_value, str):
        return None, "Ожидается строковое значение."
    allowed = set(_option_values(question))
    if raw_value not in allowed:
        return None, "Недопустимое значение."
    return raw_value, None


def _validate_multiselect(question: Question, raw_value: Any) -> Tuple[Optional[Any], Optional[str]]:
    if raw_value in (None, []):
        return [], None
    if not isinstance(raw_value, (list, tuple)):
        return None, "Ожидается список значений."
    allowed = set(_option_values(question))
    cleaned: List[str] = []
    for item in raw_value:
        if not isinstance(item, str):
            return None, "Коды вариантов должны быть строками."
        if item not in allowed:
            return None, "Недопустимое значение в списке."
        if item not in cleaned:
            cleaned.append(item)
    return cleaned, None


def _validate_boolean(raw_value: Any) -> Tuple[Optional[Any], Optional[str]]:
    if raw_value in (None, ""):
        return None, None
    if isinstance(raw_value, bool):
        return raw_value, None
    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True, None
        if lowered in {"false", "0", "no", "off"}:
            return False, None
    return None, "Ожидается булево значение."


def _validate_string(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    if raw_value in (None, ""):
        return raw_value, None
    if not isinstance(raw_value, str):
        return None, "Ожидается текстовая строка."
    return raw_value.strip(), None


def _validate_email(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    value, error = _validate_string(raw_value)
    if error or value in (None, ""):
        return value, error
    if not EMAIL_RE.match(value):
        return None, "Некорректный формат email."
    return value, None


def _validate_phone(raw_value: Any) -> Tuple[Optional[str], Optional[str]]:
    value, error = _validate_string(raw_value)
    if error or value in (None, ""):
        return value, error
    if not PHONE_RE.match(value):
        return None, "Некорректный формат телефона."
    return value, None


def _validate_date(raw_value: Any, constraints: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    if raw_value in (None, ""):
        return raw_value, None
    if not isinstance(raw_value, str):
        return None, "Ожидается строка в формате YYYY-MM-DD."
    try:
        parsed = datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        return None, "Некорректный формат даты."
    if constraints.get("date_not_future") and parsed > date.today():
        return None, "Дата не может быть в будущем."
    return parsed.isoformat(), None


def validate_answer_value(question: Question, raw_value: Any) -> Tuple[Optional[Any], Optional[str]]:
    """Проверяет соответствие ответа типу вопроса и ограничениям."""

    payload = question.payload or {}
    constraints = payload.get("constraints") or {}
    qtype = question.type

    if qtype in {Question.QType.TEXT, Question.QType.TEXTAREA}:
        return _validate_string(raw_value)
    if qtype == Question.QType.EMAIL:
        return _validate_email(raw_value)
    if qtype == Question.QType.PHONE:
        return _validate_phone(raw_value)
    if qtype == Question.QType.DATE:
        return _validate_date(raw_value, constraints)
    if qtype in {Question.QType.BOOLEAN, Question.QType.YES_NO}:
        return _validate_boolean(raw_value)
    if qtype in {Question.QType.SELECT, Question.QType.SELECT_ONE}:
        return _validate_select(question, raw_value)
    if qtype in {Question.QType.MULTISELECT, Question.QType.SELECT_MANY}:
        return _validate_multiselect(question, raw_value)
    if qtype == Question.QType.NUMBER:
        if raw_value in (None, ""):
            return raw_value, None
        if isinstance(raw_value, (int, float)):
            return raw_value, None
        try:
            return float(raw_value), None
        except (TypeError, ValueError):
            return None, "Ожидается числовое значение."
    if qtype in {Question.QType.FILE, Question.QType.FILE_MULTI}:
        return raw_value, None
    return raw_value, None


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


def _derive_branch(application: Application, answers: Dict[str, Any]) -> Optional[str]:
    mapping = {
        "self": "adult",
        "relative": "adult",
        "parent": "child",
        "guardian": "child",
    }
    applicant_type = application.applicant_type or ""
    branch = mapping.get(applicant_type.strip())
    if branch:
        return branch
    who_fills = answers.get("q_who_fills")
    if isinstance(who_fills, str):
        return mapping.get(who_fills.strip())
    return None


def _derive_age(answers: Dict[str, Any]) -> Optional[int]:
    dob_value = answers.get("q_dob")
    if not dob_value:
        return None
    if isinstance(dob_value, date):
        dob = dob_value
    elif isinstance(dob_value, str):
        try:
            dob = datetime.strptime(dob_value, "%Y-%m-%d").date()
        except ValueError:
            return None
    else:
        return None
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(years, 0)


def validate_documents(application: Application, answers: Dict[str, Any]) -> List[Dict[str, str]]:
    """Проверяет выполнение требований по документам анкеты."""

    requirements = list(application.survey.doc_requirements.all())
    if not requirements:
        return []

    from documents.models import DocumentVersion  # type: ignore
    from documents.services import list_versions  # локальный импорт во избежание циклов

    context: Dict[str, Any] = dict(answers)
    branch = _derive_branch(application, answers)
    if branch:
        context.setdefault("branch", branch)
    age = _derive_age(answers)
    if age is not None:
        context.setdefault("age", age)

    versions = list(list_versions(application))
    latest_by_document: Dict[int, DocumentVersion] = {}
    for version in versions:
        if version.document_id not in latest_by_document:
            latest_by_document[version.document_id] = version

    docs_by_code: Dict[str, List[DocumentVersion]] = {}
    for version in latest_by_document.values():
        if version.document.requirement_id:
            code = version.document.requirement.code
        else:
            code = version.document.code or ""
        if not code:
            continue
        docs_by_code.setdefault(code, []).append(version)

    acceptable_statuses = {
        DocumentVersion.Status.AVAILABLE,
        DocumentVersion.Status.UPLOADED,
    }

    errors: List[Dict[str, str]] = []
    for requirement in requirements:
        expression = requirement.expression
        required = True
        if expression not in (None, True):
            required = bool(eval_expr(expression, context))
        if not required:
            continue
        versions_for_requirement = docs_by_code.get(requirement.code, [])
        has_ready_version = any(
            version.status in acceptable_statuses for version in versions_for_requirement
        )
        if not has_ready_version:
            errors.append(
                {
                    "field": f"documents.{requirement.code}",
                    "message": f"Документ «{requirement.label}» не загружен или ожидает проверки.",
                }
            )
    return errors


__all__ = [
    "build_answer_dict",
    "eval_expr",
    "validate_answer_value",
    "visible_questions",
    "next_step",
    "validate_required",
    "validate_documents",
]
