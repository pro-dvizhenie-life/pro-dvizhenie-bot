"""Команда загрузки базовой анкеты по сценарию чат-бота."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import (
    Condition,
    DocumentRequirement,
    Option,
    Question,
    Step,
    Survey,
)
from ...services.form_runtime import next_step, visible_questions


@dataclass
class FixtureEntry:
    """Упрощённое представление записи фикстуры."""

    model: str
    pk: int
    fields: Dict[str, object]

    @classmethod
    def from_raw(cls, raw: Dict[str, object]) -> "FixtureEntry":
        return cls(model=raw["model"], pk=raw["pk"], fields=raw["fields"])  # type: ignore[index]


class Command(BaseCommand):
    help = "Загружает/обновляет анкету default из фикстуры и выполняет sanity-check'и."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--path",
            dest="path",
            type=str,
            default=None,
            help="Путь к JSON-фикстуре (по умолчанию: backend/apps/applications/fixtures/survey_default.json)",
        )

    def handle(self, *args, **options) -> None:
        fixture_path = self._resolve_path(options.get("path"))
        entries = self._load_fixture(fixture_path)
        by_model = self._group_by_model(entries)

        with transaction.atomic():
            survey_map = self._upsert_surveys(by_model.get("applications.survey", []))
            if not survey_map:
                raise CommandError("Фикстура не содержит модель applications.survey.")
            step_map = self._upsert_steps(by_model.get("applications.step", []), survey_map)
            question_map = self._upsert_questions(by_model.get("applications.question", []), step_map)
            self._sync_options(by_model.get("applications.option", []), question_map)
            self._sync_conditions(by_model.get("applications.condition", []), survey_map, step_map, question_map)
            self._sync_documents(by_model.get("applications.documentrequirement", []), survey_map)

        target_surveys = list(survey_map.values())
        for survey in target_surveys:
            self._run_sanity_checks(survey)
            stats = self._collect_stats(survey)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Анкета '{survey.code}' загружена: steps={stats['steps']} questions={stats['questions']} "
                    f"options={stats['options']} conditions={stats['conditions']} documents={stats['documents']}"
                )
            )

    def _resolve_path(self, override: Optional[str]) -> Path:
        if override:
            path = Path(override)
        else:
            path = Path(__file__).resolve().parents[2] / "fixtures" / "survey_default.json"
        if not path.exists():
            raise CommandError(f"Фикстура не найдена: {path}")
        return path

    def _load_fixture(self, path: Path) -> List[FixtureEntry]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - защитный код
            raise CommandError(f"Ошибка разбора JSON: {exc}") from exc
        if not isinstance(raw, list):
            raise CommandError("Ожидался список записей в фикстуре.")
        return [FixtureEntry.from_raw(item) for item in raw]

    def _group_by_model(self, entries: Iterable[FixtureEntry]) -> Dict[str, List[FixtureEntry]]:
        grouped: Dict[str, List[FixtureEntry]] = {}
        for entry in entries:
            grouped.setdefault(entry.model, []).append(entry)
        return grouped

    def _upsert_surveys(self, entries: Iterable[FixtureEntry]) -> Dict[int, Survey]:
        survey_map: Dict[int, Survey] = {}
        for entry in entries:
            fields = entry.fields
            survey, _ = Survey.objects.update_or_create(
                code=fields["code"],
                defaults={
                    "title": fields.get("title", ""),
                    "version": fields.get("version", 1),
                    "is_active": fields.get("is_active", True),
                },
            )
            survey_map[entry.pk] = survey
        return survey_map

    def _upsert_steps(
        self,
        entries: Iterable[FixtureEntry],
        survey_map: Dict[int, Survey],
    ) -> Dict[int, Step]:
        step_map: Dict[int, Step] = {}
        codes_by_survey: Dict[int, set[str]] = {}
        for entry in entries:
            fields = entry.fields
            survey = survey_map.get(fields["survey"])
            if survey is None:
                raise CommandError(f"Неизвестный survey pk {fields['survey']} для шага {fields['code']}")
            step, _ = Step.objects.update_or_create(
                survey=survey,
                code=fields["code"],
                defaults={
                    "title": fields.get("title", ""),
                    "order": fields.get("order", 0),
                },
            )
            step_map[entry.pk] = step
            codes_by_survey.setdefault(survey.id, set()).add(step.code)
        for survey in survey_map.values():
            codes = codes_by_survey.get(survey.id, set())
            Step.objects.filter(survey=survey).exclude(code__in=codes).delete()
        return step_map

    def _upsert_questions(
        self,
        entries: Iterable[FixtureEntry],
        step_map: Dict[int, Step],
    ) -> Dict[int, Question]:
        question_map: Dict[int, Question] = {}
        codes_by_step: Dict[int, set[str]] = {}
        for entry in entries:
            fields = entry.fields
            step = step_map.get(fields["step"])
            if step is None:
                raise CommandError(f"Неизвестный step pk {fields['step']} для вопроса {fields['code']}")
            question, _ = Question.objects.update_or_create(
                step=step,
                code=fields["code"],
                defaults={
                    "type": fields.get("type", "text"),
                    "label": fields.get("label", ""),
                    "required": fields.get("required", False),
                    "payload": fields.get("payload", {}),
                },
            )
            question_map[entry.pk] = question
            codes_by_step.setdefault(step.id, set()).add(question.code)
        for step in step_map.values():
            codes = codes_by_step.get(step.id, set())
            Question.objects.filter(step=step).exclude(code__in=codes).delete()
        return question_map

    def _sync_options(
        self,
        entries: Iterable[FixtureEntry],
        question_map: Dict[int, Question],
    ) -> None:
        options_by_question: Dict[int, List[FixtureEntry]] = {}
        for entry in entries:
            fields = entry.fields
            options_by_question.setdefault(fields["question"], []).append(entry)
        for fixture_pk, question in question_map.items():
            question_options = options_by_question.get(fixture_pk, [])
            seen_values: List[str] = []
            for option_entry in question_options:
                fields = option_entry.fields
                value = str(fields.get("value"))
                option, _ = Option.objects.update_or_create(
                    question=question,
                    value=value,
                    defaults={
                        "label": fields.get("label", ""),
                        "order": fields.get("order", 0),
                    },
                )
                seen_values.append(option.value)
            Option.objects.filter(question=question).exclude(value__in=seen_values).delete()
        dangling = set(options_by_question.keys()) - set(question_map.keys())
        if dangling:
            raise CommandError(
                "Фикстура содержит варианты ответов без соответствующих вопросов: " + ", ".join(map(str, sorted(dangling)))
            )

    def _sync_conditions(
        self,
        entries: Iterable[FixtureEntry],
        survey_map: Dict[int, Survey],
        step_map: Dict[int, Step],
        question_map: Dict[int, Question],
    ) -> None:
        for survey in survey_map.values():
            survey.conditions.all().delete()
        for entry in entries:
            fields = entry.fields
            survey = survey_map.get(fields["survey"])
            if survey is None:
                raise CommandError("Неизвестный survey pk для условия")
            question = question_map.get(fields.get("question")) if fields.get("question") else None
            from_step = step_map.get(fields.get("from_step")) if fields.get("from_step") else None
            goto_step = step_map.get(fields.get("goto_step")) if fields.get("goto_step") else None
            Condition.objects.create(
                survey=survey,
                scope=fields["scope"],
                expression=fields.get("expression"),
                question=question,
                from_step=from_step,
                goto_step=goto_step,
            )

    def _sync_documents(
        self,
        entries: Iterable[FixtureEntry],
        survey_map: Dict[int, Survey],
    ) -> None:
        codes_by_survey: Dict[int, set[str]] = {}
        for entry in entries:
            fields = entry.fields
            survey = survey_map.get(fields["survey"])
            if survey is None:
                raise CommandError("Неизвестный survey pk для DocumentRequirement")
            doc, _ = DocumentRequirement.objects.update_or_create(
                survey=survey,
                code=fields["code"],
                defaults={
                    "label": fields.get("label", ""),
                    "expression": fields.get("expression"),
                },
            )
            codes_by_survey.setdefault(survey.id, set()).add(doc.code)
        for survey in survey_map.values():
            codes = codes_by_survey.get(survey.id, set())
            DocumentRequirement.objects.filter(survey=survey).exclude(code__in=codes).delete()

    def _run_sanity_checks(self, survey: Survey) -> None:
        required_questions = list(
            Question.objects.filter(step__survey=survey, required=True).select_related("step")
        )
        coverage = {question.code: False for question in required_questions}
        scenarios = [
            {"q_agree": True, "q_who_fills": "self", "q_tsr_certificate_has": False, "q_other_funds_active": False},
            {"q_agree": True, "q_who_fills": "relative", "q_tsr_certificate_has": True, "q_other_funds_active": False},
            {"q_agree": True, "q_who_fills": "parent", "q_tsr_certificate_has": False, "q_other_funds_active": True},
        ]
        for base_answers in scenarios:
            answers = dict(base_answers)
            visited: set[int] = set()
            step = next_step(survey, None, answers)
            while step and step.id not in visited:
                visited.add(step.id)
                for question in visible_questions(step, answers):
                    if question.required:
                        coverage[question.code] = True
                step = next_step(survey, step, answers)
        missing = [code for code, seen in coverage.items() if not seen]
        if missing:
            raise CommandError(
                "Обязательные вопросы недостижимы в сценариях: " + ", ".join(sorted(missing))
            )

    def _collect_stats(self, survey: Survey) -> Dict[str, int]:
        return {
            "steps": survey.steps.count(),
            "questions": Question.objects.filter(step__survey=survey).count(),
            "options": Option.objects.filter(question__step__survey=survey).count(),
            "conditions": survey.conditions.count(),
            "documents": survey.doc_requirements.count(),
        }

