"""Проверки поведения при отказе от согласия на обработку данных."""

from __future__ import annotations

import json

from applications.models import Application, Question, Step, Survey
from applications.services.application_service import CONSENT_DECLINED_MESSAGE
from django.contrib.auth import get_user_model
from django.test import TestCase


class ConsentDeclineTests(TestCase):
    """Убеждаемся, что отказ от согласия очищает данные и возвращает подсказку."""

    def setUp(self):
        self.survey = Survey.objects.create(code="test", title="Test", version=1, is_active=True)
        self.step = Step.objects.create(survey=self.survey, code="intro", title="Intro", order=0)
        self.consent_question = Question.objects.create(
            step=self.step,
            code="q_agree",
            type=Question.QType.BOOLEAN,
            label="Согласие",
            required=True,
        )
        self.user = get_user_model().objects.create_user(
            email="applicant@example.com",
            phone="+71234567890",
            password="pass1234",
        )
        self.application = Application.objects.create(
            survey=self.survey,
            user=self.user,
            current_step=self.step,
            current_stage=self.step.order,
        )

    def test_decline_removes_application_and_user(self):
        self.client.cookies["session_token"] = str(self.application.public_id)
        response = self.client.patch(
            f"/api/v1/applications/{self.application.public_id}/draft/patch/",
            data=json.dumps(
                {
                    "answers": [
                        {
                            "question_code": "q_agree",
                            "value": False,
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["detail"], CONSENT_DECLINED_MESSAGE)
        self.assertTrue(payload.get("consent_declined"))
        self.assertFalse(Application.objects.filter(pk=self.application.pk).exists())
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
