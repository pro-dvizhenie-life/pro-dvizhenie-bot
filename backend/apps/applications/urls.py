"""Маршруты приложения заявок."""

from django.urls import path

from . import views
from .views import admin_views, application_views, bot_views, export_views

app_name = "applications"

urlpatterns = [
    path("", views.index, name="index"),
    path("forms/<slug:survey_code>/sessions/", application_views.create_session, name="create_session"),
    path("<uuid:public_id>/draft/", application_views.get_draft, name="get_draft"),
    path("<uuid:public_id>/draft/patch/", application_views.patch_draft, name="patch_draft"),
    path("<uuid:public_id>/next/", application_views.post_next, name="post_next"),
    path("<uuid:public_id>/submit/", application_views.post_submit, name="post_submit"),
    path("<uuid:public_id>/consents/", application_views.post_consent, name="post_consent"),
    path("<uuid:public_id>/comments/", application_views.application_comments, name="application_comments"),
    path("admin/applications/", admin_views.application_list, name="admin_application_list"),
    path("admin/applications/<uuid:public_id>/", admin_views.application_detail, name="admin_application_detail"),
    path("admin/applications/<uuid:public_id>/status/", admin_views.application_status_patch, name="admin_application_status"),
    path("admin/applications/<uuid:public_id>/timeline/", admin_views.application_timeline, name="admin_application_timeline"),
    path("admin/export.csv", export_views.export_csv, name="applications_export"),
    path("telegram/webhook/", bot_views.telegram_webhook, name="telegram_webhook"),
]
