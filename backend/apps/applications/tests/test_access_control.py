"""Тесты для проверки разграничения доступов."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from ..models import Application, Survey

User = get_user_model()


class AccessControlTests(TestCase):
    """Проверки доступов для разных ролей."""

    def setUp(self):
        self.client = APIClient()

        # Создаем пользователей
        self.applicant_a = User.objects.create_user(
            email="applicant_a@test.com", phone="+79990000001", password="password", role=User.Role.APPLICANT
        )
        self.applicant_b = User.objects.create_user(
            email="applicant_b@test.com", phone="+79990000002", password="password", role=User.Role.APPLICANT
        )
        self.employee = User.objects.create_user(
            email="employee@test.com", phone="+79990000003", password="password", role=User.Role.EMPLOYEE
        )
        self.admin = User.objects.create_user(
            email="admin@test.com", phone="+79990000004", password="password", role=User.Role.ADMIN, is_staff=True
        )

        # Создаем анкету и заявки
        self.survey = Survey.objects.create(code="main", title="Main", version="1", is_active=True)
        self.application_a = Application.objects.create(survey=self.survey, user=self.applicant_a)
        self.application_b = Application.objects.create(survey=self.survey, user=self.applicant_b)

    def test_anonymous_user_cannot_list_applications(self):
        """Анонимный пользователь не может получить список заявок."""
        response = self.client.get("/api/v1/applications/admin/applications/")
        self.assertEqual(response.status_code, 401)  # IsAuthenticated

    def test_anonymous_user_cannot_get_application_details(self):
        """Анонимный пользователь не может получить детали заявки."""
        url = f"/api/v1/applications/{self.application_a.public_id}/draft/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)  # IsOwnerOrEmployee -> has_permission

    def test_anonymous_user_can_create_application(self):
        """Анонимный пользователь может создать новую заявку."""
        url = f"/api/v1/applications/forms/{self.survey.code}/sessions/"
        response = self.client.post(url, {"applicant_type": "self"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue("session_token" in response.cookies)

    def test_applicant_can_list_only_own_applications(self):
        """Заявитель видит в списке только свои заявки."""
        self.client.force_authenticate(user=self.applicant_a)
        response = self.client.get("/api/v1/applications/admin/applications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["public_id"], str(self.application_a.public_id))

    def test_applicant_can_get_own_application_details(self):
        """Заявитель может получить детали своей заявки."""
        self.client.force_authenticate(user=self.applicant_a)
        url = f"/api/v1/applications/{self.application_a.public_id}/draft/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_applicant_cannot_get_others_application_details(self):
        """Заявитель не может получить детали чужой заявки."""
        self.client.force_authenticate(user=self.applicant_a)
        url = f"/api/v1/applications/{self.application_b.public_id}/draft/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # IsOwnerOrEmployee -> has_object_permission

    def test_employee_can_list_all_applications(self):
        """Сотрудник видит в списке все заявки."""
        self.client.force_authenticate(user=self.employee)
        response = self.client.get("/api/v1/applications/admin/applications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    def test_employee_can_get_any_application_details(self):
        """Сотрудник может получить детали любой заявки."""
        self.client.force_authenticate(user=self.employee)
        url_a = f"/api/v1/applications/{self.application_a.public_id}/draft/"
        url_b = f"/api/v1/applications/{self.application_b.public_id}/draft/"
        response_a = self.client.get(url_a)
        response_b = self.client.get(url_b)
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)

    def test_employee_can_access_admin_views(self):
        """Сотрудник может получить доступ к админским эндпоинтам."""
        self.client.force_authenticate(user=self.employee)
        url = f"/api/v1/applications/admin/applications/{self.application_a.public_id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_applicant_cannot_access_admin_views(self):
        """Заявитель не может получить доступ к админским эндпоинтам."""
        self.client.force_authenticate(user=self.applicant_a)
        url = f"/api/v1/applications/admin/applications/{self.application_a.public_id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # IsEmployeeOrAdmin

    def test_applicant_cannot_add_comment(self):
        """Заявитель не может добавить комментарий."""
        self.client.force_authenticate(user=self.applicant_a)
        url = f"/api/v1/applications/{self.application_a.public_id}/comments/"
        response = self.client.post(url, {"comment": "This is a comment"})
        self.assertEqual(response.status_code, 403)

    def test_employee_can_add_comment(self):
        """Сотрудник может добавить комментарий."""
        self.client.force_authenticate(user=self.employee)
        url = f"/api/v1/applications/{self.application_a.public_id}/comments/"
        response = self.client.post(url, {"comment": "This is a comment from an employee"})
        self.assertEqual(response.status_code, 201)
